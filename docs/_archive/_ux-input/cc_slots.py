#!/usr/bin/env python3
"""cc-slots — monthly request capacity (10/mo, auto-resets on the 1st) + a public
availability file the landing page reads to show slots-left or the waitlist.
Usage: cc-slots [status|claim|reset]
State:  /root/.openclaw/phase2/slots.json
Public: /var/www/teams/availability.json  ->  https://teams.codeandcraft.ai/availability.json
"""
import sys, json, os
from datetime import datetime, timezone

STATE = "/root/.openclaw/phase2/slots.json"
PUBLIC = "/var/www/teams/availability.json"
LIMIT = 10


def month_key():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def publish(d):
    left = max(0, d["limit"] - d["used"])
    pub = {"month": d["month"], "slotsLeft": left, "limit": d["limit"],
           "status": "open" if left > 0 else "full"}
    try:
        json.dump(pub, open(PUBLIC, "w"))
    except Exception as e:
        print("WARN: could not publish to", PUBLIC, "-", e)


def save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w"), indent=2)
    publish(d)


def load():
    try:
        d = json.load(open(STATE))
    except Exception:
        d = {}
    if d.get("month") != month_key():           # auto monthly reset
        d = {"month": month_key(), "used": 0, "limit": LIMIT}
        save(d)
    return d


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    d = load()
    if cmd == "claim":
        if d["used"] >= d["limit"]:
            print("FULL — 0 slots left this month (%s). Route to WAITLIST." % d["month"]); sys.exit(1)
        d["used"] += 1; save(d)
        print("CLAIMED — %d/%d used (%s); %d left" % (d["used"], d["limit"], d["month"], d["limit"] - d["used"]))
    elif cmd == "reset":
        d = {"month": month_key(), "used": 0, "limit": LIMIT}; save(d)
        print("RESET — %s, 0/%d used" % (d["month"], LIMIT))
    else:
        left = d["limit"] - d["used"]
        print("month %s | used %d/%d | left %d | status %s"
              % (d["month"], d["used"], d["limit"], left, "open" if left > 0 else "full"))
        print("public file:", json.load(open(PUBLIC)) if os.path.exists(PUBLIC) else "(not published yet)")


if __name__ == "__main__":
    main()
