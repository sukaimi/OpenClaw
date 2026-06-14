#!/usr/bin/env python3
"""cc-sp-triage — large-site guardrails: classify a captured site's pages into a
SCOPE SHEET the operator signs off before any page is built (JOB0024-108).

Reads site-inventory.json (from cc-sp-capture --inventory-out; enriched with
bytes/webPartCount/isPublishing/hasListWebpart) and applies config-driven
heuristics:

  keep      = modified within `triageKeepMonths` AND not a system/template page
  buildable = lib=='Site Pages' AND webPartCount<=heavyWebpartCap
              AND not hasListWebpart AND not isPublishing
              (else FLAGGED with a reason — flag-don't-fake; rebuilding flagged
               page types is the separate content-type-coverage work, JOB0024-109)

Emits scope-sheet.json (machine) + scope-sheet.csv (operator review).

Usage:
  cc_sp_triage.py <jobDir|inventory.json> [--config job.config.json]
                  [--keep-months N] [--heavy-cap N] [--out-dir DIR]
  cc_sp_triage.py <jobDir> --approve [--all-buildable]   # writes scope-approved.json (B1)
  cc_sp_triage.py <jobDir> --worklist [--wave-size N]     # writes worklist.json (C1)
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_KEEP_MONTHS = 18
DEFAULT_HEAVY_CAP = 6
# pages that are scaffolding/system, never client content
SYSTEM_PAGES = {"home.aspx", "default.aspx"}  # home is handled specially by the builder

# flag-don't-fake: a flagged page type may only flip flag->buildable when an actual
# build handler exists for it AND the operator whitelists it via `buildableTypes`
# (job.config "buildableTypes" or --buildable-types). HANDLED_TYPES maps the short
# flag key (the first token of flagReason) to the content-type-coverage handler that
# can rebuild it. As each coverage sub-task lands, register its key here.
#   "publishing" -> sp-audit._publishing_blocks (pub-field extraction, JOB0024-109/1)
#   "list"       -> sp-audit._listview_blocks (static list-view snapshot, JOB0024-109/2)
#   "tiles"      -> canvas_compose tiles_from_blocks -> quicklinks_wp (JOB0024-109/3)
#   "banner"     -> canvas_compose banner_from_blocks -> hero_wp (JOB0024-109/3)
# CAROUSEL is deliberately ABSENT: its native modern equivalent needs an SPFx web
# part whose source is missing + toolchain broken, so it STAYS flagged (carousel-spfx)
# — flag-don't-fake. Never add "carousel" here without a real SPFx authoring path.
HANDLED_TYPES = {"publishing", "list", "tiles", "banner"}
# flagReason short-key for a flagReason (must match classify() below). The
# list-driven flag maps to the human key 'list' so the downgrade whitelist reads
# buildableTypes:["list"]. tiles/banner map to their family keys; carousel-spfx maps
# to itself (NOT in HANDLED_TYPES) so it can never be whitelisted into buildable.
_FLAG_KEYS = {"publishing-layout": "publishing", "list-driven": "list",
              "hometiles": "tiles", "banner": "banner", "carousel-spfx": "carousel"}


def _load_cfg(cfg_path):
    if cfg_path and os.path.isfile(cfg_path):
        try:
            return json.load(open(cfg_path))
        except Exception:
            pass
    return {}


def _resolve_inventory(target):
    """Accept a jobDir (look for site-inventory.json) or a direct json path."""
    if os.path.isdir(target):
        for cand in (os.path.join(target, "site-inventory.json"),
                     os.path.join(target, "capture", "site-inventory.json")):
            if os.path.isfile(cand):
                return cand, target
        sys.exit("no site-inventory.json under %s" % target)
    if os.path.isfile(target):
        return target, os.path.dirname(target) or "."
    sys.exit("not found: %s" % target)


def _months_since(iso, now):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (now - d).days / 30.0
    except Exception:
        return None


def _flag_key(flag):
    """Short stable key for a flagReason (first token), e.g.
    'heavy-media (7 web parts > cap 6)' -> 'heavy-media'. Maps known full reasons
    via _FLAG_KEYS so the downgrade whitelist can use a human key ('publishing')."""
    if not flag:
        return None
    head = flag.split(" ")[0]
    return _FLAG_KEYS.get(head, head)


def classify(inv, keep_months, heavy_cap, now, buildable_types=None):
    """Classify pages into a scope sheet. `buildable_types` is the operator's
    whitelist of flagged content-types to TREAT as buildable (config
    `buildableTypes` / --buildable-types). A flagged type only flips
    flag->buildable when it's whitelisted AND a handler exists in HANDLED_TYPES
    (flag-don't-fake); the per-page gate still applies downstream."""
    whitelist = set(buildable_types or [])
    rows = []
    for p in inv:
        f = (p.get("file") or "").lower()
        age = _months_since(p.get("modified"), now)
        is_system = f in SYSTEM_PAGES
        keep = (age is None or age <= keep_months) and not is_system
        wp = int(p.get("webPartCount") or 0)
        is_pub = bool(p.get("isPublishing"))
        is_list = bool(p.get("hasListWebpart"))
        # tiles/carousel are list-family pages with DISTINCT routing (JOB0024-109/3):
        # HomeTiles/banner have native modern handlers; Carousel is SPFx-blocked. They
        # are checked BEFORE the generic list flag so they get their specific reason.
        has_tiles = bool(p.get("hasTiles"))
        has_carousel = bool(p.get("hasCarousel"))
        is_banner = bool(p.get("hasBanner"))
        flag = None
        if is_pub:
            flag = "publishing-layout"
        elif has_carousel:
            # SPFx-blocked: no native modern equivalent we can author here. STAYS
            # flagged (carousel maps to 'carousel' which is NOT in HANDLED_TYPES, so
            # even buildableTypes=['carousel'] cannot flip it).
            flag = "carousel-spfx"
        elif has_tiles:
            flag = "hometiles"
        elif is_banner:
            flag = "banner"
        elif is_list:
            flag = "list-driven"
        elif (p.get("lib") or "") != "Site Pages":
            flag = "non-sitepages-lib"
        elif wp > heavy_cap:
            flag = "heavy-media (%d web parts > cap %d)" % (wp, heavy_cap)
        # flag->buildable downgrade: only when the operator whitelisted this type
        # AND we actually have a handler that can rebuild it.
        fkey = _flag_key(flag)
        if flag and fkey in whitelist and fkey in HANDLED_TYPES:
            flag = None
        buildable = keep and flag is None
        rows.append({
            "file": p.get("file"), "title": p.get("title"), "lib": p.get("lib"),
            "modified": p.get("modified"), "ageMonths": round(age, 1) if age is not None else None,
            "bytes": p.get("bytes"), "webPartCount": wp,
            "isPublishing": is_pub, "hasListWebpart": is_list,
            "hasTiles": has_tiles, "hasCarousel": has_carousel,
            "keep": keep, "buildable": buildable, "flagReason": flag,
        })
    return rows


def write_outputs(rows, out_dir):
    jp = os.path.join(out_dir, "scope-sheet.json")
    json.dump(rows, open(jp, "w"), indent=1)
    cp = os.path.join(out_dir, "scope-sheet.csv")
    with open(cp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "title", "lib", "modified", "ageMonths", "bytes",
                    "webPartCount", "keep", "buildable", "flagReason"])
        for r in rows:
            w.writerow([r["file"], r["title"], r["lib"], r["modified"], r["ageMonths"],
                        r["bytes"], r["webPartCount"], r["keep"], r["buildable"], r["flagReason"] or ""])
    return jp, cp


