#!/usr/bin/env python3
"""cc-verify-bridge — SERVER side of the operator-assisted Verify-at-intake flow.

Bridges the Command Center "Intake Briefs" list <-> the Mac-side `cc-verify-watch`
worker (which can't accept inbound calls) through the file queue /srv/verify-queue/.

  setup   add the verify columns to "Intake Briefs" (idempotent)
  run     ENQUEUE pending verify requests + RECONCILE finished captures (cron this)

Flow: operator sets VerifyRequested=Yes (the form "Verify" button) -> ENQUEUE writes
/srv/verify-queue/<itemId>.json -> the Mac worker captures over the operator's login
popup + ships the bundle to /srv/intake-captures/<itemId>/ + writes <itemId>.result.json
-> RECONCILE sets AccessVerified=Verified (or Failed), moves the bundle into the JOB dir
(if JOBNumber set) + runs sp-audit --from-capture. Submit stays gated on AccessVerified.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, "/root/.openclaw/sp-provision")
import spclient  # noqa: E402
import requests  # noqa: E402

QUEUE = "/srv/verify-queue"
CAPTURES = "/srv/intake-captures"
PROV = "/root/.openclaw/sp-provision"
PY = "/root/.openclaw/venv/bin/python"
LIST = "Intake Briefs"

VERIFY_COLS = [
    ("VerifyRequested", {"boolean": {}}),
    ("AccessVerified", {"choice": {"choices": ["Pending", "Verified", "Failed"]}}),
    ("CaptureId", {"text": {}}),
    ("VerifyNotes", {"text": {}}),
]


def _ctx():
    sp = spclient.SP()
    lid = sp.list_id(LIST)
    base = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (sp.site_id(), lid)
    return sp, base


def _patch(sp, base, item_id, fields):
    r = requests.patch(base + "/items/%s/fields" % item_id,
                       headers={**sp.H, "Content-Type": "application/json"},
                       data=json.dumps(fields))
    if r.status_code >= 300:
        print("  PATCH %s FAILED %d: %s" % (item_id, r.status_code, r.text[:160]))
    return r.status_code < 300


def cmd_setup():
    sp, base = _ctx()
    existing = {c.get("name") for c in sp.list_columns(LIST) if isinstance(c, dict)}
    for name, typ in VERIFY_COLS:
        if name in existing:
            print("col exists:", name)
            continue
        r = requests.post(base + "/columns",
                          headers={**sp.H, "Content-Type": "application/json"},
                          data=json.dumps({"name": name, **typ}))
        print("add col %-16s -> %d %s" % (name, r.status_code,
              "ok" if r.status_code < 300 else r.text[:140]))


def cmd_run():
    os.makedirs(QUEUE + "/done", exist_ok=True)
    sp, base = _ctx()
    items = sp.items(LIST)

    # ---- ENQUEUE: VerifyRequested && not-yet-Verified && has URL && not already queued ----
    for it in items:
        f = it.get("fields", it) if isinstance(it, dict) else {}
        iid = str(it.get("id") or f.get("id") or "")
        if not iid:
            continue
        if str(f.get("VerifyRequested")).lower() not in ("true", "1", "yes"):
            continue
        if (f.get("AccessVerified") or "") == "Verified":
            continue
        url = f.get("SourceSiteURL")
        if not url:
            continue
        if os.path.exists("%s/%s.json" % (QUEUE, iid)) or os.path.exists("%s/%s.result.json" % (QUEUE, iid)):
            continue
        json.dump({"itemId": iid, "url": url, "job": f.get("JOBNumber") or ""},
                  open("%s/%s.json" % (QUEUE, iid), "w"), indent=2)
        _patch(sp, base, iid, {"AccessVerified": "Pending", "VerifyNotes": "queued for capture"})
        print("ENQUEUED item %s  %s" % (iid, url))

    # ---- RECONCILE: each finished capture result -> update the list item ----
    for rf in glob.glob("%s/*.result.json" % QUEUE):
        rid = os.path.basename(rf)[:-len(".result.json")]
        try:
            res = json.load(open(rf))
        except Exception:
            continue
        try:
            req = json.load(open("%s/%s.json" % (QUEUE, rid)))
        except Exception:
            req = {}
        job = (req.get("job") or "").strip()

        if res.get("ok"):
            notes = "verified: %s pages, %s images" % (res.get("pages"), res.get("images"))
            bundle = "%s/%s" % (CAPTURES, rid)
            if job and os.path.isdir(bundle):
                dst = "/srv/projects/%s" % job
                os.makedirs(dst, exist_ok=True)
                if os.path.isdir(dst + "/capture"):
                    shutil.rmtree(dst + "/capture", ignore_errors=True)
                shutil.move(bundle, dst + "/capture")
                subprocess.run([PY, PROV + "/sp-audit.py", "--from-capture",
                                dst + "/capture", "--job", job, "--out", dst + "/sp-expect.json"])
                notes += "; bundle -> %s/capture + sp-expect generated" % dst
            _patch(sp, base, rid, {"AccessVerified": "Verified", "CaptureId": rid,
                                   "VerifyRequested": False, "VerifyNotes": notes})
            print("RECONCILED %s -> VERIFIED (%s)" % (rid, notes))
        else:
            _patch(sp, base, rid, {"AccessVerified": "Failed", "VerifyRequested": False,
                                   "VerifyNotes": "verify failed: %s" % res.get("error")})
            print("RECONCILED %s -> FAILED: %s" % (rid, res.get("error")))

        # archive processed queue files so they aren't reprocessed
        for ext in (".json", ".result.json"):
            p = "%s/%s%s" % (QUEUE, rid, ext)
            if os.path.exists(p):
                shutil.move(p, "%s/done/%s%s" % (QUEUE, rid, ext))


def main():
    {"setup": cmd_setup, "run": cmd_run}.get(sys.argv[1] if len(sys.argv) > 1 else "run", cmd_run)()


if __name__ == "__main__":
    main()
