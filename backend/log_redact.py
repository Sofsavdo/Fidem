"""Keep credentials out of server logs.

The WebSocket handshake and media URLs carry the session JWT in the query
string (`/api/ws?token=...`, `/api/chat/voice/<id>?auth=...`) because the
browser can't set headers there. uvicorn logs the full request path, which
would leave a valid token in the hosting provider's logs, so redact those
query values before any handler formats the record.
"""
import logging
import re

_SECRET_QUERY = re.compile(r"([?&](?:token|auth|access_token)=)[^\s&\"']+", re.IGNORECASE)


def redact(text: str) -> str:
    return _SECRET_QUERY.sub(r"\1[redacted]", text)


class RedactSecretsFilter(logging.Filter):
    """Redact in place and keep the record's shape: uvicorn's access formatter
    unpacks ``record.args`` as (client, method, path, version, status), so the
    args tuple must stay intact - only its string members are rewritten."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.args, tuple) and record.args:
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
            elif isinstance(record.msg, str):
                record.msg = redact(record.msg)
        except Exception:
            pass
        return True


def install() -> None:
    """Attach the filter to the loggers that print request paths."""
    flt = RedactSecretsFilter()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactSecretsFilter) for f in logger.filters):
            logger.addFilter(flt)
