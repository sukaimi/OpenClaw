#!/usr/bin/env python3
"""cc-sp-restore — restore a built SharePoint page from a pre-overwrite backup
(JOB0024-108 backup-before-republish recovery; this SP has no version history).

Backups are written by canvas_compose._backup_page into
/srv/projects/<JOB>/backups/<page>.<ts>.json (newest wins) whenever the build runs
with CC_SP_BACKUP_DIR set.

Usage:
  cc_sp_restore.py <JOB> --list                       # list available backups
  cc_sp_restore.py <JOB> <page.aspx> [--at <ts>] [--site-path /sites/CCBuild-NNNN]
                                                      # re-apply the saved canvas
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, "/root/.openclaw/sp-provision")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas_compose import apply_page, SITE_HOST  # noqa: E402
from spclient import SP  # noqa: E402

PROJECTS = "/srv/projects"


def _strip_odata(o):
    """Recursively drop '*@odata.*' annotation keys (e.g. 'horizontalSections@odata.context')
    that a $expand GET adds — Graph rejects them on a re-POST of canvasLayout."""
    if isinstance(o, dict):
        return {k: _strip_odata(v) for k, v in o.items() if "@odata" not in k}
    if isinstance(o, list):
        return [_strip_odata(x) for x in o]
    return o


def _backups_dir(job):
    return os.path.join(PROJECTS, job, "backups")


def cmd_list(job):
    d = _backups_dir(job)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    if not files:
        print("no backups under", d)
        return
    by_page = {}
    for f in files:
        b = os.path.basename(f)
        page = b.rsplit(".", 2)[0]  # <page>.<ts>.json -> <page>
        by_page.setdefault(page, []).append(b)
    for page in sorted(by_page):
        print("%s  (%d backup(s))" % (page, len(by_page[page])))
        for b in sorted(by_page[page]):
            print("   ", b)


def _pick_backup(job, page, at):
    d = _backups_dir(job)
    cands = sorted(glob.glob(os.path.join(d, "%s.*.json" % page)))
    if not cands:
        sys.exit("no backup for %s under %s" % (page, d))
    if at:
        match = [c for c in cands if at in os.path.basename(c)]
        if not match:
            sys.exit("no backup for %s at %s" % (page, at))
        return match[-1]
    return cands[-1]  # newest


def _site_path(job, arg_site_path):
    if arg_site_path:
        return arg_site_path
    sj = os.path.join(PROJECTS, job, "site.json")
    if os.path.isfile(sj):
        try:
            s = json.load(open(sj))
            sp = s.get("sitePath") or s.get("site_path")
            if sp:
                return sp
            url = s.get("url") or s.get("siteUrl") or ""
            if "/sites/" in url:
                return "/sites/" + url.rstrip("/").split("/sites/")[-1]
        except Exception:
            pass
    sys.exit("need --site-path (no resolvable site.json under %s)" % os.path.join(PROJECTS, job))


def cmd_restore(job, page, at, arg_site_path):
    bpath = _pick_backup(job, page, at)
    bak = json.load(open(bpath))
    canvas = _strip_odata(bak.get("canvasLayout"))
    if not canvas:
        sys.exit("backup %s has no canvasLayout — cannot restore" % bpath)
    site_path = _site_path(job, arg_site_path)
    sp = SP(site_host=SITE_HOST, site_path=site_path)
    sid = bak.get("sid") or sp.site_id()
    print("restoring %s from %s (saved %s) into %s ..." % (page, os.path.basename(bpath), bak.get("savedAt"), site_path))
    # re-apply the saved canvas (apply_page deletes+recreates; if CC_SP_BACKUP_DIR is
    # set it will also snapshot the current state first — chained restore is safe).
    created, api = apply_page(sp, sid, page, bak.get("title") or page, canvas,
                              publish=True, replace=True)
    print("RESTORED %s -> page id %s (%s)" % (page, created.get("id"), api))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("page", nargs="?")
    ap.add_argument("--at", help="timestamp substring to pick a specific backup")
    ap.add_argument("--site-path")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.page:
        cmd_list(a.job)
        return
    cmd_restore(a.job, a.page, a.at, a.site_path)


if __name__ == "__main__":
    main()
