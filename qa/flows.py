import os
import httpx, json
B = "http://127.0.0.1:18100/api"
U = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")))
def H(k): return {"Authorization": f"Bearer {U[k]['token']}"}
adm = httpx.post(f"{B}/auth/login", json=dict(email="admin@fidem.uz", password="AdminQa#2026")).json()
HA = {"Authorization": f"Bearer {adm['token']}"}
ME = "qa@fidem.uz"; me = U[ME]["id"]
res = []
def chk(name, cond, detail=""):
    res.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(detail)[:200]) if (detail and not cond) else ""))
def req(m, p, k=ME, **kw):
    h = HA if k == "ADMIN" else H(k)
    return httpx.request(m, B + p, headers=h, timeout=30, **kw)

# ---- AUTH
r = httpx.post(f"{B}/auth/login", json=dict(email=ME, password="wrong")); chk("login wrong pw -> 401", r.status_code == 401, r.status_code)
r = httpx.post(f"{B}/auth/register", json=dict(email=ME, password="QaPass#2026")); chk("duplicate register -> 400", r.status_code == 400, r.status_code)
r = httpx.get(f"{B}/auth/me"); chk("me without token -> 401/403", r.status_code in (401, 403), r.status_code)
r = req("GET", "/auth/me"); j = r.json()
chk("me has no password_hash", "password_hash" not in j); chk("me plan free", j.get("plan") == "free", j.get("plan"))
# ---- CANDIDATES
r = req("GET", "/candidates"); c = r.json()
chk("candidates 200 & list", r.status_code == 200 and isinstance(c, list), r.status_code)
ids = [x["id"] for x in c]
chk("candidates exclude self", me not in ids)
chk("candidates only women (search_gender)", all(x.get("gender") == "female" for x in c), {x.get("gender") for x in c})
chk("candidates count == 7 women", len(c) == 7, len(c))
leak = [k for x in c for k in ("email", "password_hash", "phone", "contact_phone", "telegram_id", "ip_address") if k in x]
chk("candidates leak no private fields", not leak, set(leak))
chk("photos open by default in the feed", all(x.get("photo_url") for x in c), [bool(x.get("photo_url")) for x in c][:4])
r = req("GET", f"/candidates/{ids[0]}"); d = r.json()
leak = [k for k in ("email", "password_hash", "contact_phone", "contact_telegram", "contact_instagram", "telegram_id", "ip_address") if k in d]
chk("candidate detail leaks no private fields", not leak, leak)
# ---- SIGNUP RULES
r = httpx.post(f"{B}/auth/register", json=dict(email="minor@fidem.uz", password="QaPass#2026"))
if "token" not in r.json():  # re-run on the same DB: the account already exists
    r = httpx.post(f"{B}/auth/login", json=dict(email="minor@fidem.uz", password="QaPass#2026"))
