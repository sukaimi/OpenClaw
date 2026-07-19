#!/usr/bin/env python3
"""Verify-at-intake SUBMIT-GATE: a brief that has a SourceSiteURL (a conversion
needing source capture) cannot become a JOB / start a build until its source
access has been verified (AccessVerified == "Verified"). Briefs with NO source
URL (fresh redesigns) are unaffected. Patches the two JOB-launch points."""
import time

WATCH = "/root/.openclaw/sp-provision/cc_intake_watch.py"
AUTORUN = "/root/.openclaw/sp-provision/cc_intake_autorun.py"

# ---- 1) cc_intake_watch.py : _is_ready_brief ----
w_old = '''def _is_ready_brief(fields):
    status = first_field(fields, "Status")
    signed = first_field(fields, "SignedOff")
    job = first_field(fields, "JOBNumber", "JobNumber")
    return (str(status).strip().lower() == ST_APPROVED.lower()
            and _truthy(signed)
            and not job)'''
w_new = '''def _is_ready_brief(fields):
    status = first_field(fields, "Status")
    signed = first_field(fields, "SignedOff")
    job = first_field(fields, "JOBNumber", "JobNumber")
    # verify-at-intake submit-gate: a brief with a source site to capture cannot
    # become a JOB until its source access has been Verified.
    src = first_field(fields, "SourceSiteURL")
    verified = str(first_field(fields, "AccessVerified")).strip().lower() == "verified"
    if src and not verified:
        return False
    return (str(status).strip().lower() == ST_APPROVED.lower()
            and _truthy(signed)
            and not job)'''

# ---- 2) cc_intake_autorun.py : hop 2 launch ----
a_old = '''        # hop 2: launch on signoff
        if status == "approved" and signed and not jobno:
            print("[launch] item %s \'%s\'%s" % (iid, title, " (DRY)" if DRY else ""))'''
a_new = '''        # hop 2: launch on signoff
        if status == "approved" and signed and not jobno:
            # verify-at-intake submit-gate: a brief with a source site to capture
            # cannot start a build until AccessVerified == Verified.
            if src and (f.get("AccessVerified") or "").strip().lower() != "verified":
                print("[gate] item %s \'%s\' BLOCKED — source set, AccessVerified != Verified" % (iid, title))
                continue
            print("[launch] item %s \'%s\'%s" % (iid, title, " (DRY)" if DRY else ""))'''

for path, old, new in ((WATCH, w_old, w_new), (AUTORUN, a_old, a_new)):
    txt = open(path).read()
    if new.split("\n")[2] in txt and "submit-gate" in txt:
        print("ALREADY PATCHED:", path)
        continue
    n = txt.count(old)
    assert n == 1, "anchor count %d (expected 1) in %s" % (n, path)
    open(path + ".bak-vgate-%d" % int(time.time()), "w").write(txt)
    open(path, "w").write(txt.replace(old, new, 1))
    print("PATCHED:", path)

# syntax check
import py_compile
for p in (WATCH, AUTORUN):
    py_compile.compile(p, doraise=True)
    print("compiles OK:", p)
