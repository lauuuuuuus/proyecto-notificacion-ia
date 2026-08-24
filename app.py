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

# ---------------------------------------------------------------------
# 1. Carga de datos
# ---------------------------------------------------------------------
st.header("1. Datos de estudiantes")

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

# ---------------------------------------------------------------------
# 2. Configuración del análisis
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# 3. Generación de alertas con IA y envío de correo
# ---------------------------------------------------------------------
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
)"""
Módulo de análisis de riesgo académico.

Recibe un DataFrame con notas de estudiantes a lo largo del semestre
y calcula, para cada uno, si se encuentra en riesgo de bajo rendimiento.

Formato esperado del CSV (columnas):
    id_estudiante, nombre, correo_tutor, materia, nota_corte1, nota_corte2, nota_corte3

- nota_corteX: notas parciales (escala 0.0 - 5.0)
"""

import pandas as pd


def calcular_riesgo(df: pd.DataFrame, umbral_promedio: float = 3.0, umbral_caida: float = 0.8) -> pd.DataFrame:
    """
    Calcula el nivel de riesgo académico por estudiante.

    Args:
        df: DataFrame con las columnas de notas parciales.
        umbral_promedio: promedio mínimo aceptable (por debajo de esto -> riesgo).
        umbral_caida: caída mínima entre el primer y último corte que se considera alarmante.

    Returns:
        DataFrame original + columnas: promedio, caida, en_riesgo, motivo
    """
    df = df.copy()

    columnas_notas = [c for c in df.columns if c.startswith("nota_corte")]
    if not columnas_notas:
        raise ValueError("El archivo no tiene columnas 'nota_corteX' con las notas parciales.")

    df["promedio"] = df[columnas_notas].mean(axis=1).round(2)
    df["caida"] = (df[columnas_notas[0]] - df[columnas_notas[-1]]).round(2)

    def evaluar(row):
        motivos = []
        if row["promedio"] < umbral_promedio:
            motivos.append(f"promedio {row['promedio']} por debajo de {umbral_promedio}")
        if row["caida"] >= umbral_caida:
            motivos.append(f"caída de {row['caida']} puntos entre el primer y último corte")
        return pd.Series({
            "en_riesgo": len(motivos) > 0,
            "motivo": "; ".join(motivos) if motivos else "sin novedades"
        })

    resultado = df.join(df.apply(evaluar, axis=1))
    return resultado


def resumen_riesgo(df_evaluado: pd.DataFrame) -> dict:
    """Genera un pequeño resumen numérico para mostrar en el dashboard."""
    total = len(df_evaluado)
    en_riesgo = int(df_evaluado["en_riesgo"].sum())
    return {
        "total_estudiantes": total,
        "en_riesgo": en_riesgo,
        "porcentaje_riesgo": round((en_riesgo / total) * 100, 1) if total else 0,
    }"""
Módulo de generación de alertas con IA (API de Anthropic - Claude).

Toma los datos de un estudiante en riesgo y genera un mensaje breve,
claro y accionable para el tutor, explicando la situación y sugiriendo
un primer paso de acompañamiento.
"""

import os
import anthropic


def _get_client() -> anthropic.Anthropic:
    """
    Crea el cliente de Anthropic usando la API key.
    Busca primero en variables de entorno, luego en st.secrets (Streamlit Cloud).
    """
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
    """
    Genera un mensaje de alerta personalizado para el tutor usando Claude.

    Args:
        nombre_estudiante: nombre del estudiante en riesgo.
        materia: materia en la que se detecta el riesgo.
        promedio: promedio actual del estudiante.
        caida: puntos de caída entre el primer y último corte.
        motivo: texto con el/los motivo(s) de la alerta.

    Returns:
        Texto del mensaje listo para enviar por correo al tutor.
    """
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

    return respuesta.content[0].text.strip()"""
Módulo de envío de correo electrónico vía SMTP.

Pensado para usarse con Gmail (con "contraseña de aplicación") u otro
proveedor SMTP. Las credenciales NUNCA se escriben en el código: se leen
de variables de entorno o de st.secrets.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_config() -> dict:
    """Obtiene la configuración SMTP desde variables de entorno o st.secrets."""
    config = {
        "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
        "smtp_user": os.environ.get("SMTP_USER"),
        "smtp_password": os.environ.get("SMTP_PASSWORD"),
    }

    faltan = [k for k, v in config.items() if v in (None, "")]
    if faltan:
        try:
            import streamlit as st
            config["smtp_server"] = st.secrets.get("SMTP_SERVER", config["smtp_server"])
            config["smtp_port"] = int(st.secrets.get("SMTP_PORT", config["smtp_port"]))
            config["smtp_user"] = st.secrets.get("SMTP_USER", config["smtp_user"])
            config["smtp_password"] = st.secrets.get("SMTP_PASSWORD", config["smtp_password"])
        except Exception:
            pass

    return config


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> tuple[bool, str]:
    """
    Envía un correo electrónico.

    Returns:
        (exito: bool, mensaje: str) -> mensaje describe el resultado o el error.
    """
    config = _get_config()

    if not config["smtp_user"] or not config["smtp_password"]:
        return False, (
            "Faltan credenciales SMTP (SMTP_USER / SMTP_PASSWORD). "
            "Actívalas como variables de entorno o en .streamlit/secrets.toml."
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = config["smtp_user"]
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.sendmail(config["smtp_user"], destinatario, msg.as_string())

        return True, f"Correo enviado correctamente a {destinatario}"

    except Exception as e:
        return False, f"Error al enviar el correo: {e}"
