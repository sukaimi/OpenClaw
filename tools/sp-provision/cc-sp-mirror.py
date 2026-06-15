#!/usr/bin/env python3
"""
cc-sp-mirror — config-driven DRIVER for the Code&Craft SharePoint classic->modern pipeline.

Given a per-job job.config.json, it sequences the FULL proven pipeline by REUSING the
existing proven scripts (it does NOT reimplement them). One config entry makes the pipeline
reusable on ANY site with ZERO per-site hardcoding.

  Usage:
    cc-sp-mirror.py --config <jobDir>/job.config.json [--dry-run] [--from <stage>] [--only <stage>]

  --dry-run   print the ordered step plan with this job's params threaded through; execute NOTHING.
  --from      start at a named stage (resume); run that stage onward.
  --only      run a single named stage.

job.config.json schema (the SHARED CONTRACT — T5/T6 step scripts conform to the same):
  {
    "job": "JOB####",
    "sourceUrl":  "<classic source site URL>",
    "targetSite": "<modern build site URL>",
    "pages":      ["Page1.aspx", ...]   |  "topNactive": <int>,   # page selection (one of)
    "buildCap":   <int>,                # max pages built this run (test gate; RDQ test = 5)
    "heavyWebpartCap": 6,               # T1 heavy-media web-part batch size per page
    "styler": { "wallpaperUrl": "<url|null>", "brandColor": "#hex" },
    "jobDir":  "/srv/projects/<JOB>"    # server-side job dir; ALL artifacts live here
  }

ORCHESTRATION (cross Mac / server):
  - Mac-side (authed, needs an interactive SP session storageState): the .mjs capture/manifest/gate.
  - Server-side (Graph app-cert): the .py audit/migrate/compose/style/closeout + the .xlsx tracker.
  This driver runs ON THE MAC and shells the server stages over SSH. Each stage declares WHERE it
  runs; the driver moves the small JSON artifacts (config, source manifest) to where they are needed.

IMAGE-MAP COMPLETENESS (folds prior task #5):
  The T3 completeness gate consumes <jobDir>/image-map.json (--image-map) to NAME swaps.
  Both migration paths must populate it fully:
    - ARTICLE path:  image_migrate.py  --out <jobDir>/image-map.json   (writes the full _map).
    - HOMEPAGE path: sp_home_compose.py merges its uploaded homepage images into the SAME
                     image-map.json (its _merge_image_map step) — closes the old home2/ gap where
                     homepage migrations were not recorded.
  After both run, the driver asserts image-map.json exists and is non-empty before the gate stage.
"""

import sys, os, json, argparse, shlex, subprocess, datetime
from urllib.parse import urlparse

# ---- where the reused scripts live (no per-site values; pure tool locations) ----
SERVER = "root@76.13.179.220"
SSH = ["ssh", "-o", "ConnectTimeout=8", SERVER]
SRV_PROV = "/root/.openclaw/sp-provision"          # server-side .py tools
MAC_QA = os.path.dirname(os.path.abspath(__file__))  # this driver's dir is the Mac mirror
# the .mjs capture/gate live in the cc-visual-qa tree; allow override via env
MAC_QA_TOOLS = os.environ.get(
    "CC_VISUAL_QA",
    os.path.expanduser("~/Workspace2/OpenClaw/tools/cc-visual-qa"),
)
NODE = os.environ.get("CC_NODE", "node")
# Build-tenant Playwright session the gate uses to read the BUILT page's web-part JSON
# (codeandcanvas.sharepoint.com). NOT the verify-<host> intranet session used for SOURCE capture.
BUILD_STATE = os.environ.get(
    "CC_BUILD_STATE",
    os.path.expanduser("~/.codecraft/sp-storage-state.json"),
)


def log(msg):
    print("[mirror] %s" % msg, flush=True)


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    for k in ("job", "sourceUrl", "targetSite", "jobDir"):
        if not cfg.get(k):
            raise SystemExit("config missing required key: %s" % k)
    if not cfg.get("pages") and not cfg.get("topNactive"):
        raise SystemExit("config needs page selection: 'pages' or 'topNactive'")
    cfg.setdefault("buildCap", 5)
    cfg.setdefault("heavyWebpartCap", 6)
    cfg.setdefault("styler", {})
    return cfg


