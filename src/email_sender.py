"""
Módulo de envío de correo electrónico vía SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_config() -> dict:
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


def enviar_correo(destinatario: str, asunto: str, cuerpo: str):
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
