import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os
from config import settings

logger = logging.getLogger("SIPGA.EmailService")

def enviar_correo(destinatario: str, asunto: str, cuerpo: str):
    """
    Envía un correo electrónico real usando SMTP.
    Si no están configuradas las credenciales de correo en el archivo .env,
    imprime el correo en consola y lo guarda en logs locales para desarrollo.
    """
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(f"[EMAIL MOCK] No se configuraron las credenciales de correo. Correo para {destinatario} no enviado.")
        print(f"========================================\n"
              f"ENVIANDO CORREO (SIMULACIÓN POR FALTA DE CREDENCIALES EN .ENV):\n"
              f"Para: {destinatario}\n"
              f"Asunto: {asunto}\n"
              f"Cuerpo:\n{cuerpo}\n"
              f"========================================")
        # Escribir en un archivo local para que el usuario pueda ver el historial de correos enviados en dev
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, "sent_emails.log"), "a", encoding="utf-8") as f:
            f.write(f"Fecha: {datetime.now().isoformat()}\nPara: {destinatario}\nAsunto: {asunto}\nCuerpo:\n{cuerpo}\n\n")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, destinatario, msg.as_string())
        server.quit()
        logger.info(f"Correo enviado exitosamente a {destinatario}")
    except Exception as e:
        logger.error(f"Error al enviar correo a {destinatario}: {str(e)}")
        # Escribir en el log local de fallos
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, "failed_emails.log"), "a", encoding="utf-8") as f:
            f.write(f"Fecha: {datetime.now().isoformat()}\nPara: {destinatario}\nError: {str(e)}\n\n")
