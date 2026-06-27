"""Messages, gifts, leaderboard, WebSocket."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query

from auth import decode_token, get_current_user_id
from ai_service import quick_moderation
from core import (
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
from routers.candidates_r import candidate_can_message

router = APIRouter(tags=["chat"])


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
    async for row in cursor:
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == uid else last["from_user_id"]
        u = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
        if not u:
            continue
        unread = await db.messages.count_documents(
            {"chat_id": row["_id"], "to_user_id": uid, "read": {"$ne": True}}
        )
        items.append({
            "chat_id": row["_id"],
            "other": user_public(u),
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
    target = await get_user(req.to_user_id)
    cid = chat_id_for(uid, req.to_user_id)
    existing_msgs = await db.messages.count_documents({"chat_id": cid})
    can_msg = candidate_can_message(target, sender)
    is_first = existing_msgs == 0
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
    elif not can_msg:
        raise HTTPException(403, "You don't pass recipient's filters. Use super application.")
    elif is_first:
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
        # 50% of gift price converts to recipient's withdrawable balance (Bigo model)
        recipient_share = price // 2
        await db.users.update_one(
            {"id": uid}, {"$inc": {"balance": -price, "gifts_sent_total": price, "gifts_sent_count": 1}}
        )
        await db.users.update_one(
            {"id": req.to_user_id},
            {"$inc": {"gifts_received_total": price, "withdrawable_balance": recipient_share}},
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
    await push_notif(req.to_user_id, "gift", f"Sizga {meta['emoji']} {meta['label_uz']} sovg'a yuborildi", link="/chat?id=" + cid)
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
