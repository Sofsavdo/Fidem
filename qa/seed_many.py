"""Adds N more women so the Nomzodlar feed has more than one page (default 55:
7 seeded + 55 = 62 -> pages of 30, 30, 2). Run after seed.py."""
import sys
import httpx
B = "http://127.0.0.1:18100/api"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 55
regions = ["Toshkent", "Samarqand", "Farg'ona", "Andijon", "Buxoro", "Namangan"]
ok = 0
for i in range(N):
    r = httpx.post(f"{B}/auth/register", json=dict(email=f"w{i}@fidem.uz", password="QaPass#2026", name=f"Gul{i}"), timeout=30)
    r.raise_for_status(); d = r.json()
    h = {"Authorization": f"Bearer {d['token']}"}
    png = httpx.get(f"http://127.0.0.1:18100/api/qa-photo/{i % 10}.png").content
    up = httpx.post(f"{B}/files/upload", files={"file": (f"p{i}.png", png, "image/png")}, headers=h, timeout=30); up.raise_for_status()
    payload = dict(
        gender="female", birth_date=f"{1992 + (i % 8)}-0{1 + i % 9}-1{i % 9}", country="Uzbekistan", region=regions[i % 6],
        district="Chilonzor", marital_status="single", has_children=False, children_count=0, height_cm=160 + i % 20,
        weight_kg=55, education="Oliy", profession="O'qituvchi", religion="Islom", looking_for="Oila qurish",
        search_gender="male", search_age_min=20, search_age_max=45, search_country="Uzbekistan", search_region="",
        bio="Qisqacha.", name=f"Gul{i}", photo_url="http://127.0.0.1:18100" + up.json()["url"], smoking="no",
        alcohol="no", relocation=False, terms_accepted=True,
    )
    o = httpx.post(f"{B}/profile/onboard", json=payload, headers=h, timeout=30)
    ok += o.status_code == 200
    if o.status_code != 200:
        print("FAIL", i, o.status_code, o.text[:120])
print("added", ok, "women")
