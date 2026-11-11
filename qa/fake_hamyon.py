"""Stand-in for hamyon-api.uz in local QA (port 18102). Payments stay pending
until a test marks them paid via POST /qa/pay {payment_id}."""
import json, time, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PAYMENTS = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        return {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}

    def do_POST(self):
        path = urlparse(self.path).path
        f = self._form()
        if path == "/payment/create":
            amount = int(f["amount"])
            if any(p["amount"] == amount and p["status"] == "pending" for p in PAYMENTS.values()):
                return self._json(400, {"error": "Bu summada ochiq to'lov mavjud, summani o'zgartiring"})
            pid = uuid.uuid4().hex[:12]
            PAYMENTS[pid] = {"payment_id": pid, "order_id": f.get("order_id"), "shop_id": int(f["shop_id"]),
                             "amount": amount, "status": "pending", "expire_at": int(time.time()) + 300}
            return self._json(200, {"payment_id": pid, "order_id": f.get("order_id"), "amount": amount,
                                    "card": "8600 0000 0000 0001", "expires_in": 300,
                                    "expire_at": PAYMENTS[pid]["expire_at"], "message": "ok"})
        if path == "/payment/cancel":
            p = PAYMENTS.get(f.get("payment_id"))
            if p:
                p["status"] = "cancel"
            return self._json(200, {"result": "ok"})
        if path == "/qa/pay":
            p = PAYMENTS.get(f.get("payment_id")) or next((x for x in PAYMENTS.values() if x["order_id"] == f.get("order_id")), None)
            if p:
                p["status"] = "paid"
            return self._json(200, {"ok": bool(p)})
        return self._json(404, {"error": "not found"})

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/qa/find":
            oid = parse_qs(u.query).get("order_id", [""])[0]
            p = next((x for x in PAYMENTS.values() if x["order_id"] == oid), None)
            return self._json(200, p or {})
        if u.path == "/payment/status":
            p = PAYMENTS.get(parse_qs(u.query).get("payment_id", [""])[0])
            return self._json(200, p) if p else self._json(400, {"error": "topilmadi"})
        return self._json(404, {"error": "not found"})


HTTPServer(("127.0.0.1", 18102), H).serve_forever()
