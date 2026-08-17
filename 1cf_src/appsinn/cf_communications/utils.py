# cf-dev/cf_src/appsinn/cf_communications/utils.py

"""Outbound communication utilities (email, SMS, WhatsApp, in-app)."""

from __future__ import annotations

import logging
import socket
from smtplib import SMTPException, SMTPRecipientsRefused
from typing import Any

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from . import settings as app_settings

User = get_user_model()
logger = logging.getLogger(__name__)


def _email_transport_configured() -> bool:
    """
    True when outbound email can reasonably be attempted.

    Console/file/locmem backends need no host. SMTP requires EMAIL_HOST and
    DEFAULT_FROM_EMAIL so we do not open a socket to an empty/unresolvable host.
    """
    backend = getattr(settings, "EMAIL_BACKEND", "") or ""
    if (
        backend.endswith("console.EmailBackend")
        or backend.endswith("locmem.EmailBackend")
        or backend.endswith("filebased.EmailBackend")
        or backend.endswith("dummy.EmailBackend")
    ):
        return True

    host = (getattr(settings, "EMAIL_HOST", None) or "").strip()
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    return bool(host and from_email)


def _format_template(template: str | None, **context: Any) -> str:
    """Safe string formatting for channel templates; falls back to message."""
    if not template:
        return context.get("message", "") or ""
    try:
        return template.format(**context)
    except (KeyError, ValueError) as exc:
        logger.warning(
            "Template formatting failed (%s): %s. Falling back to raw message.",
            template,
            exc,
        )
        return context.get("message", "") or ""


def send_inapp(
    message: str,
    title: str | None = None,
    sender=None,
    recipients=None,
    notification_type: str = "info",
    extra: dict | None = None,
    fail_silently: bool = True,
):
    """
    Send a real-time in-app notification via Django Channels (notification bell).
    """
    if not recipients:
        logger.debug("send_inapp: no recipients supplied — skipping.")
        return

    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning(
            "send_inapp: no channel layer configured — in-app notifications disabled."
        )
        return

    formatted_message = _format_template(
        app_settings.INAPP_DEFAULT_TEMPLATE,
        message=message,
        title=title or "",
    )
    formatted_title = _format_template(
        app_settings.INAPP_DEFAULT_TITLE_TEMPLATE,
        title=title or message,
        message=message,
    )

    sender_id = getattr(sender, "id", None) or getattr(sender, "pk", None)
    payload = {
        "type": "new_notification",
        "message": formatted_message[:120],
        "title": formatted_title[:100],
        "notification_type": str(notification_type),
        "sender": str(sender_id) if sender_id is not None else None,
    }

    if extra:
        safe_extra = {}
        for key, value in extra.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                safe_extra[key] = value
            else:
                safe_extra[key] = str(value)
        payload.update(safe_extra)

    for user in recipients:
        try:
            raw_id = user.id if isinstance(user, User) else user
            if raw_id is None:
                logger.warning("send_inapp: recipient has no id — skipping entry.")
                continue
            user_id = str(raw_id)
            group_name = f"user_{user_id}"
            async_to_sync(channel_layer.group_send)(group_name, payload)
            logger.debug("send_inapp: notification sent to group '%s'.", group_name)
        except Exception as exc:
            display_name = getattr(user, "username", None) or str(user)
            if fail_silently:
                logger.warning(
                    "send_inapp: delivery failed [recipient=%s]: %s",
                    display_name,
                    exc,
                )
            else:
                raise


