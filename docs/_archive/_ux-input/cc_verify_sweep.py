#!/usr/bin/env python3
"""cc-verify-sweep [--dry] — safety-net sweep that auto-recovers STALLED client builds (BL-012a).

Enumerates client Kanban cards (Graph, fields expand) whose Stage is "Build" or "Internal QA"
AND whose /srv/projects/<JOB>/.verified marker is MISSING (i.e. delivered/built but never gated).
For each, it runs the REAL deterministic gate `cc-verify-client <JOB>` — which on PASS closes the
card + delivers, on FAIL bounces it back to Build. This script makes no close/deliver decisions
itself; it only triggers the gate. Idempotent: once a job is verified (.verified written) it no
longer appears as a candidate, so re-running is safe.

Skips JOB0003 (the ENGINE, not a client job) and any job without /srv/projects/<JOB>/brief.json.
--dry lists what it WOULD verify without running the gate.

Intended to run every ~20 min via /etc/cron.d/cc-verify-sweep."""
import sys, os, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)
PROJECTS = "/srv/projects"
SWEEP_STAGES = {"build", "internal qa"}


def cards():
    r = requests.get(BASE + "/items?expand=fields&top=400",
                     headers={"Authorization": "Bearer " + graph_token()})
    out = []
    for it in r.json().get("value", []):
        f = it.get("fields") or {}
        job = f.get("ProjectNo") or ""
        out.append((job, (f.get("Stage") or "")))
    return out


def is_candidate(job, stage):
    if not job or job == "JOB0003":
        return False
    if str(stage).strip().lower() not in SWEEP_STAGES:
        return False
    proj = os.path.join(PROJECTS, job)
    if not os.path.exists(os.path.join(proj, "brief.json")):
        return False
    if os.path.exists(os.path.join(proj, ".verified")):
        return False  # already gated -> not stalled
    return True


def main():
    dry = "--dry" in sys.argv
    seen = set()
    candidates = []
    for job, stage in cards():
        if job in seen:
            continue
        if is_candidate(job, stage):
            seen.add(job)
            candidates.append((job, stage))

    print("[verify-sweep]%s %d stalled client candidate(s)" % (" DRY" if dry else "", len(candidates)))
    if not candidates:
        return
    for job, stage in candidates:
        if dry:
            print("  WOULD verify %s (stage=%s, no .verified)" % (job, stage))
            continue
        print("  verifying %s (stage=%s) ..." % (job, stage))
        try:
            p = subprocess.run(["cc-verify-client", job], capture_output=True, text=True, timeout=600)
            tail = (p.stdout or p.stderr or "").strip().splitlines()
            print("    rc=%d %s" % (p.returncode, tail[-1] if tail else ""))
        except Exception as e:
            print("    ERROR running gate:", str(e)[:120])


if __name__ == "__main__":
    main()
