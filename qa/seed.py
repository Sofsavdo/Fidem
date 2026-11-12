import os
import httpx, random, json, sys
B = "http://127.0.0.1:18100/api"
random.seed(7)
regions = ["Toshkent", "Samarqand", "Farg'ona", "Andijon", "Buxoro", "Namangan"]
f_names = ["Madina", "Zilola", "Nigora", "Dilnoza", "Sevara", "Malika", "Shahnoza"]
m_names = ["Aziz", "Bobur", "Jasur", "Sardor", "Timur", "Otabek", "Rustam"]
def onboard_payload(name, gender, i):
    return dict(
        gender=gender, birth_date=f"{1990 + (i % 9)}-0{1 + i % 9}-1{i % 9}", country="Uzbekistan",
        region=regions[i % len(regions)], district="Chilonzor", marital_status=["single", "divorced"][i % 2],
        has_children=bool(i % 3 == 0), children_count=1 if i % 3 == 0 else 0, height_cm=160 + i * 2, weight_kg=55 + i * 2,
        education="Oliy", profession="Muhandis", religion="Islom", looking_for="Jiddiy munosabat, oila qurish",
        search_gender="male" if gender == "female" else "female", search_age_min=20, search_age_max=45,
        search_country="Uzbekistan", search_region="", bio="Men haqimda qisqacha. Oilaga e'tiborliman.",
        name=name, photo_url=f"http://127.0.0.1:18100/api/qa-photo/{i}.png", smoking="no", alcohol="no", relocation=False, terms_accepted=True,
    )
out = {}
def mk(email, name, gender, i, pw="QaPass#2026"):
    r = httpx.post(f"{B}/auth/register", json=dict(email=email, password=pw, name=name), timeout=30)
    r.raise_for_status(); d = r.json()
    h = {"Authorization": f"Bearer {d['token']}"}
    png = httpx.get(f"http://127.0.0.1:18100/api/qa-photo/{i}.png").content
    up = httpx.post(f"{B}/files/upload", files={"file": (f"p{i}.png", png, "image/png")}, headers=h, timeout=30); up.raise_for_status()
    payload = onboard_payload(name, gender, i); payload["photo_url"] = "http://127.0.0.1:18100" + up.json()["url"]
    o = httpx.post(f"{B}/profile/onboard", json=payload, headers=h, timeout=30)
    if o.status_code != 200:
        print("ONBOARD FAIL", email, o.status_code, o.text[:300]); return None
    out[email] = dict(id=d["user_id"], token=d["token"])
    return d["user_id"]
# main QA user: male looking for women
mk("qa@fidem.uz", "QA Tester", "male", 3)
for i, n in enumerate(f_names): mk(f"f{i}@fidem.uz", n, "female", i + 1)
for i, n in enumerate(m_names): mk(f"m{i}@fidem.uz", n, "male", i + 2)
# Women write only after the live selfie check: verify f0..f4 the way the
# admin would; f5/f6 stay unverified for the safety tests (qa/safety.py).
_adm = httpx.post(f"{B}/auth/login", json=dict(email="admin@fidem.uz", password="AdminQa#2026"), timeout=30).json()["token"]
for i in range(5):
    uid = out.get(f"f{i}@fidem.uz", {}).get("id")
    if uid:
        httpx.patch(f"{B}/admin/users/{uid}", json={"verified_selfie": True}, headers={"Authorization": f"Bearer {_adm}"}, timeout=30).raise_for_status()
# a brand new user who has NOT onboarded (for the onboarding flow)
r = httpx.post(f"{B}/auth/register", json=dict(email="new@fidem.uz", password="QaPass#2026", name="Yangi"), timeout=30); r.raise_for_status()
# a guest: signed in, picked who they look for, profile not finished
g = httpx.post(f"{B}/auth/register", json=dict(email="guest@fidem.uz", password="QaPass#2026", name="Mehmon"), timeout=30).json()
httpx.post(f"{B}/profile/guest", json={"search_gender": "female"}, headers={"Authorization": f"Bearer {g['token']}"}, timeout=30).raise_for_status()
out["guest@fidem.uz"] = dict(id=g["user_id"], token=g["token"])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json"), "w"), indent=1)
print("seeded", len(out), "users")
