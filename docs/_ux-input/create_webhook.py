#!/usr/bin/env python3
import os, requests
KEY = os.environ["STRIPE_TEST_KEY"]
r = requests.post("https://api.stripe.com/v1/webhook_endpoints",
                  headers={"Authorization": "Bearer " + KEY},
                  data={"url": "https://teams.codeandcraft.ai/cc/stripe-webhook",
                        "enabled_events[]": "checkout.session.completed"})
d = r.json()
sec = d.get("secret")
if not sec:
    print("FAIL", r.status_code, str(d)[:300]); raise SystemExit(1)
p = "/root/.openclaw/secrets/cc-secrets.env"
lines = [l for l in open(p) if "STRIPE_WEBHOOK_SECRET" not in l]
open(p, "w").writelines(lines)
open(p, "a").write("export STRIPE_WEBHOOK_SECRET=%s\n" % sec)
print("endpoint created:", d.get("id"), "| secret stored (whsec_***masked***)")
