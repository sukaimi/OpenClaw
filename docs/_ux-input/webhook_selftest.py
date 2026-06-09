#!/usr/bin/env python3
import json, hmac, hashlib, time, requests


def load_secret(name):
    for line in open("/root/.openclaw/secrets/cc-secrets.env"):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return ""


SEC = load_secret("STRIPE_WEBHOOK_SECRET")
if not SEC:
    print("no STRIPE_WEBHOOK_SECRET"); raise SystemExit(1)
event = {"type": "checkout.session.completed",
         "data": {"object": {"id": "cs_test_selftest", "amount_total": 3000, "currency": "sgd",
                             "customer_details": {"email": "selftest@example.com"}}}}
payload = json.dumps(event)
t = str(int(time.time()))
sig = hmac.new(SEC.encode(), ("%s.%s" % (t, payload)).encode(), hashlib.sha256).hexdigest()
r = requests.post("http://127.0.0.1:9000", data=payload,
                  headers={"Stripe-Signature": "t=%s,v1=%s" % (t, sig), "Content-Type": "application/json"})
print("signed self-test POST ->", r.status_code, r.text[:40])
# also test a BAD signature is rejected
rb = requests.post("http://127.0.0.1:9000", data=payload,
                   headers={"Stripe-Signature": "t=%s,v1=deadbeef" % t, "Content-Type": "application/json"})
print("bad-signature POST ->", rb.status_code, "(should be 400)")
