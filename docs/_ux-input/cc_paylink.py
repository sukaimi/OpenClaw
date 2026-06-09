#!/usr/bin/env python3
"""cc-paylink <pages> [email] — create an EXACT Stripe payment link (pages x SGD10, fixed quantity).
Prints the URL. The quantity is fixed (not adjustable) so the amount is always correct."""
import os, sys, requests

API = "https://api.stripe.com/v1"
CACHE = "/root/.openclaw/phase2/stripe-price.txt"


def load_secret(name):
    for line in open("/root/.openclaw/secrets/cc-secrets.env"):
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return ""


KEY = load_secret("STRIPE_TEST_KEY")
H = {"Authorization": "Bearer " + KEY}


def price_id():
    if os.path.exists(CACHE):
        return open(CACHE).read().strip()
    prod = requests.post(API + "/products", headers=H,
                         data={"name": "Website / EDM page — Code&Craft",
                               "description": "SGD 10 per page."}).json()
    price = requests.post(API + "/prices", headers=H,
                          data={"unit_amount": 1000, "currency": "sgd", "product": prod["id"]}).json()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    open(CACHE, "w").write(price["id"])
    return price["id"]


def main():
    if len(sys.argv) < 2:
        print("usage: cc-paylink <pages> [email]"); sys.exit(1)
    pages = int(sys.argv[1])
    email = sys.argv[2] if len(sys.argv) > 2 else ""
    pl = requests.post(API + "/payment_links", headers=H,
                       data={"line_items[0][price]": price_id(),
                             "line_items[0][quantity]": pages}).json()
    url = pl.get("url")
    if not url:
        print("FAIL", str(pl)[:300]); sys.exit(1)
    if email:
        url = url + "?prefilled_email=" + email
    print("%s" % url)
    print("# pages=%d  total=SGD%d  (fixed quantity, exact)" % (pages, pages * 10), file=sys.stderr)


if __name__ == "__main__":
    main()
