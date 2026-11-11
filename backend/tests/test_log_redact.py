"""Session tokens in query strings must never reach the log output."""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import log_redact  # noqa: E402

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1MSJ9.abc-DEF_123"


def test_redact_handles_token_auth_and_keeps_other_params():
    assert log_redact.redact(f"/api/ws?token={JWT}") == "/api/ws?token=[redacted]"
    assert log_redact.redact(f"/api/chat/voice/x?auth={JWT}&lang=uz") == "/api/chat/voice/x?auth=[redacted]&lang=uz"
    assert log_redact.redact("/api/candidates?sort=match&verified_only=false") == "/api/candidates?sort=match&verified_only=false"
    assert JWT not in log_redact.redact(f'"WebSocket /api/ws?x=1&TOKEN={JWT}" [accepted]')


def test_filter_redacts_uvicorn_style_records(caplog):
    log_redact.install()
    log_redact.install()  # idempotent
    logger = logging.getLogger("uvicorn.access")
    assert sum(isinstance(f, log_redact.RedactSecretsFilter) for f in logger.filters) == 1

    seen = []

    class Capture(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())

    handler = Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        # uvicorn.access formats via args: client, method, path, version, status
        logger.info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:5", "GET", f"/api/ws?token={JWT}", "1.1", 200)
    finally:
        logger.removeHandler(handler)
    assert seen and JWT not in seen[0] and "[redacted]" in seen[0]


def test_uvicorn_access_formatter_still_works_after_redaction():
    from uvicorn.logging import AccessFormatter

    log_redact.install()
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("1.2.3.4:5", "GET", f"/api/ws?token={JWT}", "1.1", 200), None,
    )
    for f in logging.getLogger("uvicorn.access").filters:
        f.filter(record)
    out = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s').format(record)
    assert JWT not in out
    assert "/api/ws?token=[redacted]" in out
