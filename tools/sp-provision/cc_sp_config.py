#!/usr/bin/env python3
"""cc-sp-config <JOB####> — derive job.config.json for the cc-sp-mirror pipeline from
the existing job artifacts (brief.json + site.json [+ sp-expect.json]).

Run AFTER the Content-Audit stage (sp-expect.json present) so per-page gating gets the
real page names; falls back to topNactive (brief page count) if the audit hasn't run.
Writes /srv/projects/<JOB>/job.config.json. Idempotent. No hardcoded per-site values.
"""
import json
import os
import sys

PROJ = "/srv/projects"


def main():
    if len(sys.argv) < 2:
        print("usage: cc-sp-config <JOB####>")
        sys.exit(2)
    job = sys.argv[1]
    jobdir = os.path.join(PROJ, job)
    brief = json.load(open(os.path.join(jobdir, "brief.json")))
    site = json.load(open(os.path.join(jobdir, "site.json")))

    source = brief.get("sourceSiteUrl") or brief.get("source") or ""
    target = (site.get("siteUrl") or "").rstrip("/")
    if not source or not target:
        print("FAIL: need brief.sourceSiteUrl + site.siteUrl (source=%r target=%r)"
              % (source, target))
        sys.exit(1)

    cfg = {
        "job": job,
        "sourceUrl": source,
        "targetSite": target,
        "buildCap": 5,
        "heavyWebpartCap": 6,
        "styler": {
            "wallpaperUrl": (brief.get("styler") or {}).get("wallpaperUrl"),
            "brandColor": (brief.get("styler") or {}).get("brandColor"),
        },
        "jobDir": jobdir,
    }

    # Page selection: prefer real names from the audit (sp-expect.json) for per-page
    # gating; else fall back to topNactive from the brief's page count.
    exp_path = os.path.join(jobdir, "sp-expect.json")
    if os.path.exists(exp_path):
        names = [p.get("name") for p in json.load(open(exp_path)).get("pages", [])
                 if p.get("name")]
        if names:
            cfg["pages"] = names
    if "pages" not in cfg:
        try:
            cfg["topNactive"] = int(brief.get("pages") or 5)
        except (TypeError, ValueError):
            cfg["topNactive"] = 5

    out = os.path.join(jobdir, "job.config.json")
    with open(out, "w") as f:
        json.dump(cfg, f, indent=2)
    sel = ("pages=%d" % len(cfg["pages"])) if "pages" in cfg else ("topNactive=%d" % cfg["topNactive"])
    print("wrote %s  (source=%s target=%s %s)" % (out, source, target, sel))


if __name__ == "__main__":
    main()
