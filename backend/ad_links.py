"""Ad tracking links: which channel, blogger or post brought which people.

The admin creates a link per placement (e.g. "Toshkent oilaviy kanal").
Its code goes into the bot deep link `t.me/<bot>?start=ad_<code>` (or
`?startapp=ad_<code>`, which opens the Mini App straight away). Whoever
comes through it is tagged with that code, first touch only:

- bot_starts.ad_source: everyone who pressed START through the link
  (counted as "clicks"; people who already had an account are not counted);
- users.ad_source: the accounts created from it.

The admin panel then shows, per link: clicks, sign-ups (men / women),
finished profiles, selfie-verified, paying people and the money they paid,
and with the placement's cost, the cost per sign-up and per payer.
"""
from __future__ import annotations

import re

import core
from core import iso, now_utc

PREFIX = "ad_"
CODE_RE = re.compile(r"^[a-z0-9_]{2,32}$")


def code_from_start(start_param: str | None) -> str | None:
    """'ad_toshkent1' -> 'toshkent1'; None for any other start parameter."""
    if not start_param or not start_param.startswith(PREFIX):
        return None
    code = start_param[len(PREFIX):].lower()
    return code if CODE_RE.match(code) else None


def link_for(code: str) -> str:
    return f"https://t.me/{core.TELEGRAM_BOT_USERNAME}?start={PREFIX}{code}"


def app_link_for(code: str) -> str:
    return f"https://t.me/{core.TELEGRAM_BOT_USERNAME}?startapp={PREFIX}{code}"


def slugify(name: str) -> str:
    table = str.maketrans({"'": "", "’": "", "‘": "", "ʻ": "", "ʼ": "", "`": ""})
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").lower().translate(table)).strip("_")
    return s[:24] or "link"


async def known_code(code: str | None) -> str | None:
    if not code:
        return None
    doc = await core.db.ad_links.find_one({"code": code, "active": {"$ne": False}}, {"_id": 0, "code": 1})
    return doc["code"] if doc else None


async def record_bot_start(tg_user_id: str, code: str, has_account: bool) -> None:
    """A /start through an ad link. New people only, first link wins."""
    if has_account or not await known_code(code):
        return
    await core.db.bot_starts.update_one(
        {"telegram_id": tg_user_id, "ad_source": {"$exists": False}},
        {"$set": {"ad_source": code, "ad_at": iso(now_utc())}},
    )
    await core.db.pending_refs.update_one(
        {"telegram_id": tg_user_id, "ad_source": {"$exists": False}},
        {"$set": {"telegram_id": tg_user_id, "ad_source": code, "at": iso(now_utc())}},
        upsert=True,
    )


async def source_for_new_user(tg_user_id: str, start_param: str | None, pending: dict | None) -> str | None:
    """The ad code a just-created account came from: the bot /start link
    (pending_refs) or a Mini App link opened directly (initData start_param)."""
    if pending and pending.get("ad_source"):
        return pending["ad_source"]
    code = await known_code(code_from_start(start_param))
    if code:
        # Opened straight into the Mini App: count the click too.
        await core.db.bot_starts.update_one(
            {"telegram_id": tg_user_id},
            {"$set": {"ad_source": code, "ad_at": iso(now_utc())},
             "$setOnInsert": {"telegram_id": tg_user_id, "first_start_at": iso(now_utc()), "nudge_stage": 0,
                              "via_app_link": True}},
            upsert=True,
        )
    return code


# ---------- admin ----------
async def create(name: str, code: str = "", cost_uzs: int = 0, note: str = "") -> dict:
    name = (name or "").strip()[:80]
    if not name:
        raise ValueError("name_required")
    code = (code or "").strip().lower() or slugify(name)
    if not CODE_RE.match(code):
        raise ValueError("bad_code")
    base, n = code, 2
    while await core.db.ad_links.find_one({"code": code}, {"_id": 1}):
        code = f"{base[:29]}_{n}"
        n += 1
    doc = {"code": code, "name": name, "cost_uzs": max(0, int(cost_uzs or 0)), "note": (note or "")[:300],
           "active": True, "created_at": iso(now_utc())}
    await core.db.ad_links.insert_one(dict(doc))
    return doc


async def update(code: str, fields: dict) -> dict | None:
    upd = {}
    if "name" in fields and (fields["name"] or "").strip():
        upd["name"] = fields["name"].strip()[:80]
    if "cost_uzs" in fields and fields["cost_uzs"] is not None:
        upd["cost_uzs"] = max(0, int(fields["cost_uzs"]))
    if "note" in fields and fields["note"] is not None:
        upd["note"] = str(fields["note"])[:300]
    if "active" in fields and fields["active"] is not None:
        upd["active"] = bool(fields["active"])
    if upd:
        await core.db.ad_links.update_one({"code": code}, {"$set": upd})
    return await core.db.ad_links.find_one({"code": code}, {"_id": 0})


def _money(p: dict) -> int:
    """Real money a payment brought in (not purchases paid from the balance)."""
    if p.get("status") == "success":
        return max(0, int(p.get("amount") or 0) - int(p.get("balance_used") or 0))
    if p.get("status") == "paid" and p.get("method") == "manual_p2p":
        return int(p.get("amount") or 0)
    return 0


async def stats(code: str) -> dict:
    db = core.db
    clicks = await db.bot_starts.count_documents({"ad_source": code})
    users = await db.users.find(
        {"ad_source": code}, {"_id": 0, "id": 1, "gender": 1, "onboarded": 1, "verified_selfie": 1},
    ).to_list(100000)
    ids = [u["id"] for u in users]
    payers, revenue = set(), 0
    if ids:
        pays = await db.payments.find(
            {"user_id": {"$in": ids}, "status": {"$in": ["success", "paid"]}},
            {"_id": 0, "user_id": 1, "status": 1, "method": 1, "amount": 1, "balance_used": 1},
        ).to_list(100000)
        for p in pays:
            m = _money(p)
            if m > 0:
                payers.add(p["user_id"])
                revenue += m
    signups = len(users)
    return {
        "clicks": clicks,
        "signups": signups,
        "men": sum(1 for u in users if u.get("gender") == "male"),
        "women": sum(1 for u in users if u.get("gender") == "female"),
        "onboarded": sum(1 for u in users if u.get("onboarded")),
        "verified": sum(1 for u in users if u.get("verified_selfie")),
        "payers": len(payers),
        "revenue_uzs": revenue,
        "signup_pct": round(100 * signups / clicks) if clicks else 0,
    }


async def list_with_stats() -> list[dict]:
    rows = await core.db.ad_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    out = []
    for r in rows:
        s = await stats(r["code"])
        cost = int(r.get("cost_uzs") or 0)
        s["cost_per_signup"] = round(cost / s["signups"]) if cost and s["signups"] else None
        s["cost_per_payer"] = round(cost / s["payers"]) if cost and s["payers"] else None
        out.append({**r, "link": link_for(r["code"]), "app_link": app_link_for(r["code"]), "stats": s})
    return out
