import os
import httpx, json
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flows.py")).read().split("# ---- AUTH")[0])   # reuse helpers/tokens
f3, f4, m0 = U["f3@fidem.uz"]["id"], U["f4@fidem.uz"]["id"], U["m0@fidem.uz"]["id"]
# ---- ACCESS CONTROL / IDOR
r = req("GET", "/admin/users"); chk("normal user cannot hit /admin/users", r.status_code in (401, 403), r.status_code)
r = req("GET", "/admin/manual-topups"); chk("normal user cannot hit admin topups", r.status_code in (401, 403), r.status_code)
cid_other = "_".join(sorted([f3, f4]))
r = req("GET", f"/messages/{cid_other}"); chk("cannot read others' chat", r.status_code == 403, r.status_code)
r = req("PATCH", f"/admin/users/{me}", json={"plan": "vip"}); chk("normal user cannot self-grant VIP via admin route", r.status_code in (401, 403), r.status_code)
r = req("PATCH", "/profile", json={"plan": "vip", "balance": 999999, "is_admin": True}); 
m = req("GET", "/auth/me").json(); chk("PATCH /profile cannot set plan/balance/is_admin (mass assignment)", m.get("plan") != "vip" and m.get("balance", 0) < 900000 and not m.get("is_admin"), {k: m.get(k) for k in ("plan", "balance", "is_admin")})
r = req("POST", "/admin/manual-topups/x/decide", json={"approve": True}); chk("normal user cannot approve topups", r.status_code in (401, 403, 404), r.status_code)
# ---- FILE ACCESS (private proofs, closed photos)
_B = "http://127.0.0.1:18100/api"
_hq = {"Authorization": "Bearer " + U["qa@fidem.uz"]["token"]}
_hf = {"Authorization": "Bearer " + U["f0@fidem.uz"]["token"]}
_png = httpx.get(f"{_B}/qa-photo/3.png").content
_priv = httpx.post(f"{_B}/files/upload?purpose=private", headers=_hq, files={"file": ("proof.png", _png, "image/png")}).json()["url"]
chk("owner can read their private upload", httpx.get(_B.replace("/api", "") + _priv, headers=_hq).status_code == 200)
chk("another user cannot read a private proof", httpx.get(_B.replace("/api", "") + _priv, headers=_hf).status_code == 403)
_me = httpx.get(f"{_B}/auth/me", headers=_hq).json()
_main = _me["photo_url"]
chk("open profile photo is readable by others", httpx.get(_B.replace("/api", "") + _main, headers=_hf).status_code == 200)
httpx.post(f"{_B}/settings/privacy", headers=_hq, json={"photo_public": False})
import time as _t; _t.sleep(21)   # the server caches the owner's privacy flag for 20 s
chk("closed profile photo is blocked for others at file level", httpx.get(_B.replace("/api", "") + _main, headers=_hf).status_code == 403)
chk("...but still readable by the owner", httpx.get(_B.replace("/api", "") + _main, headers=_hq).status_code == 200)
httpx.post(f"{_B}/settings/privacy", headers=_hq, json={"photo_public": True})
# ---- P2P topup flow (admin approves -> balance)
req("POST", "/admin/topup-config", k="ADMIN", json={"p2p_enabled": True, "card_number": "8600 1234 5678 9012", "card_holder": "Test"}) 
r = req("GET", "/admin/topup-config", k="ADMIN"); print("   admin topup-config GET:", r.status_code, r.text[:120])
# ---- GIFTS
cat = req("GET", "/gifts/catalog").json(); print("   gift catalog:", type(cat).__name__, (len(cat) if hasattr(cat, '__len__') else ''), (cat[0] if isinstance(cat, list) and cat else str(cat)[:150]))
r = req("GET", "/gifts/recipients"); print("   gifts/recipients:", r.status_code)
# ---- WITHDRAWALS / REFERRAL
ws = req("GET", "/withdrawals/status").json(); print("   withdrawals/status:", ws)
r = req("POST", "/withdrawals/request", json={"amount": 1000, "card_number": "8600123456789012", "card_holder": "T"}); print("   withdraw 1000 w/o earnings:", r.status_code, r.text[:140])
rf = req("GET", "/referral/mine").json(); print("   referral/mine keys:", sorted(rf.keys())[:14])
# ---- PERSONALITY
q = req("GET", "/personality/questions").json(); print("   personality questions:", len(q.get("questions", q)) if isinstance(q, dict) else len(q))
# ---- FAMILY / CONCIERGE
r = req("POST", "/family/request", json={"to_user_id": f3}); print("   family request (free):", r.status_code, r.text[:120])
r = req("POST", "/concierge/order", json={"preferences": "test"}); print("   concierge order:", r.status_code, r.text[:140])
# ---- NOTIFICATIONS / ANNOUNCEMENTS / PROMPTS
n = req("GET", "/notifications").json(); print("   notifications:", type(n).__name__, len(n) if hasattr(n, '__len__') else '')
r = req("POST", "/notifications/read-all"); chk("notifications read-all", r.status_code == 200, r.status_code)
# ---- XSS / input sanitation
r = req("POST", "/messages/send", json={"to_user_id": f0 if (f0:=U['f0@fidem.uz']['id']) else f0, "text": "<script>alert(1)</script> salom"})
h = req("GET", "/messages/" + "_".join(sorted([me, f0]))).json(); chk("script tags stripped from message", all("<script" not in x["text"].lower() for x in h), [x["text"] for x in h][-1])
r = req("POST", "/messages/send", json={"to_user_id": f0, "text": "x" * 6000}); print("   6000-char message:", r.status_code, r.text[:100])
r = req("POST", "/messages/send", json={"to_user_id": f0, "text": "   "}); print("   blank message:", r.status_code, r.text[:100])
# ---- Profile edits
r = req("PATCH", "/profile", json={"bio": "Yangi bio <b>x</b>", "name": "Hacker"}); print("   PATCH profile:", r.status_code, r.text[:140])
r = req("PATCH", "/profile/language", json={"language": "ru"}); chk("language switch", r.status_code == 200, r.text[:100])
r = req("PATCH", "/profile/filters", json={"age_min": 25, "age_max": 35}); print("   filters:", r.status_code, r.text[:140])
r = req("PATCH", "/profile", json={"birth_date": "2015-01-01"}); print("   minor birth_date accepted?:", r.status_code, r.text[:140])
print("\nSUMMARY:", sum(1 for x in res if x[1]), "pass,", sum(1 for x in res if not x[1]), "fail")
