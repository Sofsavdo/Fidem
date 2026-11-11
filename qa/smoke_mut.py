import os
import httpx, json, re
B = "http://127.0.0.1:18100"
users = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")))
me = users["qa@fidem.uz"]; other = users["f1@fidem.uz"]
adm = httpx.post(f"{B}/api/auth/login", json=dict(email="admin@fidem.uz", password="AdminQa#2026")).json()
H_ME = {"Authorization": f"Bearer {me['token']}"}; H_ADM = {"Authorization": f"Bearer {adm['token']}"}
spec = httpx.get(f"{B}/openapi.json").json()
comps = spec.get("components", {}).get("schemas", {})
def ref(s):
    return comps[s["$ref"].split("/")[-1]]
def gen(s, depth=0):
    if "$ref" in s: s = ref(s)
    if "anyOf" in s:
        for x in s["anyOf"]:
            if x.get("type") != "null": return gen(x, depth)
        return None
    if "enum" in s: return s["enum"][0]
    if "const" in s: return s["const"]
    t = s.get("type")
    if t == "string":
        f = s.get("format")
        return {"email": "qa@fidem.uz", "date-time": "2026-11-11T12:00:00Z", "date": "1995-01-01"}.get(f, "test")
    if t == "integer": return max(1, s.get("minimum", 1))
    if t == "number": return 1.0
    if t == "boolean": return False
    if t == "array": return [] if depth > 1 else [gen(s.get("items", {}), depth + 1)]
    if t == "object" or "properties" in s:
        out = {}
        for k, v in s.get("properties", {}).items():
            if k in s.get("required", []) or depth == 0:
                out[k] = gen(v, depth + 1)
        return out
    return None
ids = {"target_id": other["id"], "user_id": other["id"], "chat_id": "_".join(sorted([me["id"], other["id"]])), "id": "x"}
SKIP = ("/auth/register", "/profile/onboard")
rows = []
for path, ops in sorted(spec["paths"].items()):
    for method, op in ops.items():
        m = method.upper()
        if m == "GET" or any(path.endswith(x) for x in SKIP): continue
        url = path
        for p in re.findall(r"\{(\w+)\}", path): url = url.replace("{%s}" % p, ids.get(p, "x"))
        kw = {}
        rb = op.get("requestBody", {}).get("content", {})
        if "application/json" in rb: kw["json"] = gen(rb["application/json"]["schema"])
        elif "multipart/form-data" in rb: kw["files"] = {"file": ("a.png", b"\x89PNG\r\n", "image/png")}
        try:
            r = httpx.request(m, B + url, headers=H_ADM if "/admin" in path else H_ME, timeout=30, **kw)
            code, body = r.status_code, r.text[:160].replace("\n", " ")
        except Exception as e:
            code, body = "EXC", str(e)[:160]
        rows.append((code, m, url, body, kw.get("json")))
bad = [r for r in rows if r[0] == "EXC" or (isinstance(r[0], int) and r[0] >= 500)]
print(f"mutating endpoints: {len(rows)}; 5xx/exc: {len(bad)}")
for r in bad: print("  5xx:", r[0], r[1], r[2], "|", r[3][:120], "| body:", json.dumps(r[4])[:100])
from collections import Counter; print(Counter(str(r[0]) for r in rows))
