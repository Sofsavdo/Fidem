"""FIDEM backend entrypoint — thin app + lifespan + router mounting."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("fidem")
# httpx logs every request URL at INFO - for Telegram that URL contains the
# bot token (".../bot<TOKEN>/sendMessage"), which would end up in the hosting
# provider's logs. Keep those loggers quiet.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# Session tokens travel in some query strings (WebSocket, media); uvicorn would
# log them verbatim. Redact before they reach the log stream.
from log_redact import install as _install_log_redaction  # noqa: E402

_install_log_redaction()

if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )

from core import (  # noqa: E402  (must load env first)
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    client,
    db,
    hash_pw,
    iso,
    now_utc,
    rate_limiter_gc_loop,
)
from models import new_id  # noqa: E402
from routers.admin_r import router as admin_router  # noqa: E402
from routers.analytics_r import router as analytics_router  # noqa: E402
from routers.auth_r import router as auth_router  # noqa: E402
from routers.candidates_r import router as candidates_router  # noqa: E402
from routers.chat_r import router as chat_router  # noqa: E402
from routers.growth_r import router as growth_router  # noqa: E402
from routers.payments_r import router as payments_router  # noqa: E402
from routers.telegram_r import router as telegram_router, setup_telegram_webhook  # noqa: E402
from routers.admin_telegram_r import router as admin_telegram_router, setup_admin_telegram_webhook  # noqa: E402
from routers.personality_r import router as personality_router  # noqa: E402
from routers.prompts_r import router as prompts_router  # noqa: E402
from routers.stories_r import router as stories_router  # noqa: E402
from routers.withdrawals_r import router as withdrawals_router  # noqa: E402
from routers.family_r import router as family_router  # noqa: E402
from routers.concierge_r import router as concierge_router  # noqa: E402
from routers.boost_analytics_r import router as boost_analytics_router  # noqa: E402
from routers.face_r import router as face_router  # noqa: E402
from routers.location_r import router as location_router  # noqa: E402
from routers.settings_r import router as settings_router  # noqa: E402
from routers.picks_r import router as picks_router  # noqa: E402
from routers.announcements_r import router as announcements_router  # noqa: E402
from routers.gift_shop_r import router as gift_shop_router  # noqa: E402
from lifecycle import lifecycle_loop  # noqa: E402
from referral_earnings import referral_release_loop  # noqa: E402
from services import compute_completeness  # noqa: E402
from storage import init_storage  # noqa: E402
from winback import winback_loop  # noqa: E402

app = FastAPI(title="FIDEM API")

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(candidates_router)
api.include_router(chat_router)
api.include_router(growth_router)
api.include_router(payments_router)
api.include_router(admin_router)
api.include_router(analytics_router)
api.include_router(telegram_router)
api.include_router(admin_telegram_router)
api.include_router(personality_router)
api.include_router(prompts_router)
api.include_router(stories_router)
api.include_router(withdrawals_router)
api.include_router(family_router)
api.include_router(concierge_router)
api.include_router(boost_analytics_router)
api.include_router(face_router)
api.include_router(location_router)
api.include_router(settings_router)
api.include_router(picks_router)
api.include_router(announcements_router)
api.include_router(gift_shop_router)
app.include_router(api)


@app.get("/")
async def root():
    return {"status": "ok", "service": "fidem-backend"}


@app.on_event("startup")
async def startup() -> None:
    try:
        init_storage()
    except Exception as e:
        log.warning(f"Storage init: {e}")

    # Set Telegram webhook in background (non-fatal)
    asyncio.create_task(setup_telegram_webhook())
    asyncio.create_task(setup_admin_telegram_webhook())
    # One small real AI call: its result goes to the log and the admin panel.
    from ai_service import ai_self_check_loop
    asyncio.create_task(ai_self_check_loop())
    from hamyon import hamyon_enabled
    log.info("Payments: Hamyon %s", "ON" if hamyon_enabled() else "OFF (HAMYON_SHOP_ID / HAMYON_SHOP_KEY not set)")

    # Re-engagement notifications for inactive users - runs on its own
    # interval for the life of the process, no external cron needed.
    asyncio.create_task(winback_loop())

    # Plan expiry reminders/downgrades, daily picks pushes, weekly digests.
    asyncio.create_task(lifecycle_loop())

    # Promotes paid-subscription referral earnings from pending to
    # withdrawable once their fraud-buffer hold expires - nothing else does
    # this, so without it referral cash could never actually be withdrawn.
    asyncio.create_task(referral_release_loop())

    # Keeps the in-memory rate-limit buckets from growing forever.
    asyncio.create_task(rate_limiter_gc_loop())

    # AI photo verification (ai_service.verify_face_photo) needs this key.
    # Without it every verification call fails as "verification_unavailable",
    # which deliberately lets users through UNVERIFIED so signups don't break
    # - but it means no photo is actually being checked. Shout about it.
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning(
            "Neither GEMINI_API_KEY nor ANTHROPIC_API_KEY is set - AI photo "
            "verification and AI verification review are effectively DISABLED "
            "(all photos pass through unverified, all verifications stay "
            "pending for manual review). Set GEMINI_API_KEY to enable them."
        )

    # Indexes
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", sparse=True)
    await db.users.create_index("telegram_id", sparse=True)
    await db.users.create_index("onboarded")
    await db.users.create_index("plan")
    await db.users.create_index("is_demo", sparse=True)
    await db.users.create_index("region")
    await db.users.create_index("gender")
    await db.users.create_index("last_active")
    await db.users.create_index("created_at")
    await db.messages.create_index([("chat_id", 1), ("created_at", 1)])
    await db.saved.create_index([("owner_id", 1), ("target_id", 1)], unique=True)
    await db.profile_views.create_index([("viewer_id", 1), ("target_id", 1)], unique=True)
    await db.photo_unlocks.create_index([("requester_id", 1), ("target_id", 1)], unique=True)
    await db.payments.create_index("id", unique=True)
    await db.payments.create_index("user_id")
    await db.payments.create_index("status")
    await db.payments.create_index("created_at")
    await db.payments.create_index("purpose")
    await db.compat_unlocks.create_index([("user_id", 1), ("target_id", 1)], unique=True)
    await db.success_stories.create_index("created_at")
    # serve_file() (GET /api/files/{path}) queries by storage_path, not path -
    # the old index on "path" indexed a field no record actually has, so
    # every single photo/file request did a full collection scan. This hits
    # every photo render across the whole app (candidates grid, saved,
    # chat avatars, profile), so it compounds fast as the collection grows.
    await db.files.create_index("storage_path")
    await db.user_locations.create_index("user_id", unique=True)
    await db.withdrawals.create_index([("user_id", 1), ("created_at", -1)])
    await db.withdrawals.create_index("status")
    await db.family_requests.create_index([("from_user_id", 1), ("to_user_id", 1)])
    await db.family_requests.create_index([("to_user_id", 1), ("status", 1)])
    await db.concierge_orders.create_index([("user_id", 1), ("status", 1)])

    # PERF: Compound indexes for candidates query (scales to 100K+ users).
    # The candidates endpoint filters by: onboarded, gender, region, birth_date range.
    await db.users.create_index(
        [("onboarded", 1), ("gender", 1), ("region", 1), ("birth_date", 1)],
        name="ix_candidates_main"
    )
    # For sort by activity / new
    await db.users.create_index([("last_active", -1)], name="ix_last_active")
    # For boost float-to-top
    await db.users.create_index([("boost_until", -1)], name="ix_boost_until", sparse=True)
    # For verification & financial filters
    await db.users.create_index([("verified_selfie", 1)], name="ix_verified_selfie", sparse=True)
    await db.users.create_index([("verified_financial", 1)], name="ix_verified_financial", sparse=True)
    # Notifications: list by user_id newest first
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)], name="ix_notif_user_time")
    # Messages: chat reads pagination
    await db.messages.create_index([("from_user_id", 1), ("to_user_id", 1)], name="ix_msg_pair")
    # Referral lookup
    await db.users.create_index("referred_by", sparse=True, name="ix_referred_by")
    await db.users.create_index("referral_code", sparse=True, unique=False, name="ix_referral_code")
    # referral_id is the actual field looked up on every referral signup
    # (db.users.find_one({"referral_id": ref_code}) in auth_r.py, payments_r.py,
    # telegram_r.py) but had no index at all - every signup with a referral
    # code did a full collection scan of users.
    await db.users.create_index("referral_id", sparse=True, name="ix_referral_id")
    # Drop any existing index on referral_username_lower and recreate with sparse=True
    try:
        existing_indexes = await db.users.list_indexes().to_list(length=None)
        for idx in existing_indexes:
            if "referral_username_lower" in idx.get("key", {}):
                await db.users.drop_index(idx["name"])
                log.info(f"Dropped index {idx['name']} that references referral_username_lower")
    except Exception as e:
        log.warning(f"Warning while dropping referral username indexes: {e}")
    # Create sparse unique index - allows multiple null values
    try:
        await db.users.create_index(
            "referral_username_lower",
            unique=True,
            sparse=True,
            name="ix_referral_username"
        )
        log.info("Referral username index created successfully")
    except Exception as e:
        log.warning(f"Warning: Failed to create referral username index: {e}")
        log.warning("Server will continue without referral username index")
    await db.saved.create_index([("target_id", 1), ("at", -1)], name="ix_saved_target_at")
    await db.profile_views.create_index([("target_id", 1), ("at", -1)], name="ix_profile_views_target_at")
    await db.messages.create_index([("to_user_id", 1), ("created_at", -1)], name="ix_msg_to_user_time")
    await db.chat_unlocks.create_index([("user_id", 1), ("target_id", 1)], name="ix_chat_unlocks_user_target")
    # Verifications: looked up by id on every decide, by user_id for
    # /verification/mine, and by status+created_at for the admin queue -
    # none of these had an index, so every one of those was a full scan.
    await db.verifications.create_index("id", unique=True, name="ix_verif_id")
    await db.verifications.create_index([("user_id", 1), ("created_at", -1)], name="ix_verif_user_time")
    await db.verifications.create_index([("status", 1), ("created_at", -1)], name="ix_verif_status_time")
    # Gifts: leaderboard aggregates $match on created_at then $group by
    # from_user_id for period filters (day/week/month).
    await db.gifts.create_index([("created_at", -1)], name="ix_gifts_time")
    await db.gifts.create_index([("from_user_id", 1)], name="ix_gifts_from_user")
    # Gift shop inventory - "unused" list on every open, redeem does an
    # atomic (id, owner_id, status=unused) claim.
    await db.gift_inventory.create_index([("owner_id", 1), ("status", 1)], name="ix_gift_inv_owner_status")
    # Daily picks: unique per user per day. Without a unique index, two
    # concurrent /daily-picks requests on a cache-miss can both pass the
    # find_one-then-upsert race and insert two docs for the same day. A
    # unique-index create fails outright if any duplicate already exists in
    # the live collection - non-fatal here, same fallback pattern as the
    # referral_username_lower index below, so a pre-existing duplicate can
    # never take the whole app down at boot.
    try:
        await db.daily_picks.create_index([("user_id", 1), ("date", 1)], unique=True, name="ix_daily_picks_user_date")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique daily_picks index (likely pre-existing duplicates): {e}")
        await db.daily_picks.create_index([("user_id", 1), ("date", 1)], name="ix_daily_picks_user_date_nonunique")
    await db.reports.create_index([("status", 1), ("created_at", -1)], name="ix_reports_status_time")
    try:
        await db.pending_refs.create_index("telegram_id", unique=True, name="ix_pending_refs_tg")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique pending_refs index (likely pre-existing duplicates): {e}")
        await db.pending_refs.create_index("telegram_id", name="ix_pending_refs_tg_nonunique")
    # One view record per (announcement, viewer) - both to compute unique-
    # viewer counts cheaply and to make the mark-viewed upsert idempotent.
    try:
        await db.announcement_views.create_index(
            [("announcement_id", 1), ("user_id", 1)], unique=True, name="ix_anon_views_post_user"
        )
    except Exception as e:
        log.warning(f"Warning: Failed to create unique announcement_views index (likely pre-existing duplicates): {e}")
        await db.announcement_views.create_index(
            [("announcement_id", 1), ("user_id", 1)], name="ix_anon_views_post_user_nonunique"
        )
    # Blocks: _block_exists() runs on every message send + chat access check,
    # and candidates() fetches every block row for the current user on every
    # feed load - both were unindexed full collection scans on a collection
    # with no natural size cap.
    try:
        await db.blocks.create_index([("owner_id", 1), ("target_id", 1)], unique=True, name="ix_blocks_owner_target")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique blocks index (likely pre-existing duplicates): {e}")
        await db.blocks.create_index([("owner_id", 1), ("target_id", 1)], name="ix_blocks_owner_target_nonunique")
    await db.blocks.create_index("target_id", name="ix_blocks_target")
    # bot_starts: upserted by telegram_id on every single /start command.
    try:
        await db.bot_starts.create_index("telegram_id", unique=True, name="ix_bot_starts_tg")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique bot_starts index (likely pre-existing duplicates): {e}")
        await db.bot_starts.create_index("telegram_id", name="ix_bot_starts_tg_nonunique")
    # manual_topups: pending-count check on every P2P submission, admin queue
    # filtered by status, /stats pending count.
    await db.manual_topups.create_index([("user_id", 1), ("status", 1)], name="ix_manual_topups_user_status")
    await db.manual_topups.create_index([("status", 1), ("created_at", -1)], name="ix_manual_topups_status_time")
    # Telegram webhook update_id dedup - Telegram retries any update that
    # doesn't get a fast 2xx, so without this a retry (or a slow response)
    # reprocesses the same /start or callback_query and can double-send.
    try:
        await db.telegram_updates.create_index("update_id", unique=True, name="ix_tg_updates_id")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique telegram_updates index (likely pre-existing duplicates): {e}")
        await db.telegram_updates.create_index("update_id", name="ix_tg_updates_id_nonunique")
    # One row/day for the AI growth-insights trend comparison (lifecycle.py).
    try:
        await db.stats_snapshots.create_index("date", unique=True, name="ix_stats_snapshots_date")
    except Exception as e:
        log.warning(f"Warning: Failed to create unique stats_snapshots index (likely pre-existing duplicates): {e}")
        await db.stats_snapshots.create_index("date", name="ix_stats_snapshots_date_nonunique")

    # Initialize referral_id for existing users (first 8 chars of id) - only if needed
    sample_referral = await db.users.find_one({"referral_id": {"$exists": True}}, {"referral_id": 1})
    if not sample_referral:
        async for user in db.users.find({"referral_id": {"$exists": False}}, {"id": 1}):
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"referral_id": user["id"][:8]}}
            )

    # Seed admin
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not admin:
        await db.users.insert_one({
            "id": new_id(),
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_pw(ADMIN_PASSWORD),
            "name": "FIDEM Admin",
            "is_admin": True,
            "onboarded": True,
            "verified_identity": True,
            "verified_selfie": True,
            "verified_financial": True,
            "plan": "vip",
            "balance": 0,
            "gender": "male",
            "birth_date": "1990-01-01",
            "country": "Uzbekistan",
            "region": "Toshkent",
            "district": "Markaz",
            "marital_status": "single",
            "has_children": False,
            "children_count": 0,
            "height_cm": 175,
            "weight_kg": 70,
            "education": "Oliy",
            "profession": "Admin",
            "religion": "Islom",
            "looking_for": "—",
            "search_gender": "female",
            "search_age_min": 18,
            "search_age_max": 60,
            "search_region": "Toshkent",
            "language": "uz",
            "created_at": iso(now_utc()),
            "last_active": iso(now_utc()),
        })
        log.info(f"Seeded admin: {ADMIN_EMAIL}")

    # Demo profiles and fake success stories used to be seeded here. The app
    # runs on real users only now - nothing is auto-created; any leftover seed
    # profile is just tagged so it stays out of feeds and can be bulk-deleted
    # from the admin panel.
    await backfill_demo_flag()
    await privatize_existing_proofs()


async def privatize_existing_proofs() -> None:
    """Verification proofs and payment receipts used to be stored like profile
    photos (readable by any signed-in user). Mark every file that is referenced
    by one of them as private; new ones are uploaded private. Idempotent."""
    import re as _re

    paths = set()
    for coll in (db.verifications, db.manual_topups):
        async for doc in coll.find({"proof_url": {"$type": "string"}}, {"_id": 0, "proof_url": 1}):
            m = _re.search(r"/api/files/([^?\s]+)", doc.get("proof_url") or "")
            if m:
                paths.add(m.group(1))
    if paths:
        res = await db.files.update_many(
            {"storage_path": {"$in": list(paths)}, "is_public": {"$ne": False}},
            {"$set": {"is_public": False}},
        )
        if res.modified_count:
            log.info(f"Made {res.modified_count} existing proof/receipt files private")


async def backfill_demo_flag() -> None:
    """Demo users created before is_demo existed have no telegram_id and no
    email - the two account-creation paths (/auth/telegram, /auth/register)
    always set one or the other for a real signup, so any user missing BOTH
    (and not the admin account) can only be a seeded demo profile. Runs on
    every boot; a no-op once everything's already tagged."""
    res = await db.users.update_many(
        {
            "telegram_id": {"$in": [None, ""]},
            "email": {"$in": [None, ""]},
            "is_admin": {"$ne": True},
            "is_demo": {"$ne": True},
        },
        {"$set": {"is_demo": True}},
    )
    if res.modified_count:
        log.info(f"Backfilled is_demo on {res.modified_count} legacy seed users")


@app.on_event("shutdown")
async def shutdown() -> None:
    client.close()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,  # auth is Bearer-token only, no cookies used anywhere
    allow_origins=["*"],  # Allow all origins for development and production
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight for 10 minutes
)
