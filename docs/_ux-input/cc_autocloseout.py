#!/usr/bin/env python3
"""cc-autocloseout [--dry] — auto wind-down of DELIVERED client jobs past the grace window (BL-012b).

Finds jobs that genuinely meet ALL of:
  - /srv/projects/<JOB>/.verified PRESENT   (delivered/gated)
  - card Stage == "Closed"
  - /srv/projects/<JOB>/.closedout ABSENT   (not already wound down)
  - delivery happened more than N days ago  (N default 14, env CC_CLOSEOUT_DAYS)
Delivery timestamp = the "ts" field inside .verified (falls back to its mtime).
For each match it runs `cc-closeout <JOB>`.

CAUTION: cc-closeout takes the hosted site DOWN and emails the client. This tool is deliberately
conservative — it acts ONLY on jobs satisfying every condition above and older than N days.
Skips JOB0003 (ENGINE) and any job without brief.json. Idempotent: once .closedout exists a job
is no longer a candidate. --dry lists candidates with their computed age and never acts.

Intended to run daily via /etc/cron.d/cc-autocloseout."""
import sys, os, json, time, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)
PROJECTS = "/srv/projects"


def closeout_days():
    try:
        return int(os.environ.get("CC_CLOSEOUT_DAYS", "14"))
    except ValueError:
        return 14


def cards():
    r = requests.get(BASE + "/items?expand=fields&top=400",
                     headers={"Authorization": "Bearer " + graph_token()})
    out = []
    for it in r.json().get("value", []):
        f = it.get("fields") or {}
        out.append(((f.get("ProjectNo") or ""), (f.get("Stage") or "")))
    return out


def delivered_ts(proj):
    vf = os.path.join(proj, ".verified")
    try:
        data = json.load(open(vf))
        ts = data.get("ts")
        if ts:
            return float(ts)
    except Exception:
        pass
    try:
        return os.path.getmtime(vf)
    except OSError:
        return None


def main():
    dry = "--dry" in sys.argv
    days = closeout_days()
    cutoff = days * 86400.0
    now = time.time()

    seen = set()
    candidates = []
    for job, stage in cards():
        if not job or job == "JOB0003" or job in seen:
            continue
        if str(stage).strip().lower() != "closed":
            continue
        proj = os.path.join(PROJECTS, job)
        if not os.path.exists(os.path.join(proj, "brief.json")):
            continue
        if not os.path.exists(os.path.join(proj, ".verified")):
            continue
        if os.path.exists(os.path.join(proj, ".closedout")):
            continue
        ts = delivered_ts(proj)
        if ts is None:
            continue
        age = now - ts
        if age <= cutoff:
            continue
        seen.add(job)
        candidates.append((job, age))

    print("[autocloseout]%s N=%dd | %d candidate(s) ready to wind down"
          % (" DRY" if dry else "", days, len(candidates)))
    if not candidates:
        return
    for job, age in candidates:
        age_d = age / 86400.0
        if dry:
            print("  WOULD close out %s (delivered %.1f days ago, threshold %dd)" % (job, age_d, days))
            continue
        print("  closing out %s (delivered %.1f days ago) ..." % (job, age_d))
        try:
            p = subprocess.run(["cc-closeout", job], capture_output=True, text=True, timeout=600)
            tail = (p.stdout or p.stderr or "").strip().splitlines()
            print("    rc=%d %s" % (p.returncode, tail[-1] if tail else ""))
        except Exception as e:
            print("    ERROR running closeout:", str(e)[:120])


if __name__ == "__main__":
    main()
