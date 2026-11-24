"""Outgoing email (verification and password-reset codes).

Nothing here is configured by default; set ONE of these in Railway:
  RESEND_API_KEY + MAIL_FROM   - Resend (https://resend.com), "FIDEM <no-reply@your-domain>"
  SMTP_HOST (+ SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM)  - any SMTP provider

Without either, `configured()` is False and the email features answer
`email_unavailable` instead of pretending to send. The recipient's address is
never written to the log (only its domain).
"""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

import httpx

log = logging.getLogger("fidem.mail")


def _cfg() -> dict:
    return {
        "resend": os.environ.get("RESEND_API_KEY", "").strip(),
        "from": os.environ.get("MAIL_FROM", "").strip(),
        "smtp_host": os.environ.get("SMTP_HOST", "").strip(),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "smtp_user": os.environ.get("SMTP_USER", "").strip(),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
    }


def configured() -> bool:
    c = _cfg()
    return bool(c["from"] and (c["resend"] or c["smtp_host"]))


def _domain(addr: str) -> str:
    return addr.rsplit("@", 1)[-1] if "@" in addr else "?"


async def send_email(to: str, subject: str, text: str) -> bool:
    """True when the provider accepted the message. Never raises."""
    c = _cfg()
    if not configured():
        log.warning("email not configured: nothing sent to @%s", _domain(to))
        return False
    try:
        if c["resend"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {c['resend']}"},
                    json={"from": c["from"], "to": [to], "subject": subject, "text": text},
                )
            if r.status_code >= 300:
                log.warning("resend rejected a message to @%s: HTTP %s", _domain(to), r.status_code)
                return False
            return True
        return await asyncio.to_thread(_send_smtp, c, to, subject, text)
    except Exception as e:  # network down, bad credentials ...
        log.warning("email to @%s failed: %s", _domain(to), type(e).__name__)
        return False


def _send_smtp(c: dict, to: str, subject: str, text: str) -> bool:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = c["from"], to, subject
    msg.set_content(text)
    ctx = ssl.create_default_context()
    if c["smtp_port"] == 465:
        with smtplib.SMTP_SSL(c["smtp_host"], c["smtp_port"], context=ctx, timeout=15) as s:
            if c["smtp_user"]:
                s.login(c["smtp_user"], c["smtp_password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(c["smtp_host"], c["smtp_port"], timeout=15) as s:
            s.starttls(context=ctx)
            if c["smtp_user"]:
                s.login(c["smtp_user"], c["smtp_password"])
            s.send_message(msg)
    return True
