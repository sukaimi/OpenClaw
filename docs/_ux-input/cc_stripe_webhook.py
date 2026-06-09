#!/usr/bin/env python3
"""cc-stripe-webhook — receives Stripe webhooks, verifies signature, pings the operator on payment.
Listens on 127.0.0.1:9000 (nginx proxies https://teams.codeandcraft.ai/cc/{stripe-webhook,pay} -> here).
On checkout.session.completed -> records the request + runs cc-notify-operator (Telegram+Teams).
GET /cc/pay?type=T&pages=N&email=X -> 302 to the matching fixed-price Stripe link (pay-on-submit from
Tally). Single-page & EDM are forced to 1 page regardless of `pages`; the page count is parsed as the
first integer in `pages` (so price-anchored labels like "3 pages — SGD 30" work)."""
import os, re, json, hmac, hashlib, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, quote

PENDING = "/root/.openclaw/phase2/pending-requests.jsonl"
PAYLINKS = "/root/.openclaw/phase2/paylinks.txt"


def load_paylinks():
    m = {}
    try:
        for line in open(PAYLINKS):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                m[k.strip()] = v.strip()
    except Exception:
        pass
    return m


def load_secret(name):
    try:
        for line in open("/root/.openclaw/secrets/cc-secrets.env"):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get(name, "")


SECRET = load_secret("STRIPE_WEBHOOK_SECRET")


def verify(payload, sig_header):
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(","))
        signed = ("%s.%s" % (parts["t"], payload.decode())).encode()
        expected = hmac.new(SECRET.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, parts["v1"])
    except Exception:
        return False


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(n)
        if SECRET and not verify(payload, self.headers.get("Stripe-Signature", "")):
            self.send_response(400); self.end_headers(); self.wfile.write(b"bad sig"); return
        try:
            event = json.loads(payload)
        except Exception:
            self.send_response(400); self.end_headers(); return
        if event.get("type") == "checkout.session.completed":
            s = event.get("data", {}).get("object", {})
            email = (s.get("customer_details") or {}).get("email") or s.get("customer_email") or "?"
            amount = (s.get("amount_total") or 0) / 100.0
            try:
                os.makedirs(os.path.dirname(PENDING), exist_ok=True)
                with open(PENDING, "a") as f:
                    f.write(json.dumps({"ts": time.time(), "email": email, "amount": amount,
                                        "session": s.get("id"), "status": "paid"}) + "\n")
            except Exception:
                pass
            # Fulfil asynchronously: match the approved brief -> create job -> build -> deploy -> deliver.
            try:
                subprocess.Popen(["cc-fulfil", email])
            except Exception:
                pass
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/cc/pay":
            q = parse_qs(p.query)
            typ = (q.get("type") or [""])[0].strip().lower()
            email = (q.get("email") or [""])[0].strip()
            m = re.search(r"\d+", (q.get("pages") or [""])[0])   # parse count from "3 pages — SGD 30" etc.
            pages = m.group() if m else ""
            if typ and "multi" not in typ:                       # single page / EDM = always 1 page
                pages = "1"
            url = load_paylinks().get(pages)
            if not url:
                self.send_response(400); self.end_headers(); self.wfile.write(b"invalid pages"); return
            if email:
                url += ("&" if "?" in url else "?") + "prefilled_email=" + quote(email)
            self.send_response(302); self.send_header("Location", url); self.end_headers(); return
        self.send_response(200); self.end_headers(); self.wfile.write(b"cc-stripe-webhook up")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 9000), H).serve_forever()