def send_email(
    subject,
    body_text,
    body_html=None,
    recipients=None,
    extra_context=None,
    from_email=None,
    **kwargs,
):
    """
    Send email with optional HTML template wrapping.

    Failures are logged and do not raise by default so billing/notification
    flows continue when SMTP is unavailable.
    """
    if not recipients:
        logger.warning("send_email called with empty recipients; subject=%s", subject)
        return 0

    if not _email_transport_configured():
        logger.warning(
            "Email not sent (transport not configured: set EMAIL_HOST and "
            "DEFAULT_FROM_EMAIL, or use console/locmem EMAIL_BACKEND). "
            "subject=%r recipients=%s",
            subject,
            recipients,
        )
        return 0

    extra_context = extra_context or {}
    plain_body = strip_tags(body_text)
    sender = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.SERVER_EMAIL

    mail = EmailMultiAlternatives(
        subject=subject,
        body=plain_body,
        from_email=sender,
        to=list(recipients),
        **kwargs,
    )

    if app_settings.OPENWISP_HTML_EMAIL:
        html_content = body_html or body_text
        context = {
            "subject": subject,
            "message": html_content,
            "logo_url": app_settings.OPENWISP_EMAIL_LOGO,
        }
        context.update(extra_context)
        try:
            html_message = render_to_string(
                app_settings.OPENWISP_EMAIL_TEMPLATE,
                context=context,
            )
            mail.attach_alternative(html_message, "text/html")
        except Exception as exc:  # noqa: BLE001
            # Missing template should not block plain-text delivery.
            logger.warning("HTML email template render failed: %s", exc)
            if body_html:
                mail.attach_alternative(body_html, "text/html")

    try:
        sent = mail.send()
        logger.info("Email sent to %s", ", ".join(str(r) for r in recipients))
        return sent
    except SMTPRecipientsRefused as err:
        logger.warning("SMTP recipients refused: %s", err.recipients)
    except (socket.gaierror, socket.herror, TimeoutError, OSError, SMTPException) as exc:
        logger.warning(
            "Email send failed (SMTP/network): %s | host=%r subject=%r recipients=%s",
            exc,
            getattr(settings, "EMAIL_HOST", ""),
            subject,
            recipients,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Email send failed: %s", exc, exc_info=True)
    return 0


def send_sms(
    message: str,
    title: str | None = None,
    sender: str | None = None,
    recipients=None,
    fail_silently: bool = True,
    **context,
):
    """Send SMS via configured HTTP API with optional templating."""
    if not recipients:
        return

    formatted_message = (
        _format_template(
            app_settings.SMS_DEFAULT_TEMPLATE,
            message=message,
            title=title or "",
            **context,
        )
        or message
    )

    sms_api_url = getattr(settings, "SMS_API_URL", None)
    sms_api_key = getattr(settings, "SMS_API_KEY", None)

    if not sms_api_url or not sms_api_key:
        msg = "SMS service is not configured properly."
        if fail_silently:
            logger.warning(msg)
            return
        raise RuntimeError(msg)

    for phone in recipients:
        try:
            response = requests.post(
                sms_api_url,
                headers={"Authorization": f"Bearer {sms_api_key}"},
                json={
                    "to": phone,
                    "from": sender or "",
                    "message": formatted_message,
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info("SMS sent to %s", phone)
        except Exception as exc:
            logger.error("Failed to send SMS to %s: %s", phone, exc, exc_info=True)
            if not fail_silently:
                raise


def send_whatsapp_message(
    phone_number: str,
    template_name: str | None = None,
    parameters: list | None = None,
    language_code: str | None = None,
    fallback_message: str | None = None,
    **context,
):
    """
    Send a WhatsApp template (or free-form fallback) via Meta Cloud API.
    """
    if not getattr(settings, "WHATSAPP_ENABLED", False):
        logger.info("WhatsApp notifications are disabled in settings.")
        return False

    if not phone_number:
        logger.warning("No phone number provided for WhatsApp message.")
        return False

    template_name = template_name or app_settings.WHATSAPP_DEFAULT_TEMPLATE
    language_code = language_code or app_settings.WHATSAPP_TEMPLATE_LANGUAGE

    if not template_name and not fallback_message:
        logger.warning("No WhatsApp template or fallback message provided.")
        return False

    api_version = getattr(settings, "WHATSAPP_API_VERSION", "v19.0")
    phone_id = getattr(settings, "WHATSAPP_PHONE_ID", None)
    token = getattr(settings, "WHATSAPP_TOKEN", None)
    if not phone_id or not token:
        logger.warning("WhatsApp API is not configured (PHONE_ID / TOKEN).")
        return False

    url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    if template_name:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": param}
                            for param in (parameters or [])
                        ],
                    }
                ],
            },
        }
    else:
        formatted_fallback = _format_template(
            fallback_message or app_settings.SMS_DEFAULT_TEMPLATE, **context
        )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {"body": formatted_fallback},
        }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(
            "WhatsApp message sent to %s (template: %s)",
            phone_number,
            template_name or "free-form",
        )
        return True
    except requests.exceptions.HTTPError as exc:
        logger.error(
            "WhatsApp HTTP error: %s",
            exc.response.text if exc.response is not None else str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("WhatsApp send failed: %s", exc)
    return False


def send_whatsapp(
    phone_number: str | None = None,
    template_name: str | None = None,
    parameters: list | None = None,
    **kwargs,
):
    """Alias matching notification dispatch call sites."""
    return send_whatsapp_message(
        phone_number=phone_number or "",
        template_name=template_name,
        parameters=parameters,
        **kwargs,
    )
