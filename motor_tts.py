"""Motor de síntesis de voz para el Estudio de Podcast.

Módulo puro (sin Streamlit): limpieza del guion, troceo del texto,
backends TTS intercambiables y ensamblado del episodio en memoria.
"""
from __future__ import annotations

import asyncio
import io
import re
import time
from collections.abc import Callable
from typing import Protocol


class ErrorSintesis(RuntimeError):
    """Fallo al sintetizar audio (red, límite de peticiones, voz inválida...).

    `reintentable=False` indica que repetir la petición no servirá (p. ej. un
    403 de Edge por bloqueo del servidor), para no perder tiempo en reintentos.
    """

    def __init__(self, mensaje: str, reintentable: bool = True):
        super().__init__(mensaje)
        self.reintentable = reintentable


# ---------------------------------------------------------------------------
# Limpieza del guion
# ---------------------------------------------------------------------------
_RE_ENLACE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_RE_ACOTACION = re.compile(r"\[[^\]]*\]")                 # [Música de entrada]
_RE_ENCABEZADO = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*", re.M)
_RE_ETIQUETA_MD = re.compile(r"^[ \t]*\*\*[^*\n]{1,40}?:\*\*[ \t]*", re.M)   # **Locutor:**
_RE_ETIQUETA_MAY = re.compile(r"^[ \t]*[A-ZÁÉÍÓÚÑ0-9 ]{2,30}:[ \t]*", re.M)    # LOCUTOR:
_RE_NEGRITA = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.S)
_RE_CURSIVA = re.compile(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])")
_RE_VINETA = re.compile(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]+", re.M)
_RE_LINEAS_VACIAS = re.compile(r"\n{3,}")


def limpiar_guion(texto: str, quitar_etiquetas_locutor: bool = True) -> str:
    """Elimina el marcado que el locutor no debe leer en voz alta.

    Quita markdown (encabezados, negritas, viñetas), acotaciones entre
    corchetes y, opcionalmente, las etiquetas de locutor al inicio de línea.
    """
    t = texto.replace("\r\n", "\n")
    t = _RE_ENLACE.sub(r"\1", t)
    t = _RE_ACOTACION.sub("", t)
    t = _RE_ENCABEZADO.sub("", t)
    if quitar_etiquetas_locutor:
        t = _RE_ETIQUETA_MD.sub("", t)
        t = _RE_ETIQUETA_MAY.sub("", t)
    t = _RE_NEGRITA.sub(lambda m: m.group(1) or m.group(2), t)
    t = _RE_CURSIVA.sub(r"\1", t)
    t = _RE_VINETA.sub("", t)
    t = "\n".join(linea.strip() for linea in t.split("\n"))
    return _RE_LINEAS_VACIAS.sub("\n\n", t).strip()


# ---------------------------------------------------------------------------
# Troceo
# ---------------------------------------------------------------------------
_RE_FIN_FRASE = re.compile(r"(?<=[.!?…;:])\s+|\n+")


def trocear(texto: str, max_chars: int = 1500) -> list[str]:
    """Divide el texto en bloques <= max_chars sin cortar frases si es posible."""
    if max_chars < 20:
        raise ValueError("max_chars debe ser >= 20")
    frases = [f.strip() for f in _RE_FIN_FRASE.split(texto) if f and f.strip()]
    bloques: list[str] = []
    actual = ""
    for frase in frases:
        # Frase más larga que el límite: se corta por palabras.
        while len(frase) > max_chars:
            corte = frase.rfind(" ", 0, max_chars)
            corte = corte if corte > 0 else max_chars
            if actual:
                bloques.append(actual)
                actual = ""
            bloques.append(frase[:corte].strip())
            frase = frase[corte:].strip()
        if not frase:
            continue
        candidato = f"{actual} {frase}".strip()
        if len(candidato) <= max_chars:
            actual = candidato
        else:
            bloques.append(actual)
            actual = frase
    if actual:
        bloques.append(actual)
    return bloques


def primeras_palabras(texto: str, n: int = 20) -> str:
    return " ".join(texto.split()[:n])


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class BackendTTS(Protocol):
    nombre: str
    voces: dict[str, str]
    etiqueta_selector: str   # rótulo del desplegable de voces en la interfaz
    nota_voces: str          # aclaración breve bajo el desplegable ("" = ninguna)
    admite_velocidad: bool

    def sintetizar(self, texto: str, voz: str, velocidad: float = 1.0) -> bytes: ...


