"""
Módulo de generación de alertas con IA (API de Anthropic - Claude).
"""

import os
import anthropic


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass

    if not api_key:
        raise RuntimeError(
            "No se encontró ANTHROPIC_API_KEY. Configúrala como variable de entorno "
            "o en .streamlit/secrets.toml"
        )

    return anthropic.Anthropic(api_key=api_key)


def generar_mensaje_alerta(nombre_estudiante: str, materia: str, promedio: float,
                            caida: float, motivo: str) -> str:
    client = _get_client()

    prompt = f"""Eres un asistente que ayuda a redactar alertas tempranas para tutores universitarios.

Datos del caso:
- Estudiante: {nombre_estudiante}
- Materia: {materia}
- Promedio actual: {promedio}
- Caída de notas: {caida} puntos
- Motivo detectado: {motivo}

Redacta un correo breve (máximo 120 palabras) para el tutor académico:
- Tono profesional, cálido y orientado a la acción (no alarmista).
- Explica brevemente por qué el sistema generó esta alerta.
- Sugiere un primer paso concreto de acompañamiento (ej. agendar una tutoría).
- No inventes datos que no te di.
- No incluyas asunto de correo, solo el cuerpo del mensaje.
"""

    respuesta = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    return respuesta.content[0].text.strip()
