# 🎙️ Text_audio

Generador de audio para podcast a partir de guiones de texto, construido con Python y una interfaz web moderna en Streamlit.

El proyecto permite cargar un guion, limpiarlo de marcado, elegir la voz y el motor de síntesis y generar audio listo para escuchar o descargar.

## ✨ Características principales

- 📝 Carga de guiones en formato `.txt` o `.md`
- 🧹 Limpieza automática de markdown, encabezados, notas y etiquetas de locutor
- 🎧 Generación de audio con motores TTS intercambiables
- 🌍 Soporte para voces neuronales de Microsoft Edge TTS y respaldo con gTTS
- 🚀 División del texto en bloques para sintetizar episodios largos sin perder fluidez
- 📥 Descarga del resultado final en formato MP3
- 🧠 Interfaz intuitiva basada en Streamlit

## 🧩 ¿Qué hace este proyecto?

`Text_audio` toma un texto escrito en estilo de guion y lo convierte en audio con una voz natural. Está pensado para crear episodios de podcast, voz en off o contenido narrado a partir de scripts de texto.

El flujo principal es:

1. Subir o escribir el guion
2. Limpiar el texto eliminando etiquetas y formato visual
3. Elegir voz, acento y velocidad
4. Generar una prueba rápida o el episodio completo
5. Reproducir o descargar el archivo generado

## 🏗️ Arquitectura del proyecto

- `app.py`: interfaz gráfica con Streamlit
- `motor_tts.py`: lógica central de síntesis, limpieza del guion y gestión de backends
- `test_motor_tts.py`: pruebas unitarias del motor de TTS
- `pyproject.toml`: configuración del proyecto y dependencias

## 🛠️ Stack tecnológico

- Python 3.11+
- Streamlit
- Edge TTS
- gTTS
- Pytest

## ⚙️ Requisitos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

- Python 3.11 o superior
- pip
- ffmpeg o dependencias del entorno para reproducir/exportar audio

## 🚀 Instalación

```bash
git clone https://github.com/me1lopig/Text_audio.git
cd Text_audio
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -U pip
pip install .
```

## ▶️ Uso

Ejecuta la aplicación:

```bash
streamlit run app.py
```

Luego:

- abre la interfaz en tu navegador
- pega o carga tu guion
- ajusta la voz y la velocidad
- genera una prueba o el episodio completo
- descarga el archivo MP3

## 🧠 Motor de síntesis

El proyecto implementa un backend configurable:

- `BackendEdge`: utiliza voces neuronales de Microsoft Edge TTS
- `BackendGTTS`: usa Google Translate TTS como respaldo o alternativa

La lógica de limpieza y segmentación del texto está centralizada en `motor_tts.py`, lo que permite mantener el sistema modular y extensible.

## 📌 Observaciones

- La interfaz está enfocada en automatizar la creación de contenido de audio a partir de texto.
- El sistema incluye manejo de errores para respaldos y reintentos de síntesis.
- El repositorio está preparado para seguir evolucionando con nuevas voces, mejoras de calidad y funcionalidades adicionales.

## 🧪 Pruebas

```bash
pytest
```

## 📄 Licencia

Este proyecto se distribuye bajo la licencia indicada en el archivo `LICENSE`.

---

Desarrollado con ❤️ para automatizar la creación de contenido de audio a partir de guiones.
