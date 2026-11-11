import os
import httpx, json, re, sys
B = "http://127.0.0.1:18100"
users = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")))
me = users["qa@fidem.uz"]; other = users["f0@fidem.uz"]
adm = httpx.post(f"{B}/api/auth/login", json=dict(email="admin@fidem.uz", password="AdminQa#2026")).json()
H_ME = {"Authorization": f"Bearer {me['token']}"}; H_ADM = {"Authorization": f"Bearer {adm['token']}"}
spec = httpx.get(f"{B}/openapi.json").json()
ids = {"target_id": other["id"], "user_id": other["id"], "chat_id": "_".join(sorted([me["id"], other["id"]])),
       "other_id": other["id"], "app_id": "x", "id": "x", "uid": other["id"]}
rows = []
for path, ops in sorted(spec["paths"].items()):
    for method, op in ops.items():
        if method.upper() != "GET": continue
        url = path
        for p in re.findall(r"\{(\w+)\}", path):
            url = url.replace("{%s}" % p, ids.get(p, "x"))
        admin = "/admin" in path
        try:
            r = httpx.get(B + url, headers=H_ADM if admin else H_ME, timeout=30)
            code = r.status_code; body = r.text[:140].replace("\n", " ")
        except Exception as e:
            code = "EXC"; body = str(e)[:140]
        rows.append((code, method.upper(), url, body))
bad = [r for r in rows if r[0] == "EXC" or (isinstance(r[0], int) and r[0] >= 500)]
print(f"GET endpoints: {len(rows)}; 5xx/exceptions: {len(bad)}")
for r in bad: print("  5xx", r)
from collections import Counter
print(Counter(str(r[0]) for r in rows))
print("-- 4xx (review) --")
for r in rows:
    if isinstance(r[0], int) and 400 <= r[0] < 500: print(" ", r[0], r[2], r[3][:90])
