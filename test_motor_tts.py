import pytest

from motor_tts import (
    ErrorSintesis,
    limpiar_guion,
    primeras_palabras,
    sintetizar_guion,
    trocear,
    velocidad_a_rate,
    voz_gtts_equivalente,
)


class BackendFalso:
    nombre = "falso"
    voces = {"x": "x"}
    admite_velocidad = True

    def __init__(self, fallos_iniciales: int = 0):
        self.fallos = fallos_iniciales
        self.llamadas: list[str] = []

    def sintetizar(self, texto, voz, velocidad=1.0):
        self.llamadas.append(texto)
        if self.fallos > 0:
            self.fallos -= 1
            raise ErrorSintesis("429")
        return f"<{texto}>".encode()


# --- limpiar_guion ---------------------------------------------------------
def test_limpia_markdown_y_acotaciones():
    guion = "# Episodio 1\n[Música de entrada]\n**Locutor:** Hola, *bienvenidos*.\n- Punto uno"
    assert limpiar_guion(guion) == "Episodio 1\n\nHola, bienvenidos.\nPunto uno"


def test_quita_etiquetas_en_mayusculas_y_conserva_enlaces():
    guion = "PRESENTADOR 1: Mira [esta web](https://x.org)."
    assert limpiar_guion(guion) == "Mira esta web."


def test_etiquetas_opcionales():
    assert limpiar_guion("LOCUTOR: Hola", quitar_etiquetas_locutor=False) == "LOCUTOR: Hola"


# --- trocear -----------------------------------------------------------------
def test_trocear_respeta_limite_y_no_pierde_palabras():
    texto = " ".join(f"Frase número {i} del guion." for i in range(200))
    bloques = trocear(texto, max_chars=300)
    assert all(len(b) <= 300 for b in bloques)
    assert " ".join(bloques).split() == texto.split()


def test_trocear_frase_gigante_se_corta_por_palabras():
    texto = "palabra " * 500
    bloques = trocear(texto, max_chars=100)
    assert len(bloques) > 1 and all(len(b) <= 100 for b in bloques)


def test_trocear_vacio():
    assert trocear("   \n  ") == []


def test_primeras_palabras():
    assert primeras_palabras("a b c d", 2) == "a b"


@pytest.mark.parametrize("vel, esperado", [(1.0, "+0%"), (1.15, "+15%"), (0.9, "-10%")])
def test_velocidad_a_rate(vel, esperado):
    assert velocidad_a_rate(vel) == esperado


# --- sintetizar_guion ----------------------------------------------------------
def test_concatena_bloques_y_reporta_progreso():
    b = BackendFalso()
    pasos = []
    audio = sintetizar_guion("Uno. Dos.", b, "x", max_chars=20, progreso=lambda i, n: pasos.append((i, n)))
    assert audio == b"<Uno. Dos.>"
    assert pasos == [(1, 1)]


def test_reintenta_y_luego_funciona():
    b = BackendFalso(fallos_iniciales=2)
    esperas = []
    audio = sintetizar_guion("Hola.", b, "x", reintentos=2, espera_s=1, dormir=esperas.append)
    assert audio == b"<Hola.>"
    assert esperas == [1, 2]


def test_agota_reintentos():
    b = BackendFalso(fallos_iniciales=5)
    with pytest.raises(ErrorSintesis):
        sintetizar_guion("Hola.", b, "x", reintentos=1, dormir=lambda s: None)


def test_error_no_reintentable_no_espera():
    class Bloqueado(BackendFalso):
        def sintetizar(self, texto, voz, velocidad=1.0):
            self.llamadas.append(texto)
            raise ErrorSintesis("403", reintentable=False)

    b, esperas = Bloqueado(), []
    with pytest.raises(ErrorSintesis):
        sintetizar_guion("Hola.", b, "x", reintentos=3, dormir=esperas.append)
    assert len(b.llamadas) == 1 and esperas == []


@pytest.mark.parametrize("voz, esperado", [("es-MX-DaliaNeural", "com.mx"),
                                           ("es-ES-AlvaroNeural", "es")])
def test_voz_gtts_equivalente(voz, esperado):
    assert voz_gtts_equivalente(voz) == esperado


def test_guion_vacio():
    with pytest.raises(ValueError):
        sintetizar_guion("  ", BackendFalso(), "x")