def page_selection_args(cfg):
    """Return the page-selection flags threaded from config (no hardcoded names)."""
    if cfg.get("pages"):
        return "--pages " + shlex.quote(",".join(cfg["pages"]))
    return "--top-active %d" % int(cfg["topNactive"])


def article_pages(cfg):
    """The explicit article page list (e.g. 'Innovation is the Key to Success.aspx').
    Per-page gating requires named pages; when selection is top-active (no explicit names)
    only the HOME page is gated and a note flags that the article list is resolved at run
    time. Returns [] when no explicit 'pages' are configured."""
    return list(cfg.get("pages") or [])


def manifest_stem(page):
    """Manifest/built filename stem for a page name: drop a trailing .aspx.
    'Innovation is the Key to Success.aspx' -> 'Innovation is the Key to Success'."""
    return page[:-5] if page.lower().endswith(".aspx") else page


def page_targets(cfg):
    """Ordered list of (label, source_manifest, built_canvas_url, min_sections) tuples — one
    per gated page. HOME is always first (home-manifest.json vs SitePages/Home.aspx). Each
    configured article follows: its per-article source manifest under <jobDir>/manifests/<stem>.json
    vs its built SitePages/<page> URL. EVERY tuple is gated; the job FAILS if ANY page fails."""
    jobDir = cfg["jobDir"]
    tgt = cfg["targetSite"]
    targets = [(
        "home",
        "%s/home-manifest.json" % jobDir,
        "%s/SitePages/Home.aspx" % tgt,
        2,
    )]
    for page in article_pages(cfg):
        stem = manifest_stem(page)
        targets.append((
            stem,
            "%s/manifests/%s.json" % (jobDir, stem),
            "%s/SitePages/%s" % (tgt, page),
            1,
        ))
    return targets


