"""Gift shop: a standalone catalog (bottom-nav "Sovg'alar" tab) distinct
from the in-chat gift button in chat_r.py. Two ways to buy:
  - pick a recipient up front -> charged and delivered immediately
    (reuses chat_r.charge_for_gift/deliver_gift, works for ANY user, not
    just an existing chat partner)
  - no recipient -> charged now, held in a personal "inventory" until
    redeemed to whoever, whenever, exactly once
Redeeming later delivers the SAME way an immediate purchase would (same
db.gifts ledger row, same chat message, same notification) so the
leaderboard and the recipient's experience are identical either path.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import age_from_birth, db, get_user, iso, now_utc
from models import GIFT_PRICES, GiftPurchaseRequest, GiftRedeemRequest, new_id
from routers.chat_r import charge_for_gift, deliver_gift, resolve_gift_kind

router = APIRouter(tags=["gift-shop"])


async def _blocked_pair(a: str, b: str) -> bool:
    exists = await db.blocks.find_one(
        {"$or": [{"owner_id": a, "target_id": b}, {"owner_id": b, "target_id": a}]},
        {"_id": 1},
    )
    return exists is not None


@router.get("/gifts/recipients")
async def gift_recipients(q: str = "", limit: int = 30, uid: str = Depends(get_current_user_id)):
    """Lightweight "who gets this gift" picker - deliberately leaner than
    /candidates (no matching/filters), and never leaks a private photo
    (only photo_public profiles show one here, matching strip_locked_photo's
    rule everywhere else)."""
    limit = max(1, min(limit, 50))
    exclude_ids = {uid}
    blocked_rows = await db.blocks.find(
        {"$or": [{"owner_id": uid}, {"target_id": uid}]}, {"_id": 0, "owner_id": 1, "target_id": 1}
    ).to_list(1000)
    for b in blocked_rows:
        exclude_ids.add(b["owner_id"])
        exclude_ids.add(b["target_id"])

    query: dict = {
        "onboarded": True,
        "blocked": {"$ne": True},
        "shadow_banned": {"$ne": True},
        "id": {"$nin": list(exclude_ids)},
    }
    q = q.strip()
    if q:
        query["name"] = {"$regex": re.escape(q), "$options": "i"}

    rows = await db.users.find(
        query,
        {"_id": 0, "id": 1, "name": 1, "birth_date": 1, "region": 1, "district": 1, "photo_url": 1, "photo_public": 1, "last_active": 1},
    ).limit(limit).to_list(limit)

    from core import is_online

    out = []
    for u in rows:
        out.append({
            "id": u["id"],
            "name": u.get("name", ""),
            "age": age_from_birth(u.get("birth_date", "2000-01-01")),
            "region": u.get("region", ""),
            "district": u.get("district", ""),
            "photo_url": u.get("photo_url") if u.get("photo_public") else None,
            "online": is_online(u.get("last_active")),
        })
    return out


@router.get("/gifts/inventory")
async def gift_inventory(uid: str = Depends(get_current_user_id)):
    """Gifts already paid for, sitting unused, waiting to be given to
    someone. Disappears from this list the moment it's redeemed."""
    rows = await db.gift_inventory.find(
        {"owner_id": uid, "status": "unused"}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    out = []
    for r in rows:
        meta = GIFT_PRICES.get(r["kind"], {})
        out.append({
            "id": r["id"],
            "kind": r["kind"],
            "emoji": meta.get("emoji", "🎁"),
            "label_uz": meta.get("label_uz", r["kind"]),
            "label_ru": meta.get("label_ru", r["kind"]),
            "label_en": meta.get("label_en", r["kind"]),
            "price": r["price"],
            "tier": meta.get("tier", "care"),
            "created_at": r["created_at"],
        })
    return {"items": out}


@router.post("/gifts/purchase")
async def gift_purchase(req: GiftPurchaseRequest, uid: str = Depends(get_current_user_id)):
    kind, meta = resolve_gift_kind(req.gift_kind)
    sender = await get_user(uid)

    if req.to_user_id:
        if req.to_user_id == uid:
            raise HTTPException(400, "O'zingizga sovg'a yubora olmaysiz")
        await get_user(req.to_user_id)  # validates exists
        if await _blocked_pair(uid, req.to_user_id):
            raise HTTPException(403, "Bu foydalanuvchiga sovg'a yubora olmaysiz")
        await charge_for_gift(uid, kind, meta)
        gift_meta = await deliver_gift(sender, uid, req.to_user_id, kind, meta, meta["category"])
        new_balance = sender.get("balance", 0) - meta["price"]
        return {"ok": True, "balance": new_balance, "delivered": True, "gift": gift_meta}

    if meta["category"] == "plan":
        # A gifted subscription is never held - "buy it for myself" is just
        # the regular /payments/create flow on the Premium page.
        raise HTTPException(400, "Obuna sovg'asi hoziroq kimgadir yuborilishi kerak")

    # No recipient chosen yet: charge now, hold in inventory for later.
    await charge_for_gift(uid, kind, meta)
    item = {
        "id": new_id(),
        "owner_id": uid,
        "kind": kind,
        "price": meta["price"],
        "status": "unused",
        "created_at": iso(now_utc()),
    }
    await db.gift_inventory.insert_one(item)
    new_balance = sender.get("balance", 0) - meta["price"]
    return {"ok": True, "balance": new_balance, "delivered": False, "inventory_id": item["id"]}


@router.post("/gifts/inventory/{item_id}/redeem")
async def gift_redeem(item_id: str, req: GiftRedeemRequest, uid: str = Depends(get_current_user_id)):
    if req.to_user_id == uid:
        raise HTTPException(400, "O'zingizga sovg'a yubora olmaysiz")
    sender = await get_user(uid)
    await get_user(req.to_user_id)  # validates exists
    if await _blocked_pair(uid, req.to_user_id):
        raise HTTPException(403, "Bu foydalanuvchiga sovg'a yubora olmaysiz")

    # Atomic claim: two taps on the same inventory item (or a retried
    # request) must not both deliver it - only the first "unused -> used"
    # transition succeeds.
    claim = await db.gift_inventory.find_one_and_update(
        {"id": item_id, "owner_id": uid, "status": "unused"},
        {"$set": {"status": "used", "used_at": iso(now_utc()), "used_for": req.to_user_id}},
    )
    if claim is None:
        raise HTTPException(404, "Bu sovg'a topilmadi yoki allaqachon ishlatilgan")

    kind, meta = resolve_gift_kind(claim["kind"])
    gift_meta = await deliver_gift(sender, uid, req.to_user_id, kind, meta, meta["category"])
    return {"ok": True, "gift": gift_meta}
