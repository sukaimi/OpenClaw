#!/usr/bin/env python3
"""cc-resend <JOB####> <correct-email> [--dry] — re-send an already-delivered job (live URL + source zip)
to a corrected address. NO rebuild / NO redeploy. The wrong-email recovery path.
Reuses the verify gate's delivery email (URL + source zip attached), updates the brief's clientEmail to
the corrected one, notes the card, and pings the operator. Card stays Closed."""
import sys, os, json, time, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
import cc_verify_client as v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    job, email = args[0], args[1].strip()
    proj = "/srv/projects/%s" % job
    if not os.path.exists(proj + "/brief.json"):
        print("[resend] %s has no brief.json" % job); sys.exit(2)
    brief = json.load(open(proj + "/brief.json"))
    name = brief.get("clientName") or brief.get("brand") or "there"
    typ = brief.get("type", "multipage_site")
    url = open(proj + "/deploy-url.txt").read().strip() if os.path.exists(proj + "/deploy-url.txt") else ""
    old = brief.get("clientEmail", "")
    print("[resend]%s %s | was %s -> %s | url %s" % (" DRY" if dry else "", job, old or "(none)", email, url or "(none)"))
    if dry:
        print("  would: update brief email, re-send URL + source zip from hello@, note card, ping operator")
        return
    brief["clientEmail"] = email
    json.dump(brief, open(proj + "/brief.json", "w"), indent=2)
    code, hadzip = v.deliver(email, name, url, job, proj, typ)
    print("  delivery email %s | source attached: %s" % (code, hadzip))
    item = v.card_id(job)
    if item:
        v.move(item, "Closed", "RE-SENT %s to %s (was %s)" % (time.strftime("%Y-%m-%d"), email, old))
    try:
        subprocess.run(["cc-notify-operator", "↪️ %s re-sent to %s (was %s)" % (job, email, old)], timeout=60)
    except Exception:
        pass
    # clear any prior bounce flag (it's been re-delivered)
    try:
        os.remove(proj + "/.bounced")
    except OSError:
        pass
    print("[resend] done")


if __name__ == "__main__":
    main()