class BackendGTTS:
    """Google Translate TTS (no oficial). Sin control de velocidad ni tono:
    el 'acento' solo cambia el dominio de Google, la voz es la misma."""

    nombre = "gTTS (Google Translate)"
    voces = {
        "🇪🇸 España": "es",
        "🇲🇽 México": "com.mx",
        "🇺🇸 EE. UU. (latino)": "us",
    }
    etiqueta_selector = "Acento"
    nota_voces = "gTTS tiene una única voz femenina: solo cambia el acento."
    admite_velocidad = False

    def sintetizar(self, texto: str, voz: str, velocidad: float = 1.0) -> bytes:
        from gtts import gTTS, gTTSError

        buf = io.BytesIO()
        try:
            gTTS(text=texto, lang="es", tld=voz, slow=velocidad < 0.85).write_to_fp(buf)
        except gTTSError as e:
            raise ErrorSintesis(f"gTTS: {e}") from e
        return buf.getvalue()


def velocidad_a_rate(velocidad: float) -> str:
    """1.0 -> '+0%', 1.15 -> '+15%', 0.9 -> '-10%' (formato de edge-tts)."""
    return f"{round((velocidad - 1.0) * 100):+d}%"


class BackendEdge:
    """Voces neuronales de Microsoft Edge vía edge-tts (no oficial).
    Requiere edge-tts 7.x o superior y el reloj del sistema en hora."""

    nombre = "Edge TTS (voces neuronales)"
    voces = {
        "🇪🇸 Álvaro · locutor (España)": "es-ES-AlvaroNeural",
        "🇪🇸 Elvira · locutora (España)": "es-ES-ElviraNeural",
        "🇲🇽 Jorge · locutor (México)": "es-MX-JorgeNeural",
        "🇲🇽 Dalia · locutora (México)": "es-MX-DaliaNeural",
    }
    etiqueta_selector = "Locutor / locutora"
    nota_voces = ""
    admite_velocidad = True

    def sintetizar(self, texto: str, voz: str, velocidad: float = 1.0) -> bytes:
        import edge_tts

        async def _run() -> bytes:
            com = edge_tts.Communicate(texto, voz, rate=velocidad_a_rate(velocidad))
            buf = bytearray()
            async for trozo in com.stream():
                if trozo["type"] == "audio":
                    buf.extend(trozo["data"])
            return bytes(buf)

        try:
            audio = asyncio.run(_run())
        except Exception as e:  # edge-tts lanza excepciones variadas de aiohttp
            if "403" in str(e):
                raise ErrorSintesis(
                    "Edge TTS rechazó la conexión (403). Microsoft está bloqueando "
                    "esta petición: puede ser la IP (nube, VPN, muchas peticiones) "
                    "o un cambio en su servicio. Prueba otro motor de voz.",
                    reintentable=False,
                ) from e
            raise ErrorSintesis(f"Edge TTS: {e}") from e
        if not audio:
            raise ErrorSintesis("Edge TTS no devolvió audio.")
        return audio


BACKENDS: dict[str, BackendTTS] = {b.nombre: b for b in (BackendEdge(), BackendGTTS())}


def voz_gtts_equivalente(voz_edge: str) -> str:
    """Acento de gTTS más parecido a una voz de Edge (para el respaldo)."""
    return "com.mx" if voz_edge.startswith("es-MX") else "es"


# ---------------------------------------------------------------------------
# Ensamblado del episodio
# ---------------------------------------------------------------------------
def sintetizar_guion(
    texto: str,
    backend: BackendTTS,
    voz: str,
    velocidad: float = 1.0,
    max_chars: int = 1500,
    reintentos: int = 2,
    espera_s: float = 2.0,
    progreso: Callable[[int, int], None] | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> bytes:
    """Sintetiza el guion por bloques y concatena los MP3 en memoria.

    Reintenta cada bloque con espera creciente para absorber límites de
    peticiones (HTTP 429/403 transitorios).
    """
    bloques = trocear(texto, max_chars)
    if not bloques:
        raise ValueError("El guion está vacío.")
    salida = io.BytesIO()
    for i, bloque in enumerate(bloques, start=1):
        for intento in range(reintentos + 1):
            try:
                salida.write(backend.sintetizar(bloque, voz, velocidad))
                break
            except ErrorSintesis as e:
                if not e.reintentable or intento == reintentos:
                    raise
                dormir(espera_s * (intento + 1))
        if progreso:
            progreso(i, len(bloques))
    return salida.getvalue()
