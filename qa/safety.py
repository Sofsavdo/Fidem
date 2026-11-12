"""Safety rules against fake profiles and off-platform pulls (real API, QA DB).
Run after seed.py (f0..f4 selfie-verified, f5/f6 not)."""
import json, os
import httpx

B = "http://127.0.0.1:18100/api"
U = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")))
H = lambda who: {"Authorization": "Bearer " + U[who]["token"]}
ADM = {"Authorization": "Bearer " + httpx.post(f"{B}/auth/login", json=dict(email="admin@fidem.uz", password="AdminQa#2026")).json()["token"]}
fails = 0


def chk(name, ok, extra=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" | {extra}"))
    fails += 0 if ok else 1


def send(who, to, text):
    return httpx.post(f"{B}/messages/send", headers=H(who), json={"to_user_id": U[to]["id"], "text": text})


def me(who):
    return httpx.get(f"{B}/auth/me", headers=H(who)).json()


# --- women: free Premium only after selfie, and selfie to write
m5 = me("f5@fidem.uz")
chk("unverified woman: no free Premium yet", m5["plan"] == "free" and m5.get("women_promo") == "needs_selfie", m5.get("plan"))
r = send("f5@fidem.uz", "m0@fidem.uz", "Assalomu alaykum")
chk("unverified woman cannot write (selfie_required)", r.status_code == 403 and r.json().get("detail") == "selfie_required", r.text[:120])
m0 = me("f0@fidem.uz")
chk("verified woman gets Premium free", m0["plan"] == "premium" and m0.get("plan_source") == "women_free", m0.get("plan"))

# --- selfie with a random gesture
png = httpx.get(f"{B}/qa-photo/2.png").content
up = httpx.post(f"{B}/files/upload?purpose=private", headers=H("f5@fidem.uz"), files={"file": ("s.png", png, "image/png")}).json()["url"]
r = httpx.post(f"{B}/verification/request", headers=H("f5@fidem.uz"), json={"kind": "selfie", "proof_url": "http://127.0.0.1:18100" + up})
chk("selfie without a gesture challenge is refused", r.status_code == 400 and r.json().get("detail") == "challenge_required", r.text[:120])
ch = httpx.get(f"{B}/verification/selfie-challenge", headers=H("f5@fidem.uz")).json()
chk("challenge names a gesture", bool(ch.get("text_uz")) and bool(ch.get("code")), ch)
r = httpx.post(f"{B}/verification/request", headers=H("f5@fidem.uz"), json={"kind": "selfie", "proof_url": "http://127.0.0.1:18100" + up})
chk("selfie with the challenge is accepted for review", r.status_code == 200, r.text[:120])
v = httpx.get(f"{B}/admin/verifications?status=pending", headers=ADM).json()
rows = v.get("verifications", v if isinstance(v, list) else [])
chk("admin sees which gesture was asked", any(x.get("gesture_text") for x in rows), str(rows)[:200])

# --- off-platform: contacts in text blocked for everyone, money requests blocked + flagged
httpx.patch(f"{B}/admin/users/{U['m1@fidem.uz']['id']}", headers=ADM, json={"plan": "premium", "verified_selfie": True})
r = send("m1@fidem.uz", "f1@fidem.uz", "telegramda yozing @bobur_uz")
chk("contact in text blocked even for Premium", r.status_code == 403 and r.json().get("detail") == "contact_use_button", r.text[:120])
r = send("f1@fidem.uz", "m1@fidem.uz", "kartamga 50 ming tashlab bering 8600 1234 5678 9012")
chk("money request blocked", r.status_code == 422 and r.json().get("detail") == "money_request_blocked", r.text[:120])
reps = httpx.get(f"{B}/admin/reports", headers=ADM).json()
chk("money request flagged for the admin", any(x.get("reason") == "money_request" and x.get("target_id") == U["f1@fidem.uz"]["id"] for x in reps), str(reps)[:200])
for _ in range(2):
    send("f1@fidem.uz", "m1@fidem.uz", "pul o'tkazib bering iltimos")
f1 = httpx.get(f"{B}/admin/users/{U['f1@fidem.uz']['id']}/detail", headers=ADM).json()
f1u = f1.get("user", f1)
chk("3 money requests hide the profile for review", f1u.get("shadow_banned") is True, {k: f1u.get(k) for k in ("shadow_banned", "shadow_ban_reason", "money_request_flags")})

