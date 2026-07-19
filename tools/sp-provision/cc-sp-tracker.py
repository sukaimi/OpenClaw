#!/usr/bin/env python3
"""cc-sp-tracker.py — config-driven Content Tracker (.xlsx) for the Code&Craft SP pipeline.

Usage:
    cc-sp-tracker.py --config <jobDir>/job.config.json

Produces <jobDir>/<JOB>-content-tracker.xlsx  (3 sheets, FARA-style):
  1. Page Inventory   — every source page classified Active vs Archival
  2. Content Elements — per-page rendered content (images/links/text/web parts)
  3. Classic→Modern   — each source element → modern build target

Inputs read from jobDir:
  - capture/manifest.json      (required — captured pages + images)
  - home-manifest.json         (optional — homepage images/links)
  - image-map.json             (optional — src→dst URL rewriting map)
  - sp-expect.json             (optional — build plan pages; enriches Sheet 3)
  - site-inventory.json        (optional — full site page list; enriches Sheet 1)
  - <jobDir>/*-manifest.json   (optional — additional page manifests)

Idempotent. Exits nonzero on failure.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("cc-sp-tracker")

# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------
PURPLE = "5C2D91"
LIGHT  = "EDE7F4"
GREY   = "F3F2F1"
BUILT_FILL = LIGHT
PENDING_FILL = "FFF4E5"

hdr_font  = Font(bold=True, color="FFFFFF", size=11)
hdr_fill  = PatternFill("solid", fgColor=PURPLE)
title_font = Font(bold=True, size=15, color=PURPLE)
sub_font  = Font(italic=True, size=10, color="666666")
thin      = Side(style="thin", color="D0CCE0")
border    = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap      = Alignment(vertical="top", wrap_text=True)
center    = Alignment(vertical="center", wrap_text=True)


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = center
        cell.border = border


def set_widths(ws, col_widths):
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def apply_border_wrap(ws, row, ncols):
    for c in range(1, ncols + 1):
        ws.cell(row=row, column=c).border = border
        ws.cell(row=row, column=c).alignment = wrap


def apply_row_fill(ws, row, ncols, fgColor):
    for c in range(1, ncols + 1):
        ws.cell(row=row, column=c).fill = PatternFill("solid", fgColor=fgColor)


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        cfg = json.load(f)
    job_dir = cfg.get("jobDir") or str(Path(config_path).parent)
    cfg["jobDir"] = job_dir
    cfg.setdefault("job", Path(job_dir).name)
    cfg.setdefault("sourceUrl", "")
    cfg.setdefault("targetSite", "")
    cfg.setdefault("buildCap", 999)
    cfg.setdefault("activeThreshold", "2024")   # pages modified >= this year = Active
    return cfg


def jload(path, default=None):
    """Load JSON if file exists, else return default."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        log.debug("optional file not found: %s", path)
        return default
    except json.JSONDecodeError as e:
        log.warning("JSON parse error in %s: %s", path, e)
        return default


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_job_data(cfg: dict) -> dict:
    job_dir = cfg["jobDir"]

    # Required
    cap_manifest_path = os.path.join(job_dir, "capture", "manifest.json")
    cap = jload(cap_manifest_path, {})
    if not cap:
        log.warning("capture/manifest.json not found or empty at %s — Sheet 1 will be sparse", cap_manifest_path)

    # Optional extras
    home_manifest = jload(os.path.join(job_dir, "home-manifest.json"), {})
    image_map     = jload(os.path.join(job_dir, "image-map.json"), {})
    sp_expect     = jload(os.path.join(job_dir, "sp-expect.json"), {})
    site_inv      = jload(os.path.join(job_dir, "site-inventory.json"), None)   # full 500+ page list
    sp_scored     = jload(os.path.join(job_dir, "sp-scored.json"), None)        # Phase 1 scoring output

    # Additional capture dirs (cap5, cap3, …)
    extra_caps = []
    for entry in sorted(os.scandir(job_dir), key=lambda e: e.name):
        if entry.is_dir() and entry.name.startswith("cap") and entry.name != "capture":
            m = jload(os.path.join(entry.path, "manifest.json"), {})
            if m:
                log.info("found extra capture dir: %s (%d pages)", entry.name, len(m.get("pages", [])))
                extra_caps.append(m)

    # Gate verdict files: qa-verdict-<label>.json (one per gated page).
    # Label = "home" for Home.aspx / Default.aspx; else page stem (filename minus .aspx).
    verdicts = {}
    for entry in os.scandir(job_dir):
        if entry.name.startswith("qa-verdict-") and entry.name.endswith(".json"):
            label = entry.name[len("qa-verdict-"):-len(".json")]
            v = jload(entry.path, None)
            if v is not None:
                verdicts[label] = v
    if verdicts:
        log.info("Loaded %d gate verdict(s): %s", len(verdicts), sorted(verdicts.keys()))

    return dict(
        cap=cap,
        home_manifest=home_manifest,
        image_map=image_map,
        sp_expect=sp_expect,
        site_inv=site_inv,
        sp_scored=sp_scored,
        extra_caps=extra_caps,
        verdicts=verdicts,
    )


