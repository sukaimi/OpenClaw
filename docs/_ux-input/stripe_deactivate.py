#!/usr/bin/env python3
"""Deactivate the old adjustable-quantity payment link + list remaining active links."""
import requests

API = "https://api.stripe.com/v1"
OLD = "plink_1TfFBZDh6DRSIZD3oirIviQO"  # the SGD10/page adjustable link (Tally redirect)


def load_secret(name):
    for line in open("/root/.openclaw/secrets/cc-secrets.env"):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return ""


H = {"Authorization": "Bearer " + load_secret("STRIPE_TEST_KEY")}

r = requests.post(API + "/payment_links/" + OLD, headers=H, data={"active": "false"})
print("deactivate old adjustable link:", r.status_code, "-> active:", r.json().get("active"))

ls = requests.get(API + "/payment_links?limit=30", headers=H).json().get("data", [])
act = [p for p in ls if p.get("active")]
print("active payment links remaining:", len(act))
for p in act:
    print("  -", p["id"], "|", p["url"][:48])
