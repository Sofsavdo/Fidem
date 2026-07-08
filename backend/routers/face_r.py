"""Face verification — uses OpenAI gpt-4o-mini vision via emergentintegrations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from ai_service import verify_face_photo
from core import db, iso, now_utc

router = APIRouter(tags=["face"])


class FaceVerifyRequest(BaseModel):
    photo_url: str | None = None
    photo_base64: str | None = None


@router.post("/face/verify")
async def face_verify(req: FaceVerifyRequest, uid: str = Depends(get_current_user_id)):
    if not req.photo_url and not req.photo_base64:
        raise HTTPException(400, "Rasm taqdim etilmadi")
    result = await verify_face_photo(
        image_url=req.photo_url or "",
        image_base64=req.photo_base64 or "",
    )
    # Persist last verification on user
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {
                "photo_verified": bool(result.get("valid")),
                "photo_verified_at": iso(now_utc()) if result.get("valid") else None,
                "photo_verification_code": result.get("code"),
            }
        },
    )
    return result
