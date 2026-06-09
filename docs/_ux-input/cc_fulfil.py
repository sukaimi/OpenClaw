#!/usr/bin/env python3
"""cc-fulfil <client-email> — payment received: find the approved brief for this email, create the
job, and hand the build to the Code&Craft AI team (O/C). Called async by the Stripe webhook.

Two ways a brief is found:
  1. An awaiting-payment record (operator ran `cc-go` first), OR
  2. FALLBACK: pull the latest Tally submission for this email straight from the mailbox — this is the
     pay-on-submit path (client submitted Tally -> redirected to Stripe -> paid), so no `cc-go` step ran.
Matching is by email; the Tally redirect prefills the client's form email into Stripe, so the payer
email equals the brief email."""
import sys, os, json, subprocess, re
sys.path.insert(0, "/root/.openclaw/sp-provision")
import cc_go  # reuse the Tally brief reader + parser

PENDING = "/root/.openclaw/phase2/awaiting-payment.jsonl"


def notify(msg):
    try:
        subprocess.run(["cc-notify-operator", msg], timeout=60)
    except Exception:
        pass


def load_recs():
    if not os.path.exists(PENDING):
        return []
    return [json.loads(l) for l in open(PENDING) if l.strip()]


def main():
    email = sys.argv[1].lower()
    recs = load_recs()
    rec = next((r for r in reversed(recs)
                if r.get("brief", {}).get("clientEmail", "").lower() == email
                and r.get("status") == "awaiting-payment"), None)
    if rec is None:
        # Pay-on-submit fallback: read the brief from the Tally mailbox by email.
        body = cc_go.latest_tally(email)
        if not body:
            notify("Paid by %s — but no approved brief AND no Tally submission found for that email." % email)
            return
        brief = cc_go.parse_brief(body)
        if not brief.get("clientEmail"):
            brief["clientEmail"] = email
        rec = {"brief": brief, "status": "awaiting-payment", "source": "mailbox-fallback"}
        recs.append(rec)

    brief = rec["brief"]
    bf = "/tmp/brief-%s.json" % re.sub(r"[^a-z0-9]", "_", email)
    json.dump(brief, open(bf, "w"))
    r = subprocess.run(["cc-intake", bf], capture_output=True, text=True)
    mj = re.search(r"JOB\d+", r.stdout)
    if not mj:
        notify("Paid by %s — intake failed: %s" % (email, (r.stderr or r.stdout)[-200:]))
        return
    job = mj.group()
    rec["status"] = "paid:" + job
    open(PENDING, "w").write("\n".join(json.dumps(x) for x in recs) + "\n")
    notify("💰 Paid SGD%d by %s — created %s. Dispatching to the Code&Craft AI team to build…"
           % ((brief.get("pages") or 1) * 10, email, job))
    # Hand the build to O/C (the Delivery Lead + specialists), per CLIENT-BUILD.md. Async — the team
    # builds, deploys, verifies, delivers, and closes the card itself (with its own progress pings).
    msg = ("Build client job %s per /root/.openclaw/workspace-delivery-lead/CLIENT-BUILD.md (follow it exactly). "
           "Brief + manifest are in /srv/projects/%s. Build a real on-brand site with the FULL paid page count, "
           "then deploy with `cc-deploy %s` and run `cc-verify-client %s`. The verify gate — not you — emails the "
           "client and closes the card; you CANNOT self-close. If it FAILs, fix the real issue and re-run." % (job, job, job, job))
    subprocess.Popen(["openclaw", "agent", "--agent", "main", "--timeout", "1500", "--message", msg])


if __name__ == "__main__":
    main()