# ---------------------------------------------------------------------------
# Verdict helpers
# ---------------------------------------------------------------------------

def verdict_label(srcfile: str) -> str:
    """Map a page filename to its gate verdict label — mirrors manifest_stem() in cc-sp-mirror.py.
    Home.aspx / Default.aspx -> 'home'; otherwise strip trailing .aspx."""
    name = srcfile or ""
    if name.lower() in ("home.aspx", "default.aspx"):
        return "home"
    return name[:-5] if name.lower().endswith(".aspx") else name


def verdict_status(label: str, verdicts: dict) -> str | None:
    """Return the gate-driven status string for a page, or None if no verdict exists."""
    v = verdicts.get(label)
    if v is None:
        return None
    if v.get("pass"):
        return "Built — gate PASS"
    missing = v.get("missing", [])
    n = len(missing) if isinstance(missing, list) else missing
    return f"INCOMPLETE — gate FAIL ({n} missing)"


# ---------------------------------------------------------------------------
# Build set resolution (Sheet 3 source)
# ---------------------------------------------------------------------------

def resolve_build_set(cfg: dict, data: dict) -> list:
    """Return list of dicts: title, src, srcfile, dst, page_type, approach, status."""
    source_url  = cfg["sourceUrl"]
    target_site = cfg["targetSite"]
    build_cap   = int(cfg.get("buildCap", 999))
    sp_expect   = data["sp_expect"]
    cap         = data["cap"]
    extra_caps  = data["extra_caps"]
    verdicts    = data.get("verdicts", {})

    # Collect all captured pages
    all_pages = list(cap.get("pages", []))
    for ec in extra_caps:
        all_pages.extend(ec.get("pages", []))

    # If sp-expect has pages, use those as the canonical build list (richer)
    expect_pages = sp_expect.get("pages", [])
    if expect_pages:
        build = []
        for p in expect_pages[:build_cap]:
            name   = p.get("name", "")
            title  = p.get("title", name)
            # Infer type from webparts in sp-expect
            wps    = [w.get("type", "") for w in p.get("webparts", [])]
            if any("image" in w.lower() for w in wps):
                ptype = "Article (text/media)"
            elif len(wps) == 0:
                ptype = "Article (text)"
            else:
                ptype = "Article (text)"
            approach = "OOTB native (sectioned canvas)"
            vlabel   = verdict_label(name)
            status   = verdict_status(vlabel, verdicts) or p.get("status", "In scope")
            dst_name = name.replace(".aspx", "") + ".aspx"
            build.append({
                "title":    title,
                "src":      source_url + "/Pages/" + name if source_url else name,
                "srcfile":  name,
                "dst":      target_site + "/SitePages/" + dst_name if target_site else dst_name,
                "type":     ptype,
                "approach": approach,
                "status":   status,
            })
        # Also add homepage if home-manifest exists and not already in list
        home_m = data["home_manifest"]
        if home_m and not any(b["srcfile"] in ("Default.aspx", "Home.aspx") for b in build):
            home_vstatus = verdict_status("home", verdicts) or "Built"
            build.insert(0, {
                "title":    home_m.get("title", "Site Home"),
                "src":      source_url,
                "srcfile":  "Default.aspx",
                "dst":      target_site + "/SitePages/Home.aspx" if target_site else "Home.aspx",
                "type":     "List-driven homepage",
                "approach": "OOTB (Hero/Image/QuickLinks) + SPFx styler",
                "status":   home_vstatus,
            })
        return build

    # Fallback: build from captured pages
    build = []
    if data["home_manifest"]:
        home_vstatus = verdict_status("home", verdicts) or "In scope"
        build.append({
            "title":    data["home_manifest"].get("title", "Site Home"),
            "src":      source_url,
            "srcfile":  "Default.aspx",
            "dst":      target_site + "/SitePages/Home.aspx" if target_site else "Home.aspx",
            "type":     "List-driven homepage",
            "approach": "OOTB (Hero/Image/QuickLinks) + SPFx styler",
            "status":   home_vstatus,
        })
    for p in all_pages[:build_cap]:
        name  = p.get("name", "")
        title = p.get("title", name)
        vlabel = verdict_label(name)
        vstatus = verdict_status(vlabel, verdicts) or "In scope"
        build.append({
            "title":    title,
            "src":      source_url + "/Pages/" + name if source_url else name,
            "srcfile":  name,
            "dst":      target_site + "/SitePages/" + name if target_site else name,
            "type":     "Article (text)",
            "approach": "OOTB native (sectioned canvas)",
            "status":   vstatus,
        })
    return build


