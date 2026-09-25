"""Outgoing email over SMTP. Messages are plain text with a simple HTML alternative."""

import html
import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings

log = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(get_settings().smtp_host)


def build_message(
    to: str, subject: str, paragraphs: list[str], action: tuple[str, str] | None = None
) -> EmailMessage:
    """paragraphs are plain text; action is (label, url) for the one button in the email."""
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    footer = "Powered by SecAI by hdbrzgr · https://github.com/hdbrzgr/SecAI"

    text = "\n\n".join(paragraphs)
    if action:
        text += f"\n\n{action[0]}: {action[1]}"
    msg.set_content(f"{text}\n\n--\n{footer}\n")

    body = "".join(f'<p style="margin:0 0 16px">{html.escape(p)}</p>' for p in paragraphs)
    if action:
        body += (
            f'<p style="margin:24px 0"><a href="{html.escape(action[1], quote=True)}" '
            'style="background:#0b6e68;color:#ffffff;padding:10px 18px;border-radius:4px;'
            f'text-decoration:none;font-weight:600">{html.escape(action[0])}</a></p>'
            f'<p style="margin:0 0 16px;color:#526073;font-size:13px">Or open this link: '
            f"{html.escape(action[1])}</p>"
        )
    msg.add_alternative(
        '<!doctype html><html><body style="margin:0;padding:24px;background:#f5f7f9;'
        "font-family:'IBM Plex Sans',system-ui,sans-serif;color:#0e1621;"
        'font-size:15px;line-height:24px">'
        '<div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #dde3ea;'
        'border-radius:6px;padding:28px">'
        '<p style="margin:0 0 20px;font-weight:700;font-size:20px">'
        'Sec<span style="color:#0b6e68">AI</span></p>'
        f"{body}</div>"
        f'<p style="text-align:center;color:#526073;font-size:12px">{html.escape(footer)}</p>'
        "</body></html>",
        subtype="html",
    )
    return msg


async def send(msg: EmailMessage) -> bool:
    """Send a message. Returns False (and logs) instead of raising, so email never breaks a flow."""
    settings = get_settings()
    if not settings.smtp_host:
        log.info("SMTP not configured; not sending %r to %s", msg["Subject"], msg["To"])
        return False
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_security == "starttls",
            use_tls=settings.smtp_security == "tls",
            timeout=20,
        )
        return True
    except (aiosmtplib.SMTPException, OSError) as exc:
        log.warning("Sending %r to %s failed: %s", msg["Subject"], msg["To"], exc)
        return False
