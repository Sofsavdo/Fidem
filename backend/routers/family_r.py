"""Family contact share — VIP users can request exchange of parent phone numbers.
Both parties must be VIP and explicitly accept.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import chat_id_for, db, get_user, iso, log, manager, now_utc, push_notif
from models import new_id

router = APIRouter(prefix="/family", tags=["family"])


def _is_vip(u: dict) -> bool:
    return u.get("plan") == "vip"


@router.patch("/contacts")
async def set_family_contacts(
    parent_phone: str = Body(..., embed=True),
    parent_name: str = Body("", embed=True),
    parent_relation: str = Body("parent", embed=True),
    uid: str = Depends(get_current_user_id),
):
    phone = "".join(ch for ch in parent_phone if ch.isdigit() or ch == "+")
    if len(phone) < 9:
        raise HTTPException(400, "Telefon raqami noto'g'ri")
    await db.users.update_one(
        {"id": uid},
        {"$set": {
            "family_contact": {
                "phone": phone,
                "name": parent_name,
                "relation": parent_relation,
                "set_at": iso(now_utc()),
            }
        }},
    )
    return {"ok": True}


@router.get("/contacts/mine")
async def my_family_contact(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    return {"family_contact": me.get("family_contact")}


@router.post("/request")
async def request_family_share(
    target_user_id: str = Body(..., embed=True),
    note: str = Body("", embed=True),
    uid: str = Depends(get_current_user_id),
):
    if target_user_id == uid:
        raise HTTPException(400, "O'zingizga so'rov yubora olmaysiz")
    me = await get_user(uid)
    other = await get_user(target_user_id)
    if not _is_vip(me):
        raise HTTPException(403, "Faqat VIP foydalanuvchilar oilaviy aloqa so'rovini yubora oladi")
    if not me.get("family_contact"):
        raise HTTPException(400, "Avval o'z oilaviy aloqangizni kiriting (ota-ona telefoni)")
    # Prevent duplicate active request
    existing = await db.family_requests.find_one({
        "from_user_id": uid, "to_user_id": target_user_id, "status": {"$in": ["pending", "accepted"]}
    })
    if existing:
        raise HTTPException(400, "Avvalgi so'rov allaqachon mavjud")
    rid = new_id()
    doc = {
        "id": rid,
        "from_user_id": uid,
        "to_user_id": target_user_id,
        "note": note,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    await db.family_requests.insert_one(doc)
    await push_notif(
        target_user_id,
        "family_request",
        f"💍 {me.get('name','')} sizdan oilaviy aloqa (sovchilar telefonini almashish) so'radi",
        link="/family",
    )
    return {"ok": True, "id": rid}


@router.post("/respond/{request_id}")
async def respond_family_share(
    request_id: str,
    accept: bool = Body(..., embed=True),
    uid: str = Depends(get_current_user_id),
):
    req = await db.family_requests.find_one({"id": request_id})
    if not req:
        raise HTTPException(404, "So'rov topilmadi")
    if req["to_user_id"] != uid:
        raise HTTPException(403, "Bu so'rov sizniki emas")
    if req["status"] != "pending":
        raise HTTPException(400, "Allaqachon javob berilgan")
    me = await get_user(uid)
    if accept:
        if not _is_vip(me):
            raise HTTPException(403, "Oilaviy aloqa qabul qilish uchun siz ham VIP bo'lishingiz kerak")
        if not me.get("family_contact"):
            raise HTTPException(400, "Avval o'z oilaviy aloqangizni kiriting")
        await db.family_requests.update_one(
            {"id": request_id},
            {"$set": {"status": "accepted", "responded_at": iso(now_utc())}},
        )
        await push_notif(
            req["from_user_id"],
            "family_accepted",
            f"✅ {me.get('name','')} oilaviy aloqani qabul qildi! Telefonlar ko'rinishga tayyor.",
            link="/family",
        )
    else:
        await db.family_requests.update_one(
            {"id": request_id},
            {"$set": {"status": "rejected", "responded_at": iso(now_utc())}},
        )
    return {"ok": True}


@router.get("/mine")
async def my_family_requests(uid: str = Depends(get_current_user_id)):
    sent = await db.family_requests.find({"from_user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    received = await db.family_requests.find({"to_user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)

    peer_ids = {r["to_user_id"] for r in sent} | {r["from_user_id"] for r in received}
    peers = await db.users.find(
        {"id": {"$in": list(peer_ids)}}, {"_id": 0, "name": 1, "photo_url": 1, "id": 1, "plan": 1}
    ).to_list(len(peer_ids))
    peers_by_id = {p["id"]: p for p in peers}

    def enrich(rows: list, peer_key: str):
        for r in rows:
            r["peer"] = peers_by_id.get(r[peer_key])
        return rows

    return {
        "sent": enrich(sent, "to_user_id"),
        "received": enrich(received, "from_user_id"),
    }


@router.get("/contact/{other_user_id}")
async def get_shared_contact(other_user_id: str, uid: str = Depends(get_current_user_id)):
    """Returns the family contact of the OTHER user if both sides accepted a request."""
    accepted = await db.family_requests.find_one({
        "status": "accepted",
        "$or": [
            {"from_user_id": uid, "to_user_id": other_user_id},
            {"from_user_id": other_user_id, "to_user_id": uid},
        ],
    })
    if not accepted:
        raise HTTPException(403, "Hali oilaviy aloqa o'rnatilmagan")
    other = await get_user(other_user_id)
    fc = other.get("family_contact")
    if not fc:
        raise HTTPException(404, "U yana oilaviy aloqasini kiritmagan")
    return {"family_contact": fc, "name": other.get("name", "")}
