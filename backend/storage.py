"""MongoDB GridFS storage helper for FIDEM."""
from __future__ import annotations

import logging
import os
from typing import Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from core import db

log = logging.getLogger(__name__)
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
    return "mongodb-gridfs"


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    bucket = AsyncIOMotorGridFSBucket(db, bucket_name="uploads")
    file_id = await bucket.upload_from_stream(
        path,
        data,
        metadata={
            "content_type": content_type,
            "app": APP_NAME,
        },
    )

    storage_path = str(file_id)

    return {
        "path": storage_path,
        "filename": path,
        "content_type": content_type,
        "size": len(data),
        "provider": "mongodb-gridfs",
    }


async def get_object(path: str) -> Tuple[bytes, str]:
    bucket = AsyncIOMotorGridFSBucket(db, bucket_name="uploads")
    grid_out = await bucket.open_download_stream(ObjectId(path))
    data = await grid_out.read()
    content_type = "application/octet-stream"

    if grid_out.metadata and grid_out.metadata.get("content_type"):
        content_type = grid_out.metadata["content_type"]

    return data, content_type