tok = r.json()["token"]
r = httpx.post(f"{B}/profile/onboard", headers={"Authorization": f"Bearer {tok}"}, json=dict(gender="male", birth_date="2015-01-01", country="Uzbekistan", marital_status="single", has_children=False, search_gender="female", name="Bola", photo_url="http://127.0.0.1:18100/api/qa-photo/1.png", terms_accepted=True))
chk("minor cannot sign up (server-side)", r.status_code == 400 and "age_restricted" in r.text, (r.status_code, r.text[:80]))
r = httpx.get(f"{B}/payments/topup-config", headers=H(ME)); print("   topup-config:", r.json())
# ---- SAVED / MATCH
f0, f1, f2 = U["f0@fidem.uz"]["id"], U["f1@fidem.uz"]["id"], U["f2@fidem.uz"]["id"]
r = req("POST", "/saved", json={"user_id": f0}); chk("save f0 ok", r.status_code == 200, (r.status_code, r.text[:100]))
r = req("POST", "/saved", json={"user_id": f0}); chk("save twice idempotent (no 5xx)", r.status_code < 500, r.status_code)
r = req("GET", "/saved/mine"); chk("saved/mine contains f0", f0 in [x["id"] for x in r.json()])
r = req("POST", "/saved", json={"user_id": me}); chk("cannot save self", r.status_code >= 400, r.status_code)
# ---- CHAT PAYWALL
r = req("POST", "/messages/send", json={"to_user_id": f2, "text": "salom"}); chk("free user cold message -> 402", r.status_code == 402, (r.status_code, r.text[:80]))
a = req("GET", f"/chat/access/{f2}").json(); chk("access says locked + price", a.get("can_message") is False and a.get("price_uzs", 0) > 0, a)
r = req("POST", "/saved", k="f0@fidem.uz", json={"user_id": me}); 
chk("mutual save -> match chat open", req("GET", f"/chat/access/{f0}").json().get("can_message") is True)
r = req("POST", "/messages/send", json={"to_user_id": f0, "text": "Assalomu alaykum"}); chk("message to match ok", r.status_code == 200, (r.status_code, r.text[:100]))
r = req("POST", "/messages/send", json={"to_user_id": f0, "text": "yozing telegram @qatester yoki +998901234567"}); chk("free user sharing contact blocked", r.status_code == 403 and "contact_free_blocked" in r.text, (r.status_code, r.text[:100]))
r = req("POST", "/messages/send", k="f0@fidem.uz", json={"to_user_id": me, "text": "Va alaykum assalom"}); chk("reply from match ok", r.status_code == 200, r.status_code)
cid = "_".join(sorted([me, f0])); h = req("GET", f"/messages/{cid}").json()
chk("history has 2 msgs in order", len(h) == 2 and h[0]["text"] == "Assalomu alaykum", [x["text"] for x in h])
ch = req("GET", "/messages/chats").json(); chk("chats list shows f0 with last msg", any(x["other"]["id"] == f0 for x in ch), len(ch))
r = req("POST", "/messages/send", json={"to_user_id": me, "text": "x"}); chk("cannot message self", r.status_code == 400, r.status_code)
# ---- PAYMENT: plan purchase paths
t = req("GET", "/payments/topup-config").json(); print("   topup-config:", {k: v for k, v in t.items() if k != "card_number"})
r = req("POST", "/payments/create", json={"purpose": "premium", "amount": 79000, "months": 1})
print("   payments/create premium (no balance):", r.status_code, r.text[:200])
r = req("POST", "/payments/create", json={"purpose": "premium", "amount": 1, "months": 1}); chk("tampered amount rejected", r.status_code >= 400 or "amount" in r.text.lower(), (r.status_code, r.text[:120]))
# top up balance through admin then buy
r = req("PATCH", f"/admin/users/{me}", k="ADMIN", json={"add_balance": 200000}); chk("admin add balance", r.status_code == 200, (r.status_code, r.text[:100]))
bal = req("GET", "/auth/me").json().get("balance"); chk("balance 200000", bal == 200000, bal)
r = req("POST", "/payments/create", json={"purpose": "premium", "amount": 79000, "months": 1}); print("   buy premium w/ balance:", r.status_code, r.text[:160])
m = req("GET", "/auth/me").json(); chk("plan premium after balance purchase", m.get("plan") == "premium", (m.get("plan"), m.get("balance")))
r = req("POST", "/messages/send", json={"to_user_id": f2, "text": "salom, telegram @qatester"}); chk("premium user cold message + contact ok", r.status_code == 200, (r.status_code, r.text[:100]))
# ---- PRIVACY
r = req("POST", "/settings/privacy", json={"hidden_profile": True}); print("   privacy hidden:", r.status_code, r.text[:100])
c2 = req("GET", "/candidates", k="f3@fidem.uz").json(); chk("hidden user not in others' feed", me not in [x["id"] for x in c2] , len(c2))
req("POST", "/settings/privacy", json={"hidden_profile": False})
# ---- BLOCK / REPORT
r = req("POST", "/messages/block", json={"user_id": f1}); chk("block ok", r.status_code == 200, r.status_code)
chk("blocked not in feed", f1 not in [x["id"] for x in req("GET", "/candidates").json()])
r = req("POST", "/messages/report", json={"user_id": f1, "reason": "spam"}); print("   report:", r.status_code, r.text[:100])
# ---- misc
for p in ("/notifications", "/daily-picks", "/referral/mine", "/withdrawals/status", "/personality/questions", "/prompts/library", "/gifts/catalog", "/stories", "/saved/summary", "/verification/mine", "/boost/status", "/leaderboard", "/concierge/info"):
    r = req("GET", p); chk(f"GET {p} 200", r.status_code == 200, r.status_code)
print("\nSUMMARY:", sum(1 for x in res if x[1]), "pass,", sum(1 for x in res if not x[1]), "fail")
