"""The web API the website calls."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shop import outbox, payments, store
from shop.auth import customer_from_cookie


class Handler(BaseHTTPRequestHandler):
    """Routes: POST /v1/orders, GET /v1/orders/<id>."""

    def send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/v1/orders":
            return self.send_json(404, {"error": {"code": "not_found", "message": "No such route"}})
        customer = customer_from_cookie(self.headers.get("Cookie", ""))
        if customer is None:
            return self.send_json(401, {"error": {"code": "unauthenticated", "message": "Log in first"}})
        order = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        total = sum(line["qty"] * line["price_cents"] for line in order["lines"])
        now = datetime.now(timezone.utc).isoformat()
        payment_ref = payments.charge(total, order["card_token"], order_ref=now)
        with store.connect() as conn:
            order_id = store.save_order(conn, customer, order["lines"], total, payment_ref, order["address"], now)
            outbox.enqueue(conn, "order_confirmation", {"order_id": order_id}, now)
        return self.send_json(201, {"id": order_id})

    def do_GET(self):
        customer = customer_from_cookie(self.headers.get("Cookie", ""))
        if customer is None:
            return self.send_json(401, {"error": {"code": "unauthenticated", "message": "Log in first"}})
        if not self.path.startswith("/v1/orders/"):
            return self.send_json(404, {"error": {"code": "not_found", "message": "No such route"}})
        with store.connect() as conn:
            order = store.get_order(conn, int(self.path.rsplit("/", 1)[1]))
        if order is None or order["customer_id"] != customer:
            return self.send_json(404, {"error": {"code": "not_found", "message": "No such order"}})
        return self.send_json(200, order)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