def build_plan(cfg, server_mode=False):
    """Return the ORDERED stage plan. Each stage: name, where (mac|server), cmd (str), note.
    `cmd` is the literal invocation, params threaded from cfg — printed verbatim on --dry-run."""
    job = cfg["job"]
    jobDir = cfg["jobDir"]
    cfgPath = "%s/job.config.json" % jobDir
    src = cfg["sourceUrl"]
    tgt = cfg["targetSite"]
    # Source-side .mjs (capture/probe) need the SOURCE tenant's delegated session
    # (per-host ~/.codecraft/verify-<host>.json), NOT cc-sp-capture's build-tenant
    # default (sp-storage-state.json). cc-sp-manifest already resolves per-host itself.
    src_state = os.path.expanduser("~/.codecraft/verify-%s.json" % urlparse(src).netloc)
    cap = int(cfg["buildCap"])
    hcap = int(cfg["heavyWebpartCap"])
    sel = page_selection_args(cfg)
    src_man = "%s/home-manifest.json" % jobDir   # source manifest used by the gate
    imap = "%s/image-map.json" % jobDir
    styler = cfg.get("styler") or {}
    wall = styler.get("wallpaperUrl")
    brand = styler.get("brandColor")

    P = []  # plan

    # 1. verify-access — confirm we can READ the source + WRITE the target before doing work.
    #    Source-side probe is Mac-only (delegated session); skipped in --server mode since
    #    verify-at-intake already confirmed access + populated the capture bundle.
    #    Target writability (app-cert) always runs server-side.
    if not server_mode:
        P.append(dict(
            name="verify-access", where="mac",
            cmd="%s %s/cc-sp-capture.mjs %s --job %s --probe --state %s"
                % (NODE, MAC_QA_TOOLS, shlex.quote(src), job, shlex.quote(src_state)),
            note="SOURCE readable: probe the classic site over the delegated session "
                 "(enumerate pages/lists/nav; exits non-zero if the session can't reach _api)."))
    P.append(dict(
        name="verify-access", where="server",
        cmd="python3 %s/cc_preflight_sp.py --job %s --source %s --target %s"
            % (SRV_PROV, job, shlex.quote(src), shlex.quote(tgt)),
        note="TARGET writable: app-cert preflight (web reachable + AddListItems perm); "
             "abort early if not."))

    # 2. capture — Mac-side only. Skipped in --server mode: verify-at-intake already
    #    populated the capture bundle before dispatch. In Mac mode, also skipped if the
    #    bundle already exists on the server (e.g. re-run after a partial failure).
    if not server_mode:
        P.append(dict(
            name="capture", where="mac",
            cmd="%s %s/cc-sp-capture.mjs %s --job %s --out %s/capture %s --state %s --inventory-out %s/site-inventory.json"
                % (NODE, MAC_QA_TOOLS, shlex.quote(src), job, jobDir, sel, shlex.quote(src_state), jobDir),
            note="authed bundle (pages+lists+images) + full site-inventory.json (ALL pages, before --pages filter). "
                 "Then build the source manifest the gate diffs:"))
        P.append(dict(
            name="capture", where="mac",
            cmd="%s %s/cc-sp-manifest.mjs %s %s --auth --download-images %s/capture/images --images-map %s/capture/images-map.json"
                % (NODE, MAC_QA_TOOLS, shlex.quote(src), src_man, jobDir, jobDir),
            note="HOME source manifest (img + bg-image + links + text) — gated vs SitePages/Home.aspx; "
                 "also downloads CONTENT image bytes (fresh afdcache) into capture/ so image_migrate has them."))
        for page in article_pages(cfg):
            stem = manifest_stem(page)
            art_src = "%s/Pages/%s" % (src, page)
            art_man = "%s/manifests/%s.json" % (jobDir, stem)
            P.append(dict(
                name="capture", where="mac",
                cmd="%s %s/cc-sp-manifest.mjs %s %s --auth --download-images %s/capture/images --images-map %s/capture/images-map.json"
                    % (NODE, MAC_QA_TOOLS, shlex.quote(art_src), shlex.quote(art_man), jobDir, jobDir),
                note="ARTICLE source manifest for %r — gated per-page; also downloads its CONTENT "
                     "image bytes into capture/ (closes the rendered-only-image gap)." % page))

    # 3. audit — server-side, from the capture bundle -> sp-expect.json (drives compose).
    P.append(dict(
        name="audit", where="server",
        cmd="python3 %s/sp-audit.py --job %s --from-capture %s/capture --out %s/sp-expect.json"
            % (SRV_PROV, job, jobDir, jobDir),
        note="capture -> sp-expect.json (+enrich); reusable, content-driven."))

    # 3b. scorer — Phase 1 page scoring: reads sp-expect.json, writes sp-scored.json with
    #     tier (1/2/3) + priority_score + complexity_flag per page. Tracker consumes this
    #     to populate Tier/Priority Score/Complexity columns and sort Sheet 1.
    P.append(dict(
        name="scorer", where="server",
        cmd="python3 %s/cc_sp_scorer.py --job %s --out %s/sp-scored.json"
            % (SRV_PROV, jobDir, jobDir),
        note="Phase 1 scoring: sp-expect.json -> sp-scored.json (tier+priority per page)."))

    # 3c. notify — Phase 2: send Teams/Telegram message with tier breakdown.
    #     Informational only — no gate, O/C immediately proceeds.
    P.append(dict(
        name="notify", where="server",
        cmd="python3 %s/cc_sp_notify_plan.py --job %s --config %s" % (SRV_PROV, job, cfgPath),
        note="Phase 2: tier-breakdown Teams ping (informational, no gate)."))

    # 4. image-migrate — ARTICLE path; writes the FULL _map to image-map.json.
    P.append(dict(
        name="image-migrate", where="server",
        cmd="python3 %s/image_migrate.py --job %s --out %s" % (SRV_PROV, job, imap),
        note="article images: src -> renamed built URL map (deterministic ordered names)."))

    # 5. compose — articles via canvas_compose; the list-driven home via sp_home_compose.
    #    apply_page is INTERNAL to canvas_compose (publish in place / fresh-name-on-retry).
    #    buildCap gates how many pages are built this run.
    P.append(dict(
        name="compose", where="server",
        cmd="python3 %s/cc_sp_batch_runner.py --config %s" % (SRV_PROV, cfgPath),
        note="Phase 3: tier-ordered batch compose (10/batch); exceptions logged, non-fatal."))
    P.append(dict(
        name="compose", where="server",
        cmd="python3 %s/sp_home_compose.py --job %s --config %s" % (SRV_PROV, job, cfgPath),
        note="list-driven home -> modern canvas; MERGES homepage image migrations into image-map.json."))

    # 6. style — T6 styler-attach step (per contract). wallpaper + brand from config.
    P.append(dict(
        name="style", where="server",
        cmd="python3 %s/cc-sp-styler-attach.py --config %s" % (SRV_PROV, cfgPath),
        note="T6 (may not exist yet). Attaches styler with per-site wallpaper=%s brand=%s."
             % (wall, brand)))

    # 7. verify — server-side Python gate via cc_sp_verify_gate.py. Reads CanvasContent1
    #    directly from the build tenant via Graph app-cert (no Playwright session needed).
    #    Runs once per page; FAILS the job if ANY page fails.
    for (label, page_src_man, built_url, min_sec) in page_targets(cfg):
        verdict_out = "%s/qa-verdict-%s.json" % (jobDir, label)
        page_file = built_url.split("/SitePages/")[-1]  # e.g. "Home.aspx"
        P.append(dict(
            name="verify", where="server",
            cmd="python3 %s/cc_sp_verify_gate.py --source %s --built-site-url %s --page %s "
                "--image-map %s --min-sections %d --out %s --job %s"
                % (SRV_PROV, shlex.quote(page_src_man), shlex.quote(tgt),
                   shlex.quote(page_file), imap, min_sec, shlex.quote(verdict_out), job),
            note="server gate page %r: CanvasContent1 diff via SP REST app-cert; FAIL aborts closeout." % label))

    # 8. tracker — T5 deliverable. Runs AFTER verify so qa-verdict-*.json files exist and
    #    Sheet3 per-page status reflects the ACTUAL gate result (not self-asserted). The tracker
    #    is a deliverable, not a build input — nothing downstream consumes it before closeout.
    P.append(dict(
        name="tracker", where="server",
        cmd="python3 %s/cc-sp-tracker.py --config %s" % (SRV_PROV, cfgPath),
        note="T5 xlsx tracker: Sheet1 from site-inventory.json (~480+ rows Active/Archival); "
             "Sheet3 status from qa-verdict-<label>.json gate verdicts."))

    # 9. handover — Phase 4: compile handover summary + Teams ping.
    P.append(dict(
        name="handover", where="server",
        cmd="python3 %s/cc_sp_handover.py --job %s --config %s" % (SRV_PROV, job, cfgPath),
        note="Phase 4: sp-handover-summary.json + Teams handover ping."))

    # 10. closeout — server-side; only reached if the gate passed.
    P.append(dict(
        name="closeout", where="server",
        cmd="python3 %s/cc_closeout.py --job %s" % (SRV_PROV, job),
        note="finalise the job (only after the gate PASSES and tracker is generated)."))

    return P


