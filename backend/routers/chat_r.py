"""Messages, gifts, leaderboard, WebSocket."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query

from auth import decode_token, get_current_user_id
from ai_service import quick_moderation
from core import (
    CHAT_GUARANTEE_HOURS,
    CHAT_UNLOCK_COINS,
    PAID_PLANS,
    PRICE_CHAT_UNLOCK,
    PRICE_SUPER,
    chat_id_for,
    db,
    get_user,
    iso,
    log,
    manager,
    now_utc,
    parse_dt,
    push_notif,
    strip_locked_photo,
    user_public,
)
from models import (
    FREE_GIFTS_BY_PLAN,
    GIFT_EMOJI,
    GIFT_LABEL_UZ,
    GIFT_PRICES,
    LEGACY_GIFT_MAP,
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
    return False


@router.get("/chat/access/{target_id}")
async def chat_access(target_id: str, uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "self")
    await _maybe_refund_guarantee(uid, target_id)
    me = await get_user(uid)
    is_reply = (await _incoming_count(uid, target_id)) > 0
    unlocked = bool(await _unlock_doc(uid, target_id))
    plan_ok = _plan_active(me)
    can = plan_ok or is_reply or unlocked
    return {
        "can_message": can,
        "is_reply": is_reply,
        "unlocked": unlocked,
        "plan": me.get("plan", "free"),
        "plan_active": plan_ok,
        "requires_unlock": not can,
        "price_uzs": PRICE_CHAT_UNLOCK,
        "price_coins": CHAT_UNLOCK_COINS,
        "balance": int(me.get("balance", 0) or 0),
        "coins": int(me.get("coins", 0) or 0),
        "free_credits": int(me.get("free_chat_credits", 0) or 0),
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
        if int(me.get("balance", 0) or 0) < PRICE_CHAT_UNLOCK:
            raise HTTPException(402, "Insufficient balance")
        await db.users.update_one({"id": uid}, {"$inc": {"balance": -PRICE_CHAT_UNLOCK}})
        await _create_unlock(uid, target_id, "one_time", guarantee=True)
        return {"ok": True, "can_message": True, "method": "balance"}
    if method == "coins":
        if int(me.get("coins", 0) or 0) < CHAT_UNLOCK_COINS:
            raise HTTPException(402, "Insufficient coins")
        await db.users.update_one({"id": uid}, {"$inc": {"coins": -CHAT_UNLOCK_COINS}})
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
async def list_chats(uid: str = Depends(get_current_user_id)):
    pipeline = [
        {"$match": {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$chat_id", "last": {"$first": "$$ROOT"}}},
        {"$sort": {"last.created_at": -1}},
    ]
    cursor = db.messages.aggregate(pipeline)
    items = []
    rows_data = []
    async for row in cursor:
        rows_data.append(row)
    other_ids = []
    for row in rows_data:
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == uid else last["from_user_id"]
        other_ids.append(other_id)
    unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "target_id": {"$in": other_ids}, "approved": True},
        {"_id": 0, "target_id": 1},
    ).to_list(500) if other_ids else []
    unlocked_set = {p["target_id"] for p in unlocks}
    for row in rows_data:
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == uid else last["from_user_id"]
        u = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
        if not u:
            continue
        unread = await db.messages.count_documents(
            {"chat_id": row["_id"], "to_user_id": uid, "read": {"$ne": True}}
        )
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
            "unread": unread,
            "status": last.get("status", "chat"),
        })
    return items


@router.get("/messages/applications")
async def list_applications(uid: str = Depends(get_current_user_id)):
    rows = await db.applications.find({"to_user_id": uid, "status": "pending"}, {"_id": 0}).to_list(200)
    enriched = []
    for r in rows:
        u = await db.users.find_one({"id": r["from_user_id"]}, {"_id": 0, "password_hash": 0})
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
        await push_notif(row["from_user_id"], "match", "Sizning murojaatingiz qabul qilindi 🎉")
    return {"ok": True}


@router.get("/messages/{chat_id}")
async def chat_history(chat_id: str, uid: str = Depends(get_current_user_id)):
    a, b = chat_id.split("_", 1)
    if uid not in (a, b):
        raise HTTPException(403, "Not your chat")
    rows = await db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    await db.messages.update_many({"chat_id": chat_id, "to_user_id": uid}, {"$set": {"read": True}})
    for r in rows:
        r["created_at"] = parse_dt(r["created_at"])
    return rows


@router.post("/messages/send")
async def send_message(req: SendMessageRequest, uid: str = Depends(get_current_user_id)):
    if req.to_user_id == uid:
        raise HTTPException(400, "Cannot message self")
    is_voice = req.kind == "voice"
    if is_voice:
        if not req.voice_url:
            raise HTTPException(400, "voice_url required for voice message")
        # No moderation on voice (binary content); just length sanity
        if req.voice_duration and req.voice_duration > 60:
            raise HTTPException(400, "Voice message too long (max 60s)")
    else:
        # AI moderation (fast check) — text only
        ok, reason = quick_moderation(req.text)
        if not ok:
            raise HTTPException(422, reason)
    sender = await get_user(uid)
    await get_user(req.to_user_id)  # ensure target exists
    cid = chat_id_for(uid, req.to_user_id)
    existing_msgs = await db.messages.count_documents({"chat_id": cid})
    is_first = existing_msgs == 0
    is_reply = (await _incoming_count(uid, req.to_user_id)) > 0
    if is_voice:
        kind = "voice"
    else:
        kind = "super" if req.is_super else "text"
    status = "chat"

    if req.is_super:
        if sender.get("balance", 0) < PRICE_SUPER:
            raise HTTPException(402, "Insufficient balance for super application")
        await db.users.update_one({"id": uid}, {"$inc": {"balance": -PRICE_SUPER}})
        status = "application"
    elif is_reply:
        # Replying to someone who already wrote to you is always free.
        pass
    else:
        # Initiating a new conversation requires an active paid plan or a chat unlock.
        if not (_plan_active(sender) or await _unlock_doc(uid, req.to_user_id)):
            raise HTTPException(402, "chat_locked")
        if is_first:
            status = "application"

    msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "text": req.text or ("[voice]" if is_voice else ""),
        "kind": kind,
        "created_at": iso(now_utc()),
        "read": False,
        "status": status,
    }
    if is_voice:
        msg["meta"] = {"voice_url": req.voice_url, "voice_duration": req.voice_duration or 0}
    await db.messages.insert_one(msg)
    msg.pop("_id", None)
    if is_first or req.is_super:
        await db.applications.update_one(
            {"from_user_id": uid, "to_user_id": req.to_user_id},
            {"$set": {
                "id": new_id(), "from_user_id": uid, "to_user_id": req.to_user_id,
                "is_super": req.is_super, "status": "pending",
                "created_at": iso(now_utc()), "text": req.text,
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
        if last_incoming and last_incoming.get("from_user_id") == req.to_user_id:
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
    # WebSocket push: deliver to BOTH parties (so sender's other tabs update too)
    ws_payload = {"type": "message", "data": {**msg, "created_at": iso(parse_dt(msg["created_at"]))}}
    await manager.broadcast_chat([uid, req.to_user_id], ws_payload)
    # Also notify chaperones (read-only) of both sender and recipient
    try:
        chap_rows = await db.chaperones.find(
            {"$or": [{"owner_id": uid}, {"owner_id": req.to_user_id}], "status": "active"},
            {"_id": 0, "wali_id": 1},
        ).to_list(50)
        chaperone_ids = list({c["wali_id"] for c in chap_rows})
        if chaperone_ids:
            await manager.broadcast_chat(chaperone_ids, {"type": "chaperone_message", "data": ws_payload["data"]})
    except Exception:
        pass

    await push_notif(req.to_user_id, "message", f"Yangi xabar: {sender.get('name','')}")
    msg["created_at"] = parse_dt(msg["created_at"])
    return msg


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
    from fastapi import Response, Query, Header
    from auth import decode_token
    from core import get_object

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
    """Return full gift catalog with current free-quota status."""
    me = await get_user(uid)
    plan = me.get("plan", "free")
    week_id = now_utc().strftime("%G-W%V")
    used = me.get("free_gifts_used", {}) or {}
    week_used = used.get(week_id, 0) if isinstance(used, dict) else 0
    quota_per_week = FREE_GIFTS_BY_PLAN.get(plan, 1)
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
            "free": meta.get("tier") == "free",
        })
    return {
        "items": items,
        "free_quota_per_week": quota_per_week,
        "free_used_this_week": week_used,
        "free_remaining": max(0, quota_per_week - week_used),
        "balance": me.get("balance", 0),
        "plan": plan,
    }


@router.post("/gifts/send")
async def send_gift(req: SendGiftRequest, uid: str = Depends(get_current_user_id)):
    # Map legacy gift kinds
    kind = LEGACY_GIFT_MAP.get(req.gift_kind, req.gift_kind)
    meta = GIFT_PRICES.get(kind)
    if not meta:
        raise HTTPException(400, "Invalid gift")
    price = meta["price"]
    sender = await get_user(uid)
    is_free_gift = meta.get("tier") == "free"
    # Validate free-quota for free gifts
    if is_free_gift:
        plan = sender.get("plan", "free")
        week_id = now_utc().strftime("%G-W%V")
        used_map = sender.get("free_gifts_used", {}) or {}
        if not isinstance(used_map, dict):
            used_map = {}
        week_used = used_map.get(week_id, 0)
        quota = FREE_GIFTS_BY_PLAN.get(plan, 1)
        if week_used >= quota:
            raise HTTPException(402, f"Bu hafta uchun bepul sovg'a kvotangiz tugadi ({quota} ta). Pulli gift yuboring yoki kelasi haftani kuting.")
    elif sender.get("balance", 0) < price:
        raise HTTPException(402, "Balansda mablag' yetarli emas")
    await get_user(req.to_user_id)  # validates exists
    # Apply balance/quota change
    if is_free_gift:
        week_id = now_utc().strftime("%G-W%V")
        await db.users.update_one(
            {"id": uid},
            {"$inc": {f"free_gifts_used.{week_id}": 1, "gifts_sent_count": 1}},
        )
    else:
        # Gifts are NOT withdrawable (V3.2 economy system)
        await db.users.update_one(
            {"id": uid}, {"$inc": {"balance": -price, "gifts_sent_total": price, "gifts_sent_count": 1}}
        )
        await db.users.update_one(
            {"id": req.to_user_id},
            {"$inc": {"gifts_received_total": price}},
        )
    gift = {
        "id": new_id(),
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "kind": kind,
        "price": price,
        "is_free": is_free_gift,
        "created_at": iso(now_utc()),
    }
    await db.gifts.insert_one(gift)
    cid = chat_id_for(uid, req.to_user_id)
    gift_msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "text": f"{meta['emoji']} {meta['label_uz']}",
        "kind": "gift",
        "meta": {"gift": kind, "price": price, "emoji": meta["emoji"], "label": meta["label_uz"], "is_free": is_free_gift},
        "created_at": iso(now_utc()),
        "read": False,
    }
    await db.messages.insert_one(gift_msg)
    gift_msg.pop("_id", None)
    await manager.broadcast_chat([uid, req.to_user_id], {"type": "message", "data": gift_msg})
    await push_notif(req.to_user_id, "gift", f"Sizga {meta['emoji']} {meta['label_uz']} sovg'a yuborildi", link=f"/chat/{uid}")
    new_balance = sender.get("balance", 0) if is_free_gift else (sender.get("balance", 0) - price)
    return {"ok": True, "balance": new_balance, "gift": gift_msg["meta"]}


# ---------- Leaderboard ----------
@router.get("/leaderboard")
async def leaderboard(period: str = "all"):
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

    rows = []
    async for r in db.gifts.aggregate(pipeline):
        u = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "password_hash": 0})
        if u:
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
