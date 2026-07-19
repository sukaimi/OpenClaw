#!/usr/bin/env python3
"""Validate the Stripe test key + create the Code&Craft per-page Payment Link.
Reads STRIPE_TEST_KEY from env. Idempotent-ish: creates product/price/link each run (test mode)."""
import os, sys, requests

KEY = os.environ.get("STRIPE_TEST_KEY", "")
if not KEY:
    print("STRIPE_TEST_KEY not set"); sys.exit(1)
H = {"Authorization": "Bearer " + KEY}
API = "https://api.stripe.com/v1"


def post(path, data):
    r = requests.post(API + path, headers=H, data=data)
    if r.status_code >= 300:
        print("FAIL", path, r.status_code, r.text[:300]); sys.exit(1)
    return r.json()


# 1) validate
acct = requests.get(API + "/account", headers=H)
if acct.status_code >= 300:
    print("KEY INVALID:", acct.status_code, acct.text[:200]); sys.exit(1)
a = acct.json()
name = (a.get("settings", {}).get("dashboard", {}).get("display_name")
        or a.get("business_profile", {}).get("name") or a.get("email") or "?")
print("VALID test key | account:", a.get("id"), "| name:", name, "| country:", a.get("country"))

# 2) product + SGD10 price
prod = post("/products", {"name": "Website / EDM page — Code&Craft",
                          "description": "One page of a website or email design. SGD 10 per page."})
price = post("/prices", {"unit_amount": 1000, "currency": "sgd", "product": prod["id"]})
print("product:", prod["id"], "| price:", price["id"], "| SGD 10.00")

# 3) payment link, adjustable quantity (pages)
pl = post("/payment_links", {
    "line_items[0][price]": price["id"],
    "line_items[0][quantity]": 1,
    "line_items[0][adjustable_quantity][enabled]": "true",
    "line_items[0][adjustable_quantity][minimum]": 1,
    "line_items[0][adjustable_quantity][maximum]": 20,
})
print("PAYMENT LINK:", pl.get("url"))
print("link id:", pl.get("id"))
