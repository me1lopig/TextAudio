"""Interfaz Streamlit del Estudio de Podcast IA (la lógica vive en motor_tts.py)."""
import streamlit as st

from motor_tts import (
    BACKENDS,
    BackendEdge,
    BackendGTTS,
    ErrorSintesis,
    limpiar_guion,
    primeras_palabras,
    sintetizar_guion,
    voz_gtts_equivalente,
)

st.set_page_config(page_title="Generador de audios", page_icon="🎙️", layout="centered")

# --- Estado ---------------------------------------------------------------
for clave, defecto in {
    "texto_guion": "",
    "ultimo_archivo": None,
    "audio_prueba": None,
    "audio_episodio": None,
}.items():
    st.session_state.setdefault(clave, defecto)


def _al_limpiar() -> None:
    st.session_state.texto_guion = limpiar_guion(st.session_state.texto_guion)


def _invalidar_audio() -> None:
    st.session_state.audio_prueba = None
    st.session_state.audio_episodio = None


# --- Barra lateral --------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ajustes de locución")
    nombre_backend = st.selectbox("Motor de voz", list(BACKENDS), on_change=_invalidar_audio)
    backend = BACKENDS[nombre_backend]
    etiqueta_voz = st.selectbox(backend.etiqueta_selector, list(backend.voces),
                                on_change=_invalidar_audio)
    voz = backend.voces[etiqueta_voz]
    if backend.nota_voces:
        st.caption(backend.nota_voces)
    velocidad = st.slider(
        "Velocidad", 0.7, 1.3, 1.0, 0.05,
        disabled=not backend.admite_velocidad,
        help=None if backend.admite_velocidad else "gTTS no permite ajustar la velocidad.",
        on_change=_invalidar_audio,
    )
    usar_respaldo = st.toggle(
        "Si Edge falla, usar gTTS", value=True,
        disabled=not isinstance(backend, BackendEdge),
        help="Si Microsoft rechaza la conexión, el audio se genera con gTTS.",
    )


def ejecutar(sintesis):
    """Llama a sintesis(backend, voz, velocidad); si Edge falla, reintenta con gTTS."""
    try:
        return sintesis(backend, voz, velocidad)
    except ErrorSintesis as e:
        if not (usar_respaldo and isinstance(backend, BackendEdge)):
            raise
        st.warning(f"{e}\n\nSe ha usado gTTS como respaldo (voz femenina única, "
                   "sin ajuste de velocidad).")
        return sintesis(BACKENDS[BackendGTTS.nombre], voz_gtts_equivalente(voz), 1.0)

st.title("🎙️ Estudio de Podcast IA")
st.markdown("Carga tu guión, límpialo y genera el audio del episodio.")
st.markdown("Según directiva ITQ404")
st.markdown("**Nota:** Microsoft Edge TTS puede rechazar la conexión (403) si detecta "
            "muchas peticiones o un cambio en su servicio. En ese caso, prueba otro motor "
            "o activa el respaldo gTTS (voz femenina única, sin ajuste de velocidad).")

tab1, tab2 = st.tabs(["📝 1. Editor de guion", "🎧 2. Generación y audio"])

# --- Editor ---------------------------------------------------------------
with tab1:
    archivo = st.file_uploader("Sube el guion (.txt o .md)", type=["txt", "md"])
    if archivo is not None and st.session_state.ultimo_archivo != archivo.name:
        # utf-8-sig elimina el BOM; 'replace' evita fallar con codificaciones raras
        st.session_state.texto_guion = archivo.getvalue().decode("utf-8-sig", errors="replace")
        st.session_state.ultimo_archivo = archivo.name
        _invalidar_audio()
        st.success(f"Archivo «{archivo.name}» cargado.")

    st.text_area("Texto final para el locutor:", key="texto_guion", height=400,
                 on_change=_invalidar_audio)
    col1, col2 = st.columns([1, 2])
    col1.button("🧹 Limpiar marcado", on_click=_al_limpiar,
                help="Quita markdown, [acotaciones] y etiquetas tipo «LOCUTOR:».")
    n_car = len(st.session_state.texto_guion)
    col2.caption(f"{n_car:,} caracteres · ~{n_car / 900:.0f} min de audio".replace(",", "."))

# --- Generación -----------------------------------------------------------
with tab2:
    texto = st.session_state.texto_guion.strip()

    if st.button("▶️ Prueba rápida (20 palabras)", disabled=not texto):
        try:
            with st.spinner("Generando muestra..."):
                st.session_state.audio_prueba = ejecutar(
                    lambda b, v, vel: b.sintetizar(primeras_palabras(texto), v, vel))
        except ErrorSintesis as e:
            st.error(f"No se pudo generar la muestra: {e}")
    if st.session_state.audio_prueba:
        st.audio(st.session_state.audio_prueba, format="audio/mpeg")

    st.divider()

    if st.button("🎙️ Generar episodio completo", type="primary", disabled=not texto,
                 use_container_width=True):
        barra = st.progress(0.0, text="Sintetizando...")
        try:
            st.session_state.audio_episodio = ejecutar(
                lambda b, v, vel: sintetizar_guion(
                    texto, b, v, vel,
                    progreso=lambda i, n: barra.progress(i / n, text=f"Bloque {i}/{n}"),
                )
            )
            barra.empty()
            st.success("✅ Audio generado.")
        except ErrorSintesis as e:
            barra.empty()
            st.error(f"Falló la síntesis: {e}")

    # Fuera del bloque del botón: el audio sobrevive a los reruns (p. ej. al descargar)
    if st.session_state.audio_episodio:
        st.audio(st.session_state.audio_episodio, format="audio/mpeg")
        st.download_button(
            "💾 Descargar episodio (MP3)",
            data=st.session_state.audio_episodio,
            file_name="podcast_tecnologico.mp3",
            mime="audio/mpeg",
            use_container_width=True,
        )
    elif not texto:
        st.info("Escribe o carga un guion en la pestaña 1.")