# stages whose scripts may not exist yet (parallel build) — never executed on --dry-run,
# and on a live run the driver checks for existence and flags if absent.
PARALLEL_STAGES = {"style": "cc-sp-styler-attach.py (T6)"}  # tracker moved after verify — fully sequenced now


def print_plan(cfg, plan):
    print("=" * 78)
    print("cc-sp-mirror DRY-RUN — ordered step plan")
    print("  job=%s  buildCap=%s  heavyWebpartCap=%s" % (cfg["job"], cfg["buildCap"], cfg["heavyWebpartCap"]))
    print("  sourceUrl  = %s" % cfg["sourceUrl"])
    print("  targetSite = %s" % cfg["targetSite"])
    print("  pages      = %s" % (cfg.get("pages") if cfg.get("pages") else "topNactive=%s" % cfg.get("topNactive")))
    print("  styler     = %s" % json.dumps(cfg.get("styler") or {}))
    print("  jobDir     = %s" % cfg["jobDir"])
    print("=" * 78)
    n = 0
    last = None
    for st in plan:
        if st["name"] != last:
            n += 1
            last = st["name"]
        flag = "  [PARALLEL: %s]" % PARALLEL_STAGES[st["name"]] if st["name"] in PARALLEL_STAGES else ""
        print("\n%2d. %-14s (%s)%s" % (n, st["name"], st["where"], flag))
        print("    # %s" % st["note"])
        print("    $ %s" % st["cmd"])
    print("\n" + "=" * 78)
    print("image-map completeness: image_migrate.py (article path) + sp_home_compose.py merge")
    print("  (homepage path) both write %s/image-map.json; gate consumes it via --image-map." % cfg["jobDir"])
    print("Mac-side stages: capture, verify (authed .mjs). Server-side: the rest (.py over SSH).")
    print("=" * 78)


