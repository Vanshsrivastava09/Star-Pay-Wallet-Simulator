import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailDeliveryError(Exception):
    """Raised when a verification email cannot be delivered."""


def send_otp_email(recipient: str, otp: str) -> None:
    """Send an email verification OTP using Gmail SMTP and an app password."""
    if not settings.smtp_username or not settings.smtp_password:
        raise EmailDeliveryError("Email delivery is not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")

    message = EmailMessage()
    message["Subject"] = "Your Star Pay verification code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        f"Your verification code is {otp}. It expires in {settings.otp_expire_minutes} minutes. "
        "If you did not request this, you can ignore this email."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Unable to send the verification email. Please try again shortly.") from exc


def send_password_reset_otp(recipient: str, otp: str) -> None:
    """Send a password reset OTP using the configured Gmail SMTP account."""
    if not settings.smtp_username or not settings.smtp_password:
        raise EmailDeliveryError("Email delivery is not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.")

    message = EmailMessage()
    message["Subject"] = "Your Star Pay password reset code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        f"Your password reset code is {otp}. It expires in {settings.otp_expire_minutes} minutes. "
        "If you did not request a password reset, you can ignore this email."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Unable to send the password reset email. Please try again shortly.") from exc
