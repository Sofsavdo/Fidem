"""Unit tests for sofsavdo_integration.py - the Fidem -> Sofsavdo conversion
webhook emitter. Fire-and-forget by design (see the module docstring), so the
main thing worth locking down here is that it never raises: a broken webhook
must never take down a real payment."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sofsavdo_integration as si  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    """Minimal async-context-manager stand-in for httpx.AsyncClient."""

    def __init__(self, response: Optional[_FakeResponse] = None, raise_exc: Optional[Exception] = None):
        self._response = response
        self._raise_exc = raise_exc
        self.posted = None

    def __call__(self, *_a, **_kw):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, url, json=None):
        self.posted = (url, json)
        if self._raise_exc:
            raise self._raise_exc
        return self._response


def test_skips_when_secret_unset(monkeypatch):
    monkeypatch.setattr(si, "SOFSAVDO_INTEGRATION_SECRET", "")
    fake_client = _FakeAsyncClient(_FakeResponse(200))
    with patch("httpx.AsyncClient", fake_client):
        asyncio.run(si.report_sofsavdo_conversion("sf_flow1_1_abc", "txn_1", 50000, "premium"))
    assert fake_client.posted is None, "must never call out when unconfigured"


def test_posts_a_correctly_signed_body(monkeypatch):
    monkeypatch.setattr(si, "SOFSAVDO_INTEGRATION_SECRET", "test-secret")
    fake_client = _FakeAsyncClient(_FakeResponse(200))
    with patch("httpx.AsyncClient", fake_client):
        asyncio.run(si.report_sofsavdo_conversion("sf_flow1_1_abc", "txn_1", 50000, "premium"))

    assert fake_client.posted is not None
    url, body = fake_client.posted
    assert url == si.SOFSAVDO_WEBHOOK_URL
    assert body["clickToken"] == "sf_flow1_1_abc"
    assert body["externalPaymentId"] == "txn_1"
    assert body["amountMinor"] == 5_000_000  # 50,000 so'm -> tiyin
    assert body["currency"] == "UZS"
    assert body["planName"] == "premium"
    expected_sig = si._sign("sf_flow1_1_abc", "txn_1", 5_000_000, body["occurredAt"])
    assert body["signature"] == expected_sig


def test_swallows_a_non_2xx_response(monkeypatch):
    monkeypatch.setattr(si, "SOFSAVDO_INTEGRATION_SECRET", "test-secret")
    fake_client = _FakeAsyncClient(_FakeResponse(400, "bad request"))
    with patch("httpx.AsyncClient", fake_client):
        asyncio.run(si.report_sofsavdo_conversion("sf_flow1_1_abc", "txn_1", 50000, "premium"))  # must not raise


def test_swallows_a_network_error(monkeypatch):
    monkeypatch.setattr(si, "SOFSAVDO_INTEGRATION_SECRET", "test-secret")
    fake_client = _FakeAsyncClient(raise_exc=ConnectionError("network down"))
    with patch("httpx.AsyncClient", fake_client):
        asyncio.run(si.report_sofsavdo_conversion("sf_flow1_1_abc", "txn_1", 50000, "premium"))  # must not raise