def summary(rows):
    keep = sum(1 for r in rows if r["keep"])
    build = sum(1 for r in rows if r["buildable"])
    flagged = sum(1 for r in rows if r["keep"] and r["flagReason"])
    archive = len(rows) - keep
    reasons = {}
    for r in rows:
        if r["keep"] and r["flagReason"]:
            k = r["flagReason"].split(" ")[0]
            reasons[k] = reasons.get(k, 0) + 1
    print("TRIAGE: %d pages | keep %d / archive %d | buildable %d / flagged %d"
          % (len(rows), keep, archive, build, flagged))
    if reasons:
        print("  flag reasons:", ", ".join("%s=%d" % (k, v) for k, v in sorted(reasons.items())))


def cmd_approve(out_dir, rows, all_buildable):
    approved = [r["file"] for r in rows if r["buildable"]] if all_buildable else []
    ap = os.path.join(out_dir, "scope-approved.json")
    json.dump({"approvedFiles": approved, "approvedAt": None,
               "by": "auto-all-buildable" if all_buildable else "pending-operator"},
              open(ap, "w"), indent=1)
    print("scope-approved.json written (%d approved%s)"
          % (len(approved), "" if all_buildable else " — EMPTY, operator must approve"))


def cmd_worklist(out_dir, rows, wave_size):
    approved_path = os.path.join(out_dir, "scope-approved.json")
    approved = set()
    if os.path.isfile(approved_path):
        approved = set(json.load(open(approved_path)).get("approvedFiles", []))
    pages = [{"file": r["file"], "status": "pending", "wave": None}
             for r in rows if r["buildable"] and (not approved or r["file"] in approved)]
    wl = {"job": os.path.basename(out_dir.rstrip("/")), "waveSize": wave_size, "pages": pages}
    wp = os.path.join(out_dir, "worklist.json")
    json.dump(wl, open(wp, "w"), indent=1)
    print("worklist.json written (%d pages, waveSize %d%s)"
          % (len(pages), wave_size, "" if approved else " — NO approval file, used all buildable"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="jobDir or site-inventory.json")
    ap.add_argument("--config")
    ap.add_argument("--keep-months", type=int)
    ap.add_argument("--heavy-cap", type=int)
    ap.add_argument("--buildable-types",
                    help="comma-separated flagged types to treat as buildable "
                         "(e.g. 'publishing'); only flips when a handler exists")
    ap.add_argument("--out-dir")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--all-buildable", action="store_true")
    ap.add_argument("--worklist", action="store_true")
    ap.add_argument("--wave-size", type=int, default=10)
    a = ap.parse_args()

    inv_path, job_dir = _resolve_inventory(a.target)
    out_dir = a.out_dir or job_dir
    cfg = _load_cfg(a.config)
    keep_months = a.keep_months or cfg.get("triageKeepMonths") or DEFAULT_KEEP_MONTHS
    heavy_cap = a.heavy_cap or cfg.get("heavyWebpartCap") or DEFAULT_HEAVY_CAP
    # buildableTypes: CLI overrides config; config default []. Normalize to a list.
    if a.buildable_types is not None:
        buildable_types = [t.strip() for t in a.buildable_types.split(",") if t.strip()]
    else:
        buildable_types = cfg.get("buildableTypes") or []
    now = datetime.now(timezone.utc)

    inv = json.load(open(inv_path))
    rows = classify(inv, keep_months, heavy_cap, now, buildable_types)

    if a.approve:
        cmd_approve(out_dir, rows, a.all_buildable)
        return
    if a.worklist:
        cmd_worklist(out_dir, rows, a.wave_size)
        return

    jp, cp = write_outputs(rows, out_dir)
    print("scope sheet -> %s , %s" % (jp, cp))
    print("  (keepMonths=%d, heavyCap=%d, buildableTypes=%s)"
          % (keep_months, heavy_cap, buildable_types or "[]"))
    summary(rows)


if __name__ == "__main__":
    main()