# ---------------------------------------------------------------------------
# Sheet 1: Page Inventory
# ---------------------------------------------------------------------------

def build_sheet1(wb, cfg: dict, data: dict, build_set: list):
    source_url     = cfg["sourceUrl"]
    active_thresh  = cfg.get("activeThreshold", "2024")
    site_inv       = data["site_inv"]
    cap            = data["cap"]
    extra_caps     = data["extra_caps"]
    sp_scored      = data.get("sp_scored")
    job            = cfg["job"]

    build_files = {b["srcfile"].lower() for b in build_set}

    # Build scored lookup: filename (lower) -> scored entry
    scored_map = {}
    if sp_scored:
        for s in sp_scored.get("scored", []):
            scored_map[s["name"].lower()] = s

    # Use site inventory if present (full 500+ page Graph audit),
    # otherwise fall back to captured pages only.
    if site_inv:
        inv = site_inv if isinstance(site_inv, list) else site_inv.get("pages", [])
        total_label = f"Total pages: {len(inv)}"
    else:
        # Build a synthetic inventory from all captured pages
        inv = []
        all_pages = list(cap.get("pages", []))
        for ec in extra_caps:
            all_pages.extend(ec.get("pages", []))
        for p in all_pages:
            inv.append({
                "title":    p.get("title", p.get("name", "")),
                "file":     p.get("name", ""),
                "modified": p.get("modified", ""),
                "created":  p.get("created", ""),
            })
        total_label = f"Pages captured: {len(inv)}"
        log.info("No site-inventory.json — Sheet 1 built from %d captured pages", len(inv))

    active = [x for x in inv if (x.get("modified") or "")[:4] >= active_thresh]
    archival = [x for x in inv if (x.get("modified") or "")[:4] < active_thresh]

    ws = wb.active
    ws.title = "1. Page Inventory"
    ws["A1"] = f"{job} Classic Site — Page Inventory (Audit)"
    ws["A1"].font = title_font
    ws["A2"] = (
        f"Source: {source_url}  |  {total_label}  |  "
        f"Active (modified {active_thresh}+): {len(active)}  |  "
        f"Archival (pre-{active_thresh}): {len(archival)}  |  "
        f"In build scope: {len(build_set)}"
    )
    ws["A2"].font = sub_font

    has_scores = bool(scored_map)
    if has_scores:
        cols = ["#", "Page Title", "File Name", "Library", "Last Modified", "Created", "Status", "Tier", "Priority Score", "Complexity", "In Build Set"]
    else:
        cols = ["#", "Page Title", "File Name", "Library", "Last Modified", "Created", "Status", "In Build Set"]
    ws.append([])
    ws.append(cols)
    style_header(ws, 4, len(cols))

    if has_scores:
        # Sort by Tier ASC, then Priority Score DESC; unscored pages go last
        def sort_key(r):
            nm = (r.get("file") or r.get("name") or "").lower()
            s = scored_map.get(nm)
            return (s["tier"] if s else 99, -(s["priority_score"] if s else 0))
        sorted_inv = sorted(inv, key=sort_key)
    else:
        sorted_inv = sorted(inv, key=lambda r: r.get("modified") or "", reverse=True)

    for i, x in enumerate(sorted_inv, 1):
        yr     = (x.get("modified") or "")[:4]
        status = "Active" if yr >= active_thresh else ("Archival" if yr else "Unknown")
        nm_key = (x.get("file") or x.get("name") or "").lower()
        inset  = "YES" if nm_key in build_files else ""
        s = scored_map.get(nm_key) if has_scores else None
        if has_scores:
            ws.append([
                i,
                x.get("title") or "(untitled)",
                x.get("file") or x.get("name") or "",
                x.get("lib") or x.get("library") or "Pages",
                (x.get("modified") or "")[:10],
                (x.get("created")  or "")[:10],
                status,
                ("T%d" % s["tier"]) if s else "",
                s["priority_score"] if s else "",
                "Yes" if (s and s.get("complexity_flag")) else "",
                inset,
            ])
        else:
            ws.append([
                i,
                x.get("title") or "(untitled)",
                x.get("file") or x.get("name") or "",
                x.get("lib") or x.get("library") or "Pages",
                (x.get("modified") or "")[:10],
                (x.get("created")  or "")[:10],
                status,
                inset,
            ])
        r = ws.max_row
        apply_border_wrap(ws, r, len(cols))
        if inset:
            apply_row_fill(ws, r, len(cols), LIGHT)

    if has_scores:
        set_widths(ws, [5, 44, 36, 9, 14, 12, 10, 6, 14, 11, 11])
    else:
        set_widths(ws, [5, 52, 42, 9, 14, 12, 10, 11])
    ws.freeze_panes = "A5"
    log.info("Sheet 1: %d inventory rows (%d active, %d archival)", len(inv), len(active), len(archival))


