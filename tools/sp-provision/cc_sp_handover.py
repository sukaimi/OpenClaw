#!/usr/bin/env python3
"""Phase 4 handover report — writes sp-handover-summary.json and notifies operator."""

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


def verdict_passed(verdict):
    if verdict is None:
        return False
    if verdict.get("pass") is True:
        return True
    status = verdict.get("status", "")
    return isinstance(status, str) and status.lower() == "pass"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    if config is None:
        print(f"ERROR: could not read config: {args.config}", file=sys.stderr)
        sys.exit(0)

    source_url = config.get("sourceUrl", "")
    target_site = config.get("targetSite", "")
    job_dir = Path(config.get("jobDir", f"/srv/projects/{args.job}"))

    scored_data = load_json(job_dir / "sp-scored.json", default={"scored": []})
    scored_pages = scored_data.get("scored", [])

    exceptions_data = load_json(job_dir / "sp-exceptions.json", default={"exceptions": []})
    exceptions = exceptions_data.get("exceptions", [])
    exception_names = {e["name"] for e in exceptions}

    # Load all qa-verdict-*.json files
    verdict_files = glob.glob(str(job_dir / "qa-verdict-*.json"))
    verdicts = {}
    for vf in verdict_files:
        v = load_json(vf)
        if v:
            # key by page name — try "name", "page", or stem of filename
            name = v.get("name") or v.get("page")
            if not name:
                stem = Path(vf).stem  # qa-verdict-PageName
                name = stem.replace("qa-verdict-", "", 1) + ".aspx"
            verdicts[name] = v

    # Compile migrated, deferred, tier_breakdown
    migrated = []
    deferred = []
    tier_breakdown = {"T1": 0, "T2": 0, "T3": 0}

    for page in scored_pages:
        name = page.get("name", "")
        tier = page.get("tier")
        tier_key = f"T{tier}" if tier in (1, 2, 3) else None
        if tier_key:
            tier_breakdown[tier_key] += 1

        verdict = verdicts.get(name)
        if verdict is not None and verdict_passed(verdict):
            migrated.append(name)
        elif name not in exception_names:
            if verdict is None:
                deferred.append(name)
            # if verdict exists but failed, treat as exception omission — leave in deferred

    summary = {
        "job": args.job,
        "source": source_url,
        "migrated": migrated,
        "exceptions": exceptions,
        "tier_breakdown": tier_breakdown,
        "deferred": deferred,
    }

    summary_path = job_dir / "sp-handover-summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    n_migrated = len(migrated)
    n_exceptions = len(exceptions)
    n_deferred = len(deferred)
    t1 = tier_breakdown["T1"]
    t2 = tier_breakdown["T2"]
    t3 = tier_breakdown["T3"]

    message = (
        f"✅ [{args.job}] Handover Summary — {source_url}\n\n"
        f"Migrated: {n_migrated} pages\n"
        f"Tier 1: {t1} | Tier 2: {t2} | Tier 3: {t3}\n"
        f"Exceptions (needs review): {n_exceptions} — see Content Tracker\n"
        f"Deferred (low-priority, not migrated): {n_deferred} pages\n\n"
        f"Target: {target_site}\n"
        f"Full report in Content Tracker (sp-handover-summary.json)."
    )

    try:
        subprocess.run(["cc-notify-operator", message], timeout=60)
    except Exception as e:
        print(f"WARNING: notify failed: {e}", file=sys.stderr)

    print(f"Handover summary written to {summary_path}")
    print(message)
    sys.exit(0)


if __name__ == "__main__":
    main()
