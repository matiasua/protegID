"""Servicio de envío de email transaccional."""

from email.message import EmailMessage
from email.utils import formataddr
from smtplib import SMTP, SMTPException
from urllib.parse import quote

from app.core.settings import get_settings


class EmailDeliveryError(RuntimeError):
    pass


def _is_console_delivery_allowed() -> bool:
    return get_settings().app_env in {"local", "dev", "development", "test"}


def _format_expiration_window(ttl_seconds: int) -> str:
    if ttl_seconds % 3600 == 0:
        hours = ttl_seconds // 3600
        return f"{hours} hora" if hours == 1 else f"{hours} horas"

    if ttl_seconds % 60 == 0:
        minutes = ttl_seconds // 60
        return f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos"

    return f"{ttl_seconds} segundos"


def _send_console_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    if not _is_console_delivery_allowed():
        raise EmailDeliveryError("Console email delivery is not allowed outside local/dev")

    print("protegid_email_delivery_mode=console")
    print(f"to={to_email}")
    print(f"subject={subject}")
    print(text_body)
    if html_body:
        print(html_body)


def _send_smtp_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise EmailDeliveryError("SMTP_HOST is not configured")

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_port == 587:
                smtp.starttls()
            if settings.smtp_username or settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except SMTPException as error:
        raise EmailDeliveryError("SMTP email delivery failed") from error
    except OSError as error:
        raise EmailDeliveryError("SMTP connection failed") from error


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    delivery_mode = get_settings().email_delivery_mode.strip().lower()
    if delivery_mode == "console":
        _send_console_email(to_email, subject, text_body, html_body)
        return

    if delivery_mode == "smtp":
        _send_smtp_email(to_email, subject, text_body, html_body)
        return

    raise EmailDeliveryError("Unsupported email delivery mode")


def build_email_verification_url(token: str) -> str:
    base_url = get_settings().public_app_url.rstrip("/")
    return f"{base_url}/verify-email?token={quote(token, safe='')}"


def send_email_verification_email(to_email: str, verification_url: str) -> None:
    settings = get_settings()
    expiration_window = _format_expiration_window(
        settings.email_verification_token_ttl_seconds
    )
    subject = "Verifica tu correo en ProtegID"
    text_body = (
        "Hola,\n\n"
        "Usa este enlace para verificar tu correo en ProtegID:\n"
        f"{verification_url}\n\n"
        f"Este enlace expira en {expiration_window}. "
        "Si no creaste una cuenta en ProtegID, puedes ignorar este mensaje.\n"
    )
    send_email(to_email, subject, text_body)