# ---------------------------------------------------------------------------
# Sheet 2: Content Elements
# ---------------------------------------------------------------------------

def build_sheet2(wb, cfg: dict, data: dict, build_set: list):
    source_url = cfg["sourceUrl"]
    home_m     = data["home_manifest"]
    cap        = data["cap"]
    extra_caps = data["extra_caps"]
    image_map  = data["image_map"]

    ws = wb.create_sheet("2. Content Elements")
    ws["A1"] = "Content Elements — per page (rendered inventory)"
    ws["A1"].font = title_font
    ws["A2"] = "Complete rendered manifest (images incl. CSS backgrounds, links, content blocks) driving build + verification."
    ws["A2"].font = sub_font

    cols = ["Page", "Element Type", "Detail / Text", "URL / Source", "Notes"]
    ws.append([])
    ws.append(cols)
    style_header(ws, 4, len(cols))

    def add_row(page, etype, detail, url, notes=""):
        ws.append([page, etype, (detail or "")[:90], (url or "")[:80], notes])
        r = ws.max_row
        apply_border_wrap(ws, r, len(cols))

    # Homepage elements from home-manifest
    if home_m:
        page_label = home_m.get("title") or "Site Home"
        for im in home_m.get("images", []):
            note = ("link→ " + im["link"]) if im.get("link") else ""
            add_row(page_label, "Image", im.get("alt") or "(image)", im.get("src"), note)
        for lk in home_m.get("links", [])[:30]:
            add_row(page_label, "Link", lk.get("text") or "", lk.get("href") or lk.get("url") or "", "")
        for tx in home_m.get("text", [])[:10]:
            add_row(page_label, "Text block", (tx if isinstance(tx, str) else tx.get("text", ""))[:90], "", "")

    # Article pages from each capture manifest
    all_manifests = [cap] + extra_caps
    for m in all_manifests:
        src_url = m.get("sourceUrl") or source_url
        for pg in m.get("pages", []):
            pg_name  = pg.get("title") or pg.get("name") or "(page)"
            pg_bytes = pg.get("bytes", "?")
            pg_file  = pg.get("name", "")
            add_row(
                pg_name, "Page (article)",
                f"{pg_bytes} bytes body HTML",
                (src_url + "/Pages/" + pg_file) if src_url else pg_file,
                f"lib: {pg.get('lib', 'Pages')}",
            )
        for im in m.get("images", []):
            src = im if isinstance(im, str) else (im.get("src") or im.get("url") or "")
            pg_name = im.get("page", "(article images)") if isinstance(im, dict) else "(article images)"
            add_row(pg_name, "Image", im.get("alt", "") if isinstance(im, dict) else "", src, "")

    # Image map entries (migrated assets)
    if image_map:
        entries = [(k, v) for k, v in image_map.items() if not k.startswith("_")]
        for old_src, new_src in entries:
            add_row("(migrated assets)", "Image (mapped)", "", old_src,
                    f"→ {str(new_src)[:60]}")

    set_widths(ws, [40, 16, 48, 50, 26])
    ws.freeze_panes = "A5"
    log.info("Sheet 2: %d content rows", ws.max_row - 4)


