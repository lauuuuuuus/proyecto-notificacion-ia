"""
Sistema de Alerta Temprana de Bajo Rendimiento Académico
---------------------------------------------------------
Detecta estudiantes en riesgo a partir de sus notas parciales, genera
un mensaje de alerta personalizado con IA (Claude) y lo envía
automáticamente por correo al tutor asignado.

Proyecto transversal - Uso de IA para resolver un problema real universitario.
"""

import streamlit as st
import pandas as pd

from src.risk_analysis import calcular_riesgo, resumen_riesgo
from src.ai_notification import generar_mensaje_alerta
from src.email_sender import enviar_correo

st.set_page_config(
    page_title="Alerta Temprana Académica",
    page_icon="🎓",
    layout="wide",
)

st.title("🎓 Sistema de Alerta Temprana de Bajo Rendimiento")
st.caption(
    "Detecta estudiantes en riesgo académico y notifica automáticamente "
    "a su tutor con un mensaje generado por IA."
)

col_a, col_b = st.columns([2, 1])
with col_a:
    archivo = st.file_uploader(
        "Sube el CSV con las notas (o usa el archivo de ejemplo)",
        type=["csv"],
    )
with col_b:
    usar_ejemplo = st.checkbox("Usar datos de ejemplo", value=archivo is None)

if usar_ejemplo:
    df = pd.read_csv("data/estudiantes_ejemplo.csv")
elif archivo is not None:
    df = pd.read_csv(archivo)
else:
    st.info("Sube un archivo CSV o marca la casilla de datos de ejemplo para continuar.")
    st.stop()

st.dataframe(df, use_container_width=True)

st.header("2. Parámetros del análisis")

col1, col2 = st.columns(2)
with col1:
    umbral_promedio = st.slider("Promedio mínimo aceptable", 0.0, 5.0, 3.0, 0.1)
with col2:
    umbral_caida = st.slider("Caída de notas considerada alarmante", 0.0, 3.0, 0.8, 0.1)

df_evaluado = calcular_riesgo(df, umbral_promedio, umbral_caida)
resumen = resumen_riesgo(df_evaluado)

m1, m2, m3 = st.columns(3)
m1.metric("Total de estudiantes", resumen["total_estudiantes"])
m2.metric("En riesgo", resumen["en_riesgo"])
m3.metric("% en riesgo", f"{resumen['porcentaje_riesgo']}%")

en_riesgo_df = df_evaluado[df_evaluado["en_riesgo"]]
st.subheader("Estudiantes en riesgo detectados")
if en_riesgo_df.empty:
    st.success("No se detectaron estudiantes en riesgo con los parámetros actuales.")
else:
    st.dataframe(
        en_riesgo_df[["nombre", "materia", "promedio", "caida", "motivo", "correo_tutor"]],
        use_container_width=True,
    )

st.header("3. Generar y enviar alertas")

modo_simulacion = st.toggle(
    "Modo simulación (genera el mensaje pero NO envía correo real)",
    value=True,
    help="Útil para hacer la demo sin necesidad de credenciales SMTP configuradas.",
)

if en_riesgo_df.empty:
    st.stop()

if st.button("🚀 Analizar y notificar a los tutores", type="primary"):
    for _, row in en_riesgo_df.iterrows():
        with st.expander(f"📩 {row['nombre']} — {row['materia']}", expanded=True):
            with st.spinner("Generando mensaje con IA..."):
                try:
                    mensaje = generar_mensaje_alerta(
                        nombre_estudiante=row["nombre"],
                        materia=row["materia"],
                        promedio=row["promedio"],
                        caida=row["caida"],
                        motivo=row["motivo"],
                    )
                except Exception as e:
                    st.error(f"No se pudo generar el mensaje con IA: {e}")
                    continue

            st.write("**Mensaje generado:**")
            st.write(mensaje)

            asunto = f"Alerta académica: {row['nombre']} - {row['materia']}"

            if modo_simulacion:
                st.info("Modo simulación activo: el correo no fue enviado realmente.")
            else:
                exito, resultado = enviar_correo(row["correo_tutor"], asunto, mensaje)
                if exito:
                    st.success(resultado)
                else:
                    st.error(resultado)

st.divider()
st.caption(
    "Proyecto transversal — Sistema de alerta temprana con IA. "
    "Código disponible en GitHub."
)
