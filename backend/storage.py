"""Cloudinary Object Storage helper for FIDEM."""
from __future__ import annotations

import base64
import logging
import os
import uuid

import httpx

log = logging.getLogger(__name__)

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
APP_NAME = os.environ.get("APP_NAME", "fidem")

MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
    "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
    "webm": "audio/webm", "m4a": "audio/mp4",
    "mp4": "video/mp4", "mov": "video/quicktime",
    "pdf": "application/pdf",
}


def init_storage(force: bool = False) -> str | None:
    if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
        return "cloudinary"
    log.warning("Cloudinary env not set; object storage disabled")
    return None


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    if not init_storage():
        raise RuntimeError("Storage not available")

    ext = path.split(".")[-1].lower() if "." in path else "jpg"
    public_id = f"{APP_NAME}/{path.rsplit('.', 1)[0]}-{uuid.uuid4().hex[:8]}"

    data_uri = f"data:{content_type};base64,{base64.b64encode(data).decode('utf-8')}"

    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/auto/upload"

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            url,
            data={
                "file": data_uri,
                "public_id": public_id,
                "overwrite": "true",
            },
            auth=(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET),
        )
        r.raise_for_status()
        res = r.json()

    return {
        "url": res.get("secure_url") or res.get("url"),
        "path": res.get("public_id"),
        "content_type": content_type,
        "size": len(data),
        "provider": "cloudinary",
    }


async def get_object(path: str) -> tuple[bytes, str]:
    raise RuntimeError("Direct get_object is not supported for Cloudinary. Use returned secure_url.")
