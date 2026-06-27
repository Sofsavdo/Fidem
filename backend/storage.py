"""Emergent Object Storage helper."""
from __future__ import annotations
import logging
import os
import threading

import httpx

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = os.environ.get("APP_NAME", "fidem")

log = logging.getLogger(__name__)
_storage_key: str | None = None
_lock = threading.Lock()


def init_storage(force: bool = False) -> str | None:
    """Initialize storage session once. Returns storage_key or None on failure."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    if not EMERGENT_KEY:
        log.warning("EMERGENT_LLM_KEY not set; object storage disabled")
        return None
    with _lock:
        if _storage_key and not force:
            return _storage_key
        try:
            r = httpx.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
            r.raise_for_status()
            _storage_key = r.json()["storage_key"]
            log.info("Object storage initialized")
            return _storage_key
        except Exception as e:
            log.error(f"Storage init failed: {e}")
            return None


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise RuntimeError("Storage not available")
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            content=data,
        )
        if r.status_code == 403:
            init_storage(force=True)
            r = await client.put(
                f"{STORAGE_URL}/objects/{path}",
                headers={"X-Storage-Key": init_storage(), "Content-Type": content_type},
                content=data,
            )
        r.raise_for_status()
        return r.json()


async def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    if not key:
        raise RuntimeError("Storage not available")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
        )
        if r.status_code == 403:
            init_storage(force=True)
            r = await client.get(
                f"{STORAGE_URL}/objects/{path}",
                headers={"X-Storage-Key": init_storage()},
            )
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")


MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}
