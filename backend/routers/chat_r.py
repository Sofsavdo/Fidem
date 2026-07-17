"""Messages, gifts, leaderboard, WebSocket."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response, WebSocket, WebSocketDisconnect

from auth import decode_token, get_current_user_id
from ai_service import detect_contact_info, quick_moderation
from core import (
    CHAT_GUARANTEE_HOURS,
    CHAT_UNLOCK_COINS,
    FREE_WEEKLY_INITIATIONS,
    PAID_PLANS,
    PRICE_CHAT_UNLOCK,
    chat_id_for,
    db,
    get_user,
    iso,
    log,
    manager,
    now_utc,
    parse_dt,
    push_notif,
    sanitize_text,
    strip_locked_photo,
    user_public,
)
from models import (
    GIFT_PRICES,
    LEGACY_GIFT_MAP,
    PLAN_GIFTS,
    ReportRequest,
    SaveRequest,
    SendGiftRequest,
    SendMessageRequest,
    new_id,
)

router = APIRouter(tags=["chat"])


# ---------- Chat access / monetization ----------
def _plan_active(user: dict) -> bool:
    return user.get("plan", "free") in PAID_PLANS


def _week_id() -> str:
    return now_utc().strftime("%G-W%V")


def free_weekly_left(user: dict) -> int:
    """Free first-conversation allowance remaining this week (read-only)."""
    if FREE_WEEKLY_INITIATIONS <= 0 or _plan_active(user):
        return 0
    used = user.get("free_init_used", 0) if user.get("free_init_week") == _week_id() else 0
    return max(0, FREE_WEEKLY_INITIATIONS - int(used or 0))


async def _consume_free_initiation(uid: str) -> bool:
    """Atomically spend one weekly free initiation. Returns True if one was
    available and consumed. Uses the same $-guarded conditional-update pattern
    as every other balance/quota deduction so concurrent sends can't over-spend.
    """
    if FREE_WEEKLY_INITIATIONS <= 0:
        return False
    week = _week_id()
    # Idempotent weekly reset — only rewrites when the stored week is stale.
    await db.users.update_one(
        {"id": uid, "free_init_week": {"$ne": week}},
        {"$set": {"free_init_week": week, "free_init_used": 0}},
    )
    res = await db.users.update_one(
        {"id": uid, "free_init_week": week, "free_init_used": {"$lt": FREE_WEEKLY_INITIATIONS}},
        {"$inc": {"free_init_used": 1}},
    )
    return res.modified_count == 1


async def _incoming_count(uid: str, target_id: str) -> int:
    cid = chat_id_for(uid, target_id)
    return await db.messages.count_documents({"chat_id": cid, "from_user_id": target_id})


async def _unlock_doc(uid: str, target_id: str):
    return await db.chat_unlocks.find_one({"user_id": uid, "target_id": target_id}, {"_id": 0})


async def _maybe_refund_guarantee(uid: str, target_id: str) -> bool:
    """48h no-reply guarantee: if a one-time paid unlock got no reply within the
    guarantee window, grant the user a free chat credit (once)."""
    unlock = await db.chat_unlocks.find_one({"user_id": uid, "target_id": target_id})
    if not unlock or unlock.get("source") != "one_time" or unlock.get("guarantee_refunded"):
        return False
    gu = unlock.get("guarantee_until")
    if not gu or parse_dt(gu) > now_utc():
        return False
    if await _incoming_count(uid, target_id) > 0:
        # got a reply — guarantee not triggered, close it out
        await db.chat_unlocks.update_one({"_id": unlock["_id"]}, {"$set": {"guarantee_refunded": True}})
        return False
    # No reply within window → grant a free chat credit
    await db.chat_unlocks.update_one({"_id": unlock["_id"]}, {"$set": {"guarantee_refunded": True}})
    await db.users.update_one({"id": uid}, {"$inc": {"free_chat_credits": 1}})
    await push_notif(uid, "balance", "48 soat ichida javob bo'lmadi — sizga 1 ta bepul suhbat krediti qaytarildi 🎁")
    return True


async def can_initiate_chat(sender: dict, target_id: str) -> bool:
    if _plan_active(sender):
        return True
    if await _incoming_count(sender["id"], target_id) > 0:
        return True
    if await _unlock_doc(sender["id"], target_id):
        return True
    # Check for mutual save (match) - free chat for matched users
    mutual_save = await db.saved.find_one({"owner_id": sender["id"], "target_id": target_id}) and await db.saved.find_one({"owner_id": target_id, "target_id": sender["id"]})
    if mutual_save:
        return True
    return False


@router.get("/chat/access/{target_id}")
async def chat_access(target_id: str, uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "self")
    # Blocked either way: the composer locks with a "blocked" state instead
    # of misleadingly showing the paywall.
    if await _block_exists(uid, target_id):
        me0 = await get_user(uid)
        return {
            "can_message": False, "blocked": True, "is_reply": False,
            "unlocked": False, "plan": me0.get("plan", "free"),
            "plan_active": _plan_active(me0), "requires_unlock": False,
            "price_uzs": 0, "price_coins": 0,
            "balance": int(me0.get("balance", 0) or 0),
            "coins": int(me0.get("coins", 0) or 0),
            "free_credits": 0, "free_weekly_left": 0,
            "uses_free_weekly": False, "guarantee_hours": CHAT_GUARANTEE_HOURS,
        }
    await _maybe_refund_guarantee(uid, target_id)
    me = await get_user(uid)
    is_reply = (await _incoming_count(uid, target_id)) > 0
    unlocked = bool(await _unlock_doc(uid, target_id))
    plan_ok = _plan_active(me)
    can_hard = await can_initiate_chat(me, target_id)
    fwl = free_weekly_left(me)
    # A free-weekly allowance also opens the composer (consumed on actual send),
    # but only when this isn't already covered by a plan/unlock/match/reply.
    uses_free_weekly = (not can_hard) and fwl > 0
    can = can_hard or uses_free_weekly
    return {
        "can_message": can,
        "is_reply": is_reply,
        "unlocked": unlocked,
        "plan": me.get("plan", "free"),
        "plan_active": plan_ok,
        "requires_unlock": not can,
        "price_uzs": 0 if can else PRICE_CHAT_UNLOCK,
        "price_coins": 0 if can else CHAT_UNLOCK_COINS,
        "balance": int(me.get("balance", 0) or 0),
        "coins": int(me.get("coins", 0) or 0),
        "free_credits": int(me.get("free_chat_credits", 0) or 0),
        "free_weekly_left": fwl,
        "uses_free_weekly": uses_free_weekly,
        "guarantee_hours": CHAT_GUARANTEE_HOURS,
    }


async def _create_unlock(uid: str, target_id: str, source: str, guarantee: bool) -> None:
    cid = chat_id_for(uid, target_id)
    doc = {
        "id": new_id(), "user_id": uid, "target_id": target_id, "chat_id": cid,
        "source": source, "created_at": iso(now_utc()),
        "guarantee_refunded": not guarantee,
    }
    if guarantee:
        doc["guarantee_until"] = iso(now_utc() + timedelta(hours=CHAT_GUARANTEE_HOURS))
    await db.chat_unlocks.update_one(
        {"user_id": uid, "target_id": target_id}, {"$setOnInsert": doc}, upsert=True
    )


@router.post("/chat/unlock")
async def chat_unlock(
    target_id: str = Body(..., embed=True),
    method: str = Body("balance", embed=True),
    uid: str = Depends(get_current_user_id),
):
    if target_id == uid:
        raise HTTPException(400, "Cannot unlock self")
    me = await get_user(uid)
    if _plan_active(me):
        return {"ok": True, "can_message": True, "note": "plan_active"}
    if await _unlock_doc(uid, target_id):
        return {"ok": True, "can_message": True, "note": "already"}
    await get_user(target_id)  # ensure target exists (404 otherwise)

    if method == "balance":
        res = await db.users.update_one(
            {"id": uid, "balance": {"$gte": PRICE_CHAT_UNLOCK}},
            {"$inc": {"balance": -PRICE_CHAT_UNLOCK}},
        )
        if res.modified_count == 0:
            raise HTTPException(402, "Insufficient balance")
        await _create_unlock(uid, target_id, "one_time", guarantee=True)
        return {"ok": True, "can_message": True, "method": "balance"}
    if method == "coins":
        res = await db.users.update_one(
            {"id": uid, "coins": {"$gte": CHAT_UNLOCK_COINS}},
            {"$inc": {"coins": -CHAT_UNLOCK_COINS}},
        )
        if res.modified_count == 0:
            raise HTTPException(402, "Insufficient coins")
        await _create_unlock(uid, target_id, "coins", guarantee=False)
        return {"ok": True, "can_message": True, "method": "coins"}
    if method == "credit":
        if int(me.get("free_chat_credits", 0) or 0) < 1:
            raise HTTPException(402, "No free credits")
        await db.users.update_one({"id": uid}, {"$inc": {"free_chat_credits": -1}})
        await _create_unlock(uid, target_id, "credit", guarantee=False)
        return {"ok": True, "can_message": True, "method": "credit"}
    raise HTTPException(400, "Unknown method (use balance|coins|credit, or /payments/create for CLICK)")


# ---------- Messages ----------
@router.get("/messages/chats")
async def list_chats(uid: str = Depends(get_current_user_id), limit: int = Query(20)):
    """List user's chats with pagination. Optimized with parallel queries."""
    limit = min(limit, 100)  # Cap at 100 per request

    pipeline = [
        {"$match": {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$chat_id", "last": {"$first": "$$ROOT"}}},
        {"$sort": {"last.created_at": -1}},
        {"$limit": limit},
    ]
    cursor = db.messages.aggregate(pipeline)
    rows_data = []
    async for row in cursor:
        rows_data.append(row)

    if not rows_data:
        return []

    other_ids = [
        row["last"]["to_user_id"] if row["last"]["from_user_id"] == uid else row["last"]["from_user_id"]
        for row in rows_data
    ]
    chat_ids = [row["_id"] for row in rows_data]

    # Parallel queries instead of sequential
    unlocks_task = db.photo_unlocks.find(
        {"requester_id": uid, "target_id": {"$in": other_ids}, "approved": True},
        {"_id": 0, "target_id": 1},
    ).to_list(len(other_ids))

    users_task = db.users.find(
        {"id": {"$in": other_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(other_ids))

    # For unread: use a simple count per chat, not full aggregation
    unread_tasks = [
        db.messages.count_documents({"chat_id": cid, "to_user_id": uid, "read": {"$ne": True}})
        for cid in chat_ids
    ]

    unlocks, users, *unread_counts = await asyncio.gather(
        unlocks_task, users_task, *unread_tasks
    )

    unlocked_set = {p["target_id"] for p in unlocks}
    users_by_id = {u["id"]: u for u in users}
    unread_by_chat = {cid: count for cid, count in zip(chat_ids, unread_counts)}

    items = []
    for row in rows_data:
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == uid else last["from_user_id"]
        u = users_by_id.get(other_id)
        if not u:
            continue
        pub = user_public(u)
        pub["photo_unlocked"] = other_id in unlocked_set
        items.append({
            "chat_id": row["_id"],
            "other": strip_locked_photo(pub),
            "last_message": {
                "id": last["id"], "text": last["text"],
                "kind": last.get("kind", "text"),
                "from_user_id": last["from_user_id"],
                "to_user_id": last["to_user_id"],
                "created_at": parse_dt(last["created_at"]),
            },
            "unread": unread_by_chat.get(row["_id"], 0),
            "status": last.get("status", "chat"),
        })
    return items


@router.get("/messages/applications")
async def list_applications(uid: str = Depends(get_current_user_id)):
    rows = await db.applications.find({"to_user_id": uid, "status": "pending"}, {"_id": 0}).to_list(200)
    from_ids = [r["from_user_id"] for r in rows]
    users = await db.users.find(
        {"id": {"$in": from_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(from_ids))
    users_by_id = {u["id"]: u for u in users}
    enriched = []
    for r in rows:
        u = users_by_id.get(r["from_user_id"])
        if u:
            enriched.append({"application": r, "from_user": user_public(u)})
    return enriched


@router.post("/messages/applications/{app_id}/decide")
async def decide_application(app_id: str, approve: bool = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    row = await db.applications.find_one({"id": app_id, "to_user_id": uid})
    if not row:
        raise HTTPException(404, "Application not found")
    await db.applications.update_one({"id": app_id}, {"$set": {"status": "approved" if approve else "rejected"}})
    if approve:
        approver = await get_user(uid)
        await push_notif(
            row["from_user_id"], "match",
            f"🎉 {approver.get('name', '')} murojaatingizni qabul qildi — endi yozishingiz mumkin!",
            link=f"/chat/{uid}",
        )
    return {"ok": True}


@router.get("/messages/{chat_id}")
async def chat_history(chat_id: str, uid: str = Depends(get_current_user_id), limit: int = Query(50)):
    """Load chat messages with pagination. Limit per request: 50 (capped at 100)."""
    a, b = chat_id.split("_", 1)
    if uid not in (a, b):
        raise HTTPException(403, "Not your chat")
    limit = min(limit, 100)
    rows = await db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    # Reverse to get chronological order (oldest first)
    rows.reverse()

    result = await db.messages.update_many(
        {"chat_id": chat_id, "to_user_id": uid, "read": {"$ne": True}},
        {"$set": {"read": True}},
    )
    if result.modified_count > 0:
        # Let the sender's open chat flip its own bubbles to "read" live,
        # instead of only finding out next time they reload the page.
        other_id = b if uid == a else a
        asyncio.create_task(
            manager.broadcast_chat([other_id], {"type": "read", "data": {"chat_id": chat_id, "reader_id": uid}})
        )
    for r in rows:
        r["created_at"] = parse_dt(r["created_at"])
    return rows


async def _block_exists(a: str, b: str) -> bool:
    """True when either side has blocked the other."""
    row = await db.blocks.find_one({
        "$or": [
            {"owner_id": a, "target_id": b},
            {"owner_id": b, "target_id": a},
        ]
    }, {"_id": 1})
    return bool(row)


@router.post("/messages/send")
async def send_message(req: SendMessageRequest, uid: str = Depends(get_current_user_id)):
    if req.to_user_id == uid:
        raise HTTPException(400, "Cannot message self")

    # Blocks were recorded but never enforced anywhere — a blocked user could
    # simply keep messaging. Refuse in both directions.
    if await _block_exists(uid, req.to_user_id):
        raise HTTPException(403, "blocked")

    sender_doc = await get_user(uid)
    if sender_doc.get("muted"):
        raise HTTPException(403, "muted")
    if not await can_initiate_chat(sender_doc, req.to_user_id):
        # Free-weekly allowance: a free user may open a limited number of new
        # conversations per week. Consume atomically, then record a free unlock
        # for this target so their follow-up messages here don't re-charge it.
        if await _consume_free_initiation(uid):
            await _create_unlock(uid, req.to_user_id, source="free_weekly", guarantee=False)
        else:
            raise HTTPException(402, "Chat locked - unlock required")

    is_voice = req.kind == "voice"
    is_video = req.kind == "video"

    if is_voice:
        if not req.voice_url:
            raise HTTPException(400, "voice_url required for voice message")
        if req.voice_duration and req.voice_duration > 60:
            raise HTTPException(400, "Voice message too long (max 60s)")
    elif is_video:
        if not req.video_url:
            raise HTTPException(400, "video_url required for video message")
        if req.video_duration and req.video_duration > 120:
            raise HTTPException(400, "Video message too long (max 120s)")
    else:
        # Sanitize text to prevent XSS
        sanitized_text = sanitize_text(req.text, allow_tags=False)
        ok, reason = quick_moderation(sanitized_text)
        if not ok:
            raise HTTPException(422, reason)
        # Off-platform contact exchange (phone / telegram / instagram / ...):
        # a paid perk. Free senders are refused with a code the frontend
        # turns into an upsell ("aloqa almashish pullik tariflarda"); paid
        # senders pass - the frontend already asked them to confirm.
        if detect_contact_info(sanitized_text) and sender_doc.get("plan", "free") not in PAID_PLANS:
            raise HTTPException(403, "contact_free_blocked")
        req.text = sanitized_text

    sender = sender_doc
    await get_user(req.to_user_id)
    cid = chat_id_for(uid, req.to_user_id)
    
    if is_voice:
        kind = "voice"
    elif is_video:
        kind = "video"
    else:
        kind = "text"
    status = "chat"

    msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "text": req.text or ("[voice]" if is_voice else "[video]" if is_video else ""),
        "kind": kind,
        "created_at": iso(now_utc()),
        "read": False,
        "status": status,
    }
    if is_voice:
        msg["meta"] = {"voice_url": req.voice_url, "voice_duration": req.voice_duration or 0}
    elif is_video:
        msg["meta"] = {
            "video_url": req.video_url,
            "video_duration": req.video_duration or 0,
            "video_thumbnail": req.video_thumbnail
        }
    
    # Insert message immediately for fast response
    await db.messages.insert_one(msg)
    msg.pop("_id", None)

    # Real-time delivery goes out first, straight from the request handler -
    # both parties (sender's own other tabs/devices included) see it within
    # milliseconds. Previously this waited behind the slower bookkeeping
    # below (applications record, response-time analytics), which could take
    # long enough that the sender's own optimistic UI had already cleared
    # before the WS echo arrived, making the just-sent message vanish.
    asyncio.create_task(manager.broadcast_chat([uid, req.to_user_id], {"type": "message", "data": dict(msg)}))
    asyncio.create_task(push_notif(
        req.to_user_id, "message",
        f"💬 {sender.get('name', '')} sizga yozdi — javob bering!",
        link=f"/chat/{uid}",
    ))

    # Slower bookkeeping - fine to trail behind, doesn't affect what either
    # party sees in the chat.
    asyncio.create_task(_background_message_ops(uid, req.to_user_id, cid, req.text, sender))

    return msg


async def _background_message_ops(uid: str, to_user_id: str, cid: str, text: str, sender: dict):
    """Background bookkeeping after message send - not on the delivery path."""
    try:
        existing_msgs = await db.messages.count_documents({"chat_id": cid})
        is_first = existing_msgs == 1
        is_reply = (await _incoming_count(uid, to_user_id)) > 0
        
        if is_first:
            await db.applications.update_one(
                {"from_user_id": uid, "to_user_id": to_user_id},
                {"$set": {
                    "id": new_id(), "from_user_id": uid, "to_user_id": to_user_id,
                    "status": "pending",
                    "created_at": iso(now_utc()), "text": text,
                }},
                upsert=True,
            )
        
        # Response time tracking
        if not is_first:
            last_incoming = await db.messages.find_one(
                {"chat_id": cid, "to_user_id": uid},
                sort=[("created_at", -1)],
                projection={"_id": 0, "created_at": 1, "from_user_id": 1},
            )
            if last_incoming and last_incoming.get("from_user_id") == to_user_id:
                try:
                    delta_min = (now_utc() - parse_dt(last_incoming["created_at"])).total_seconds() / 60.0
                    if 0 < delta_min < 7 * 24 * 60:
                        samples = (sender.get("response_samples") or []) + [round(delta_min, 1)]
                        samples = samples[-20:]
                        avg = round(sum(samples) / len(samples))
                        await db.users.update_one(
                            {"id": uid},
                            {"$set": {"response_samples": samples, "avg_response_min": avg}},
                        )
                except Exception:
                    pass
    except Exception:
        pass


@router.post("/messages/block")
async def block_user(req: SaveRequest, uid: str = Depends(get_current_user_id)):
    await db.blocks.update_one(
        {"owner_id": uid, "target_id": req.user_id},
        {"$set": {"owner_id": uid, "target_id": req.user_id, "at": iso(now_utc())}},
        upsert=True,
    )
    return {"ok": True}


@router.post("/messages/report")
async def report_user(req: ReportRequest, uid: str = Depends(get_current_user_id)):
    await db.reports.insert_one({
        "id": new_id(),
        "reporter_id": uid,
        "target_id": req.user_id,
        "reason": req.reason,
        "created_at": iso(now_utc()),
        "status": "open",
    })
    return {"ok": True}


@router.get("/chat/voice/{message_id}")
async def get_voice_file(
    message_id: str,
    auth: Optional[str] = Query(None),
    authorization: Optional[str] = Header(default=None),
):
    """Serve voice file for a message if the user is a chat participant.
    Accepts auth via Authorization header OR auth query parameter (for audio elements)."""
    # get_object lives in storage, not core — the old `from core import
    # get_object` raised ImportError and 500'd EVERY voice message playback.
    from storage import get_object

    # Extract token from header or query parameter
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif auth:
        token = auth

    if not token:
        raise HTTPException(401, "Auth required")

    payload = decode_token(token)
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token")

    # Fetch the message
    msg = await db.messages.find_one({"id": message_id}, {"_id": 0})
    if not msg:
        raise HTTPException(404, "Message not found")
    
    # Validate it's a voice message
    if msg.get("kind") != "voice" or not msg.get("meta", {}).get("voice_url"):
        raise HTTPException(400, "Not a voice message")
    
    # Validate user is a chat participant
    chat_id = msg.get("chat_id")
    if not chat_id:
        raise HTTPException(400, "Invalid message")
    
    parts = chat_id.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(400, "Invalid chat id")
    a, b = parts
    if uid not in (a, b):
        raise HTTPException(403, "Not your chat")
    
    # Extract storage path from voice_url
    voice_url = msg["meta"]["voice_url"]
    # voice_url format: /api/files/{storage_path} or full URL
    # Extract just the storage_path part
    if voice_url.startswith("/api/files/"):
        storage_path = voice_url.replace("/api/files/", "")
    elif voice_url.startswith("http"):
        # Full URL - extract path after /files/
        import re
        match = re.search(r"/files/(.+)$", voice_url)
        storage_path = match.group(1) if match else voice_url
    else:
        storage_path = voice_url
    
    # Fetch file from storage
    try:
        data, content_type = await get_object(storage_path)
    except Exception as e:
        raise HTTPException(500, f"Storage read failed: {e}")
    
    return Response(content=data, media_type=content_type or "audio/mpeg")


# ---------- Gifts ----------
@router.get("/gifts/catalog")
async def gifts_catalog(uid: str = Depends(get_current_user_id)):
    """Decorative gift catalog - see /gifts/plan-catalog for giftable
    subscriptions. No free tier: every gift here costs real balance."""
    me = await get_user(uid)
    items = []
    for kind, meta in GIFT_PRICES.items():
        items.append({
            "kind": kind,
            "emoji": meta["emoji"],
            "label_uz": meta["label_uz"],
            "label_ru": meta["label_ru"],
            "label_en": meta["label_en"],
            "price": meta["price"],
            "tier": meta["tier"],
            "category": "deco",
        })
    return {"items": items, "balance": me.get("balance", 0), "plan": me.get("plan", "free")}


@router.get("/gifts/plan-catalog")
async def gifts_plan_catalog(uid: str = Depends(get_current_user_id)):
    """Subscription plans/bundles offered as gifts. Always delivered
    immediately to a chosen recipient - gifting a plan to yourself is just
    buying it via /payments/create, so no inventory hold exists here."""
    me = await get_user(uid)
    items = []
    for kind, meta in PLAN_GIFTS.items():
        items.append({
            "kind": kind,
            "plan": meta["plan"],
            "months": meta["months"],
            "emoji": meta["emoji"],
            "label_uz": meta["label_uz"],
            "label_ru": meta["label_ru"],
            "label_en": meta["label_en"],
            "price": meta["price"],
            "category": "plan",
        })
    return {"items": items, "balance": me.get("balance", 0)}


def resolve_gift_kind(gift_kind: str) -> tuple[str, dict]:
    """Maps legacy kinds and validates against the decorative or plan-gift
    catalog. Raises 400 on anything invalid - shared by every gift-
    purchasing entry point. The returned meta always carries a "category"
    key ("deco"/"plan") so callers know whether to apply a subscription."""
    kind = LEGACY_GIFT_MAP.get(gift_kind, gift_kind)
    if kind in GIFT_PRICES:
        return kind, {**GIFT_PRICES[kind], "category": "deco"}
    if kind in PLAN_GIFTS:
        return kind, {**PLAN_GIFTS[kind], "category": "plan"}
    raise HTTPException(400, "Invalid gift")


async def charge_for_gift(uid: str, kind: str, meta: dict) -> None:
    """Deducts the cost of ONE gift from `uid`'s balance. Raises 402 if they
    can't afford it. Split out from the old send_gift() so the gift-shop's
    "buy now, give later" flow can charge once at purchase time and deliver
    separately (possibly days later) without re-charging."""
    price = meta["price"]
    res = await db.users.update_one(
        {"id": uid, "balance": {"$gte": price}},
        {"$inc": {"balance": -price, "gifts_sent_total": price, "gifts_sent_count": 1}},
    )
    if res.modified_count == 0:
        raise HTTPException(402, "Balansda mablag' yetarli emas")


PLAN_RANK = {"standard": 0, "premium": 1, "vip": 2}


async def _apply_plan_gift(to_user_id: str, plan: str, months: int) -> None:
    """Upgrades the recipient to `plan` for `months`*30 days. Never
    downgrades a plan they already have at that tier or better - it only
    stacks the extra time on top of their current expiry in that case."""
    recipient = await db.users.find_one({"id": to_user_id}, {"_id": 0, "plan": 1, "plan_until": 1})
    current_plan = (recipient or {}).get("plan") or "free"
    candidate_until = now_utc() + timedelta(days=months * 30)
    if current_plan in PLAN_RANK and PLAN_RANK[current_plan] >= PLAN_RANK.get(plan, -1):
        current_until = parse_dt(recipient["plan_until"]) if recipient.get("plan_until") else now_utc()
        final_plan = current_plan
        final_until = max(current_until, candidate_until) if current_until > now_utc() else candidate_until
    else:
        final_plan = plan
        final_until = candidate_until
    await db.users.update_one({"id": to_user_id}, {"$set": {"plan": final_plan, "plan_until": iso(final_until)}})
    if final_plan in ("premium", "vip"):
        await db.users.update_one({"id": to_user_id}, {"$set": {"boost_until": iso(now_utc() + timedelta(days=30))}})


async def deliver_gift(sender: dict, uid: str, to_user_id: str, kind: str, meta: dict, category: str) -> dict:
    """Records an already-paid-for gift as delivered to its recipient: the
    db.gifts ledger row (this is what the leaderboard sums), a chat message
    (gifting a total stranger from the gift shop just starts that chat, the
    same way an icebreaker would), a live WS push if they're online, and a
    notification. For a plan-category gift, also applies the subscription.
    Never touches balance - see charge_for_gift for that half."""
    price = meta["price"]
    await db.users.update_one({"id": to_user_id}, {"$inc": {"gifts_received_total": price}})
    if category == "plan":
        await _apply_plan_gift(to_user_id, meta["plan"], meta["months"])
        # A gifted subscription is real subscription-tier value, exactly like
        # buying one directly (process_completed_payment credits the buyer
        # there too) - attributed to the SENDER, who actually paid, not the
        # recipient. Without this, gifting someone VIP would never count
        # toward "paying_users"/ARPPU/conversion anywhere in the admin panel.
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": price, "lifetime_contribution_breakdown.subscription_payments": price}},
        )
    gift = {
        "id": new_id(),
        "from_user_id": uid,
        "to_user_id": to_user_id,
        "kind": kind,
        "price": price,
        "category": category,
        "created_at": iso(now_utc()),
    }
    await db.gifts.insert_one(gift)
    cid = chat_id_for(uid, to_user_id)
    gift_msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": to_user_id,
        "text": f"{meta['emoji']} {meta['label_uz']}",
        "kind": "gift",
        "meta": {"gift": kind, "price": price, "emoji": meta["emoji"], "label": meta["label_uz"], "category": category},
        "created_at": iso(now_utc()),
        "read": False,
    }
    await db.messages.insert_one(gift_msg)
    gift_msg.pop("_id", None)
    await manager.broadcast_chat([uid, to_user_id], {"type": "message", "data": gift_msg})
    verb = "sovg'a qildi" if category == "plan" else "yubordi"
    await push_notif(
        to_user_id, "gift",
        f"{meta['emoji']} {sender.get('name', '')} sizga {meta['label_uz']} {verb}!",
        link=f"/chat/{uid}",
    )
    return gift_msg["meta"]


@router.post("/gifts/send")
async def send_gift(req: SendGiftRequest, uid: str = Depends(get_current_user_id)):
    kind, meta = resolve_gift_kind(req.gift_kind)
    sender = await get_user(uid)
    await get_user(req.to_user_id)  # validates exists
    await charge_for_gift(uid, kind, meta)
    gift_meta = await deliver_gift(sender, uid, req.to_user_id, kind, meta, meta["category"])
    new_balance = sender.get("balance", 0) - meta["price"]
    return {"ok": True, "balance": new_balance, "gift": gift_meta}


# ---------- Leaderboard ----------
@router.get("/leaderboard")
async def leaderboard(period: str = "all", uid: str = Depends(get_current_user_id)):
    pipeline = [
        {"$group": {"_id": "$from_user_id", "total": {"$sum": "$price"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 50},
    ]
    if period == "day":
        cutoff = iso(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})
    elif period == "week":
        cutoff = iso(datetime.now(timezone.utc) - timedelta(days=7))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})
    elif period == "month":
        cutoff = iso(datetime.now(timezone.utc) - timedelta(days=30))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})

    groups = await db.gifts.aggregate(pipeline).to_list(50)
    # One batched lookup instead of a query per leaderboard row.
    users = await db.users.find(
        {"id": {"$in": [g["_id"] for g in groups]}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(groups)) if groups else []
    by_id = {u["id"]: u for u in users}

    rows = []
    for r in groups:
        u = by_id.get(r["_id"])
        # Hidden profiles opted out of all public visibility — rankings too.
        if u and not u.get("hidden_profile"):
            rows.append({"user": user_public(u), "total": r["total"], "count": r["count"]})
    return rows


# ---------- WebSocket ----------
@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        data = decode_token(token)
        uid = data["sub"]
    except Exception:
        await websocket.close(code=4401)
        return
    await manager.connect(uid, websocket)
    try:
        await websocket.send_json({"type": "connected", "user_id": uid})
        while True:
            # Keep-alive: discard incoming pings
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning(f"ws error: {e}")
    finally:
        await manager.disconnect(uid, websocket)
