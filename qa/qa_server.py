"""QA harness: the REAL FastAPI app on an in-memory mongomock DB (no network)."""
import os, sys
os.environ.update(
    MONGO_URL="mongodb://localhost:27017", DB_NAME="qa", JWT_SECRET="qa-secret-qa-secret-qa-secret-qa-1",
    ENVIRONMENT="development", ADMIN_PASSWORD="AdminQa#2026", CORS_ORIGINS="*",
    FREE_WEEKLY_INITIATIONS="0", DAILY_STREAK_ENABLED="0",
)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
import mongomock_motor
import core
orig = core.db
mock = mongomock_motor.AsyncMongoMockClient()["qa"]
import server  # noqa
for name, mod in list(sys.modules.items()):
    if mod is not None and getattr(mod, "db", None) is orig:
        mod.db = mock
core.db = mock
# no network side-effects / background loops
server.app.router.on_startup.clear()
server.app.router.on_shutdown.clear()
# permissive limiters for exploratory QA (limits are unit-tested separately)
for lim in ("auth_limiter", "payment_limiter", "verification_limiter"):
    getattr(core, lim).check = lambda *a, **k: None
for name, mod in list(sys.modules.items()):
    for lim in ("auth_limiter", "payment_limiter", "verification_limiter"):
        if mod is not None and hasattr(mod, lim):
            getattr(mod, lim).check = lambda *a, **k: None
import zlib, struct
from fastapi import Response
def _png(r, g, b, w=240, h=320):
    raw = b"".join(b"\x00" + bytes([r, g, b]) * w for _ in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
@server.app.get("/api/qa-photo/{n}.png")
async def qa_photo(n: int):
    pal = [(233, 150, 180), (140, 170, 230), (150, 210, 170), (240, 200, 120), (190, 160, 220), (120, 200, 210)]
    return Response(_png(*pal[n % len(pal)]), media_type="image/png")
import ai_service
async def _ok(image_url="", image_base64=""): return {"valid": True, "code": "ok"}
ai_service.verify_face_photo = _ok
import routers.auth_r as _ar
async def _own(uid, url): return None
# (ownership check is now REAL: uploads go through /files/upload into in-memory storage)
import storage, uuid
_MEM = {}
async def _put(path, data, content_type):
    fid = uuid.uuid4().hex[:24]; _MEM[fid] = (data, content_type)
    return {"path": fid, "filename": path, "content_type": content_type, "size": len(data), "provider": "mem"}
async def _get(path):
    d, ct = _MEM[path]; return d, ct
storage.put_object = _put; storage.get_object = _get
import routers.auth_r as _ar2
_ar2.put_object = _put
if hasattr(_ar2, "get_object"): _ar2.get_object = _get
import asyncio
async def seed_admin():
    await mock.users.insert_one({
        "id": "admin-1", "email": "admin@fidem.uz", "password_hash": core.hash_pw(os.environ["ADMIN_PASSWORD"]),
        "name": "Admin", "is_admin": True, "onboarded": True, "plan": "vip", "balance": 0,
        "created_at": core.iso(core.now_utc()), "last_active": core.iso(core.now_utc()),
        "gender": "male", "birth_date": "1990-01-01", "country": "Uzbekistan", "region": "Toshkent",
        "marital_status": "single", "has_children": False, "children_count": 0, "height_cm": 180, "weight_kg": 80,
    })
asyncio.get_event_loop().run_until_complete(seed_admin())
import uvicorn
uvicorn.run(server.app, host="127.0.0.1", port=18100, log_level="warning")
