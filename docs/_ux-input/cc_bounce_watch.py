#!/usr/bin/env python3
"""cc-bounce-watch [--dry] — scan the hello@ inbox for delivery bounces (NDRs) and flag the matching
client job, so the operator knows a delivery failed and can get a corrected address -> `cc-resend`.

Detection: a message from postmaster/mailer-daemon, or a bounce-style subject, whose BODY contains the
clientEmail of an active delivered job (.verified present, not .closedout). Idempotent via a per-job
`.bounced` marker (cleared when cc-resend re-delivers). NOTE: only catches INVALID mailboxes (which bounce)
— a valid-but-wrong address won't bounce, so only the client reaching out surfaces that."""
import sys, os, json, re, glob, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

MBX = "hello@codeandcraft.ai"
BOUNCE_SUBJ = re.compile(
    r"undeliverable|delivery (status notification|has failed|failure)|failure notice|returned mail|"
    r"could ?n.?t be delivered|delivery incomplete|mail delivery failed", re.I)


def inbox(n=30):
    r = requests.get("https://graph.microsoft.com/v1.0/users/%s/messages?$top=%d"
                     "&$select=from,subject,body,receivedDateTime&$orderby=receivedDateTime desc" % (MBX, n),
                     headers={"Authorization": "Bearer " + graph_token()})
    return r.json().get("value", [])


def is_bounce(m):
    frm = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
    if any(x in frm for x in ("postmaster", "mailer-daemon", "mailerdaemon")):
        return True
    return bool(BOUNCE_SUBJ.search(m.get("subject") or ""))


def active_jobs():
    out = {}
    for d in glob.glob("/srv/projects/JOB*"):
        if os.path.exists(d + "/brief.json") and os.path.exists(d + "/.verified") and not os.path.exists(d + "/.closedout"):
            try:
                e = (json.load(open(d + "/brief.json")).get("clientEmail") or "").lower()
                if e:
                    out[e] = os.path.basename(d)
            except Exception:
                pass
    return out


def main():
    dry = "--dry" in sys.argv
    jobs = active_jobs()
    if not jobs:
        print("[bounce-watch]%s no active delivered jobs to match" % (" DRY" if dry else "")); return
    flagged = 0
    for m in inbox():
        if not is_bounce(m):
            continue
        body = ((m.get("body") or {}).get("content") or "").lower()
        for email, job in jobs.items():
            marker = "/srv/projects/%s/.bounced" % job
            if email in body and not os.path.exists(marker):
                flagged += 1
                print("BOUNCE: %s -> %s" % (job, email))
                if dry:
                    continue
                open(marker, "w").write(email)
                try:
                    subprocess.run(["cc-notify-operator",
                                    "⚠️ %s — delivery to %s BOUNCED. Get the correct address, then run: "
                                    "cc-resend %s <correct-email>" % (job, email, job)], timeout=60)
                except Exception:
                    pass
    print("[bounce-watch]%s %d bounce(s) flagged" % (" DRY" if dry else "", flagged))


if __name__ == "__main__":
    main()
