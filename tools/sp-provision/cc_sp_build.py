#!/usr/bin/env python3
"""cc-sp-build <JOB####> — SERVER-SIDE build runner for the SP conversion harness.

Runs the server build stages LOCALLY (no SSH, no Mac-side stages), reading params from
job.config.json: image_migrate -> canvas_compose (source-of-truth merges + 3 safety nets)
-> styler (only if styler.wallpaperUrl set). Aborts on the first failure.

Split of concerns (Level-2 model): the Mac/operator side captures the source + populates
capture/ + manifests/ at intake (delegated session — the client tenant is NOT app-cert
readable). This runner is the autonomous SERVER build. The authoritative close-gate is
`cc-verify-sp` (server, Graph read-back) — this runner never self-closes.
"""
import json
import os
import subprocess
import sys

PROV = "/root/.openclaw/sp-provision"
PY = "/root/.openclaw/venv/bin/python"


def run(cmd):
    print("[build] RUN:", " ".join(cmd), flush=True)
    if subprocess.run(cmd).returncode:
        sys.exit("[build] stage FAILED — aborting: %s" % " ".join(cmd))


def _guardrail_pages(jd, cfg, job, cfg_pages, cap):
    """Decide which pages this build run touches, applying triage + scope-gate +
    waves (JOB0024-108). Backward-compatible: with no worklist/scope-approval it
    falls back to the legacy 'cfg pages capped at buildCap' behaviour."""
    inv = jd + "/site-inventory.json"
    if not os.path.exists(inv) and os.path.exists(jd + "/capture/site-inventory.json"):
        inv = jd + "/capture/site-inventory.json"
    # produce the triage scope-sheet (informational) if we have an inventory and none yet
    if os.path.exists(inv) and not os.path.exists(jd + "/scope-sheet.json"):
        subprocess.run([PY, PROV + "/cc_sp_triage.py", inv,
                        "--config", jd + "/job.config.json", "--out-dir", jd])
    worklist = jd + "/worklist.json"
    if os.path.exists(worklist):
        wl = json.load(open(worklist))
        wave = int(cfg.get("waveSize") or wl.get("waveSize") or cap)
        pending = [p["file"] for p in wl["pages"] if p.get("status") == "pending"]
        sel = pending[:wave]
        print("[build] guardrails: WAVE mode — building %d of %d pending (waveSize %d)"
              % (len(sel), len(pending), wave))
        return sel, True
    # legacy path: cfg pages capped; enforce scope-approval if present
    sel = (cfg_pages or [])[:cap]
    approved_path = jd + "/scope-approved.json"
    if os.path.exists(approved_path):
        approved = set(json.load(open(approved_path)).get("approvedFiles", []))
        skipped = [p for p in sel if p not in approved]
        sel = [p for p in sel if p in approved]
        if skipped:
            print("[build] scope-gate: SKIPPED %d un-approved page(s): %s"
                  % (len(skipped), ", ".join(skipped)))
    elif cfg_pages:
        print("[build] guardrails: no worklist/scope-approval — LEGACY build (scope-gate not enforced)")
    return sel, False


def _mark_worklist(jd, pages, status):
    wp = jd + "/worklist.json"
    if not os.path.exists(wp):
        return
    wl = json.load(open(wp))
    s = set(pages)
    for p in wl["pages"]:
        if p.get("file") in s:
            p["status"] = status
    json.dump(wl, open(wp, "w"), indent=1)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: cc-sp-build <JOB####>")
    job = sys.argv[1]
    jd = "/srv/projects/%s" % job
    cfg = json.load(open(jd + "/job.config.json"))
    pages = cfg.get("pages") or []
    cap = int(cfg.get("buildCap", 5))
    hcap = str(cfg.get("heavyWebpartCap", 6))
    has_capture = os.path.isdir(jd + "/capture")

    # 1. image-migrate — creates image-map.json + migrates sp-expect images.
    #    Capture jobs source bytes from the captured bundle (client tenant not app-readable).
    mig = [PY, PROV + "/image_migrate.py", "--job", job, "--out", jd + "/image-map.json"]
    if has_capture:
        mig += ["--from-capture", jd + "/capture"]
    run(mig)

    # 2. GUARDRAILS (JOB0024-108): triage -> scope-gate -> wave selection -> backup-on -> compose.
    build_pages, wave_mode = _guardrail_pages(jd, cfg, job, pages, cap)
    if not build_pages:
        print("[build] guardrails: nothing to build this wave (no pending/approved pages).")
    else:
        env = dict(os.environ, CC_SP_BACKUP_DIR=jd + "/backups")  # snapshot each page before overwrite
        comp = [PY, PROV + "/canvas_compose.py", "--job", job,
                "--build-cap", str(len(build_pages)), "--heavy-cap", hcap,
                "--pages", ",".join(build_pages)]
        print("[build] RUN:", " ".join(comp), flush=True)
        if subprocess.run(comp, env=env).returncode:
            _mark_worklist(jd, build_pages, "failed")
            sys.exit("[build] compose FAILED — aborting (worklist pages marked failed)")
        _mark_worklist(jd, build_pages, "done")

    # 3. styler — attach wallpaper/brand only when configured.
    if (cfg.get("styler") or {}).get("wallpaperUrl"):
        run([PY, PROV + "/cc-sp-styler-attach.py", "--config", jd + "/job.config.json"])

    print("[build] done. Next: cc-verify-sp %s (close-gate), then "
          "cc-sp-rollup.mjs %s for exceptions.md." % (job, jd))


if __name__ == "__main__":
    main()
