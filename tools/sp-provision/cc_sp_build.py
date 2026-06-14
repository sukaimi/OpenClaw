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


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: cc-sp-build <JOB####>")
    job = sys.argv[1]
    jd = "/srv/projects/%s" % job
    cfg = json.load(open(jd + "/job.config.json"))
    pages = cfg.get("pages") or []
    cap = str(cfg.get("buildCap", 5))
    hcap = str(cfg.get("heavyWebpartCap", 6))
    has_capture = os.path.isdir(jd + "/capture")

    # 1. image-migrate — creates image-map.json + migrates sp-expect images.
    #    Capture jobs source bytes from the captured bundle (client tenant not app-readable).
    mig = [PY, PROV + "/image_migrate.py", "--job", job, "--out", jd + "/image-map.json"]
    if has_capture:
        mig += ["--from-capture", jd + "/capture"]
    run(mig)

    # 2. compose — merges manifest images+text, places everything via the 3 safety nets,
    #    publishes per page (capped). The fixes live inside canvas_compose.py.
    comp = [PY, PROV + "/canvas_compose.py", "--job", job,
            "--build-cap", cap, "--heavy-cap", hcap]
    if pages:
        comp += ["--pages", ",".join(pages)]
    run(comp)

    # 3. styler — attach wallpaper/brand only when configured.
    if (cfg.get("styler") or {}).get("wallpaperUrl"):
        run([PY, PROV + "/cc-sp-styler-attach.py", "--config", jd + "/job.config.json"])

    print("[build] done. Next: cc-verify-sp %s (the deterministic close-gate)." % job)


if __name__ == "__main__":
    main()
