import smtplib
from email.message import EmailMessage
from typing import Optional

from fintself import settings
from fintself.utils.logging import logger


def send_email(subject: str, body: str, to: Optional[list[str]] = None) -> bool:
    """Sends an email using SMTP settings from configuration.

    Returns True on success, False otherwise. If email is disabled or
    misconfigured, logs a warning and returns False.
    """
    if not settings.EMAIL_ENABLED:
        logger.warning("Email notifications are disabled (EMAIL_ENABLED=false).")
        return False

    recipients = to if to is not None else settings.EMAIL_TO
    if not settings.EMAIL_SMTP_HOST or not recipients:
        logger.warning(
            "Email not sent: missing SMTP host or recipient list (EMAIL_SMTP_HOST / EMAIL_TO)."
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM or (settings.EMAIL_SMTP_USER or "fintself@localhost")
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        if settings.EMAIL_USE_SSL:
            with smtplib.SMTP_SSL(
                settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT
            ) as server:
                if settings.EMAIL_SMTP_USER and settings.EMAIL_SMTP_PASSWORD:
                    server.login(
                        settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD
                    )
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT
            ) as server:
                if settings.EMAIL_USE_TLS:
                    try:
                        server.starttls()
                    except Exception as e:
                        logger.warning(f"Could not start TLS: {e}")
                if settings.EMAIL_SMTP_USER and settings.EMAIL_SMTP_PASSWORD:
                    server.login(
                        settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD
                    )
                server.send_message(msg)
        logger.info(
            f"Email notification sent to {', '.join(recipients)}: {subject}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False