# --- contact exchange through consent
a, b = "m1@fidem.uz", "f2@fidem.uz"
httpx.patch(f"{B}/profile", headers=H(a), json={"contact_telegram": "bobur_test"})
httpx.patch(f"{B}/profile", headers=H(b), json={"contact_telegram": "nigora_test"})
r = httpx.post(f"{B}/chat/contact-exchange/{U[b]['id']}", headers=H(a))
chk("exchange needs a real conversation first", r.status_code == 400 and r.json().get("detail") == "need_more_messages", r.text[:120])
for i in range(10):
    send(a, b, f"savol {i}")
    send(b, a, f"javob {i}")
r = httpx.post(f"{B}/chat/contact-exchange/{U[b]['id']}", headers=H(a))
chk("exchange request after 10+10 messages", r.status_code == 200 and r.json().get("status") == "pending", r.text[:160])
st = httpx.get(f"{B}/chat/contact-exchange/{U[a]['id']}", headers=H(b)).json()
chk("receiver sees an incoming request", st.get("status") == "pending" and st.get("direction") == "incoming", st)
r = httpx.post(f"{B}/chat/contact-exchange/{U[a]['id']}/respond", headers=H(b), json={"accept": True})
chk("receiver accepts", r.status_code == 200 and r.json().get("status") == "accepted", r.text[:120])
st = httpx.get(f"{B}/chat/contact-exchange/{U[b]['id']}", headers=H(a)).json()
chk("both now see the other's Telegram", st.get("contacts", {}).get("telegram") == "nigora_test", st)
r = httpx.post(f"{B}/chat/contact-exchange/{U['f3@fidem.uz']['id']}", headers=H("m2@fidem.uz"))
chk("free / unverified man cannot request", r.status_code in (402, 403), r.text[:120])

# --- two different reporters hide a profile
target = U["m3@fidem.uz"]["id"]
for who in ("f3@fidem.uz", "f4@fidem.uz"):
    httpx.post(f"{B}/messages/report", headers=H(who), json={"user_id": target, "reason": "firibgar"})
d = httpx.get(f"{B}/admin/users/{target}/detail", headers=ADM).json()
du = d.get("user", d)
chk("2 reports hide the profile until the admin looks", du.get("shadow_banned") is True, {k: du.get(k) for k in ("shadow_banned", "shadow_ban_reason")})

# --- chat moderation: insults never reach the other person; 3 in a day = 24h mute
a, b = "f3@fidem.uz", "m0@fidem.uz"
r = send(a, b, "uyda yotibman, charchadim")
chk("ordinary text that the old list blocked now goes through", r.status_code == 200, r.text[:120])
r = send(a, b, "sen ahmoq ekansan")
chk("insult blocked with a warning", r.status_code == 422 and r.json().get("detail") == "message_blocked", r.text[:120])
msgs = httpx.get(f"{B}/messages/{'_'.join(sorted([U[a]['id'], U[b]['id']]))}", headers=H(b)).json()
chk("blocked text never reached the other person", not any("ahmoq" in (m.get("text") or "") for m in (msgs if isinstance(msgs, list) else msgs.get("messages", []))), str(msgs)[:200])
send(a, b, "fuck you")
r = send(a, b, "сука")
chk("third strike in 24h mutes for a day", r.status_code == 422 and r.json().get("detail") == "muted_temp", r.text[:120])
r = send(a, b, "kechirasiz")
chk("muted user can't write", r.status_code == 403 and r.json().get("detail") == "muted_temp", r.text[:120])
ev = httpx.get(f"{B}/admin/moderation/events", headers=ADM).json()
chk("admin sees the blocked messages", ev.get("total", 0) >= 3 and ev["items"][0].get("from_user", {}).get("name"), str(ev)[:200])
st = httpx.get(f"{B}/admin/moderation", headers=ADM).json()
chk("admin panel counts", st.get("blocked_24h", 0) >= 3 and st.get("muted_now", 0) >= 1 and st.get("ai_enabled") is True, st)
httpx.post(f"{B}/admin/users/{U[a]['id']}/unmute-temp", headers=ADM)
r = send(a, b, "kechirasiz, qo'pol gapirdim")
chk("admin can lift the mute", r.status_code == 200, r.text[:120])
r = httpx.post(f"{B}/admin/moderation", headers=ADM, json={"ai_enabled": False})
chk("admin can switch the AI off", r.status_code == 200 and httpx.get(f"{B}/admin/moderation", headers=ADM).json()["ai_enabled"] is False, r.text)
httpx.post(f"{B}/admin/moderation", headers=ADM, json={"ai_enabled": True})

print("ALL PASS" if not fails else f"{fails} FAILED")