def run_stage(st, server_mode=False):
    where = st["where"]
    cmd = st["cmd"]
    log("RUN (%s) %s" % (where, st["name"]))
    if server_mode:
        # All stages run locally on the server — no SSH wrapper needed.
        full = ["/bin/sh", "-c", cmd]
    elif where == "server":
        full = SSH + [cmd]
    else:
        full = ["/bin/sh", "-c", cmd]
    r = subprocess.run(full)
    if r.returncode != 0:
        raise SystemExit("[mirror] stage '%s' FAILED (exit %d) — aborting." % (st["name"], r.returncode))


def exists_server(path):
    r = subprocess.run(SSH + ["test -f %s && echo Y || echo N" % shlex.quote(path)],
                       capture_output=True, text=True)
    return r.stdout.strip() == "Y"


def live_run(cfg, plan, start=None, only=None, server_mode=False):
    jobDir = cfg["jobDir"]
    started = start is None

    def file_exists(path):
        if server_mode:
            return os.path.isfile(path)
        return exists_server(path)

    # In server mode, assert capture bundle exists before starting.
    if server_mode:
        bundle = "%s/capture/manifest.json" % jobDir
        if not os.path.isfile(bundle):
            raise SystemExit(
                "[mirror] capture bundle missing: %s\n"
                "Run verify-at-intake first to populate the capture bundle." % bundle)

    for st in plan:
        if only and st["name"] != only:
            continue
        if not started:
            if st["name"] == start:
                started = True
            else:
                continue
        # parallel-build scripts: skip + flag if absent rather than crash
        if st["name"] in PARALLEL_STAGES:
            script = st["cmd"].split()[1]  # the .py path
            if not file_exists(script):
                log("SKIP (%s): %s not present yet (parallel build) — FLAG for follow-up." %
                    (st["name"], PARALLEL_STAGES[st["name"]]))
                continue
        # before the gate, assert image-map.json is complete
        if st["name"] == "verify":
            imap = "%s/image-map.json" % jobDir
            if not file_exists(imap):
                raise SystemExit("[mirror] %s missing — both migration paths must populate it." % imap)
        run_stage(st, server_mode=server_mode)
    log("pipeline complete.")


def main():
    ap = argparse.ArgumentParser(prog="cc-sp-mirror")
    ap.add_argument("--config", required=True, help="path to job.config.json")
    ap.add_argument("--dry-run", action="store_true", help="print ordered plan; execute nothing")
    ap.add_argument("--from", dest="start", help="resume at this stage")
    ap.add_argument("--only", help="run a single stage")
    ap.add_argument("--server", action="store_true",
                    help="run on the server: all stages execute locally (no SSH); "
                         "capture stages skipped (bundle must already exist from verify-at-intake)")
    a = ap.parse_args()

    cfg = load_config(a.config)
    plan = build_plan(cfg, server_mode=a.server)

    if a.dry_run:
        print_plan(cfg, plan)
        return
    live_run(cfg, plan, start=a.start, only=a.only, server_mode=a.server)


if __name__ == "__main__":
    main()