# ---------------------------------------------------------------------------
# Sheet 3: Classic → Modern Mapping
# ---------------------------------------------------------------------------

def build_sheet3(wb, cfg: dict, data: dict, build_set: list):
    image_map = data["image_map"]
    job       = cfg["job"]
    n_pages   = len(build_set)

    ws = wb.create_sheet("3. Classic → Modern")
    ws["A1"] = f"Classic → Modern — Build Mapping ({job}: {n_pages} pages)"
    ws["A1"].font = title_font
    ws["A2"] = "Per-page: classic source → new modern URL, build approach (OOTB vs custom SPFx), and status."
    ws["A2"].font = sub_font

    cols = ["#", "Page Title", "Classic Source URL", "Modern Built URL", "Page Type", "Build Approach", "Status"]
    ws.append([])
    ws.append(cols)
    style_header(ws, 4, len(cols))

    for i, b in enumerate(build_set, 1):
        status = b.get("status", "In scope")
        ws.append([i, b["title"], b["src"], b["dst"], b["type"], b["approach"], status])
        r = ws.max_row
        apply_border_wrap(ws, r, len(cols))
        fill = BUILT_FILL if "built" in status.lower() else PENDING_FILL
        apply_row_fill(ws, r, len(cols), fill)

    # Image mapping section (separator + entries)
    if image_map:
        entries = [(k, v) for k, v in image_map.items() if not k.startswith("_")]
        if entries:
            ws.append([])  # blank separator
            r = ws.max_row
            ws.cell(r, 1).value = "— Image URL Map —"
            ws.cell(r, 1).font  = Font(bold=True, color=PURPLE)

            img_cols = ["#", "Classic Image URL", "Modern Image URL", "Notes", "", "", ""]
            ws.append(img_cols)
            r = ws.max_row
            apply_border_wrap(ws, r, len(cols))
            ws.cell(r, 1).font = Font(bold=True, color="FFFFFF")
            ws.cell(r, 1).fill = PatternFill("solid", fgColor=PURPLE)
            ws.cell(r, 2).font = Font(bold=True, color="FFFFFF")
            ws.cell(r, 2).fill = PatternFill("solid", fgColor=PURPLE)
            ws.cell(r, 3).font = Font(bold=True, color="FFFFFF")
            ws.cell(r, 3).fill = PatternFill("solid", fgColor=PURPLE)

            for j, (old_src, new_src) in enumerate(entries, 1):
                ws.append([j, old_src, str(new_src), "", "", "", ""])
                r = ws.max_row
                apply_border_wrap(ws, r, 3)

        log.info("Sheet 3: %d build-set rows + %d image-map entries", n_pages, len(entries))
    else:
        log.info("Sheet 3: %d build-set rows (no image-map.json)", n_pages)

    set_widths(ws, [5, 38, 46, 46, 20, 40, 26])
    ws.freeze_panes = "A5"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate FARA-style Content Tracker xlsx for an SP pipeline job.")
    parser.add_argument("--config", required=True, help="Path to job.config.json")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        log.error("Config not found: %s", args.config)
        sys.exit(1)

    cfg  = load_config(args.config)
    job  = cfg["job"]
    job_dir = cfg["jobDir"]
    log.info("Generating tracker for %s  jobDir=%s", job, job_dir)

    data = load_job_data(cfg)

    build_set = resolve_build_set(cfg, data)
    log.info("Build set: %d pages", len(build_set))

    wb = Workbook()
    build_sheet1(wb, cfg, data, build_set)
    build_sheet2(wb, cfg, data, build_set)
    build_sheet3(wb, cfg, data, build_set)

    out_path = os.path.join(job_dir, f"{job}-content-tracker.xlsx")
    wb.save(out_path)
    log.info("Saved: %s", out_path)

    # Summary to stdout for pipeline consumption
    ws1 = wb["1. Page Inventory"]
    ws2 = wb["2. Content Elements"]
    ws3 = wb["3. Classic → Modern"]
    print(f"Tracker: {out_path}")
    print(f"Sheet1 inventory rows: {ws1.max_row - 4}")
    print(f"Sheet2 content rows:   {ws2.max_row - 4}")
    print(f"Sheet3 mapping rows:   {ws3.max_row - 4}")


if __name__ == "__main__":
    main()
