"""Outgoing email over SMTP (stdlib smtplib), sent from a worker thread."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

_PURPOSE_COPY = {
    "verify_email": (
        "رمز التحقق من بريدك الإلكتروني",
        "Your email verification code",
        "استخدم هذا الرمز لتأكيد بريدك الإلكتروني",
        "Use this code to verify your email address",
    ),
    "reset_password": (
        "رمز إعادة تعيين كلمة المرور",
        "Your password reset code",
        "استخدم هذا الرمز لإعادة تعيين كلمة المرور",
        "Use this code to reset your password",
    ),
}


def build_code_message(to: str, code: str, purpose: str) -> EmailMessage:
    """Short bilingual (Arabic + English) message carrying the 6-digit code."""
    subject_ar, subject_en, line_ar, line_en = _PURPOSE_COPY[purpose]
    message = EmailMessage()
    message["To"] = to
    message["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME or "no-reply@localhost"
    message["Subject"] = f"TRENDY AI - {subject_ar} | {subject_en}"
    message.set_content(
        f"{line_ar}:\n\n"
        f"    {code}\n\n"
        "ينتهي الرمز خلال 15 دقيقة. إذا لم تطلبه فتجاهل هذه الرسالة.\n"
        "\n"
        "---\n"
        "\n"
        f"{line_en}:\n\n"
        f"    {code}\n\n"
        "The code expires in 15 minutes. If you did not request it, ignore this email.\n"
    )
    return message


def _send_sync(message: EmailMessage) -> None:
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    context = ssl.create_default_context()
    if port == 465 and not settings.SMTP_STARTTLS:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    with server:
        server.ehlo()
        if settings.SMTP_STARTTLS and port != 465:
            server.starttls(context=context)
            server.ehlo()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)


def send_code_email_sync(to: str, code: str, purpose: str) -> None:
    if not settings.SMTP_HOST:
        # Dev mode: no mail server configured, so surface the code in the log.
        logger.warning("SMTP_HOST is empty; %s code for %s is %s", purpose, to, code)
        return
    _send_sync(build_code_message(to, code, purpose))


async def send_code_email(to: str, code: str, purpose: str) -> None:
    """Send the code without blocking the event loop.

    Delivery problems are logged, never raised: the endpoints answer the same
    way whether or not mail went out (no account enumeration), and the user
    can request a new code.
    """
    try:
        await asyncio.to_thread(send_code_email_sync, to, code, purpose)
    except Exception:
        logger.exception("Failed to send %s email to %s", purpose, to)
