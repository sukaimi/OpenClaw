#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    try:
        with open(args.config) as f:
            config = json.load(f)
    except Exception as e:
        print(f"ERROR: Could not read config: {e}", file=sys.stderr)
        sys.exit(1)

    job_dir = config.get("jobDir", "")
    source_url = config.get("sourceUrl", "")

    scored_path = Path(job_dir) / "sp-scored.json"
    try:
        with open(scored_path) as f:
            scored_data = json.load(f)
    except Exception as e:
        print(f"ERROR: Could not read sp-scored.json: {e}", file=sys.stderr)
        sys.exit(1)

    pages = scored_data.get("scored", [])
    total = len(pages)

    tiers = {1: [], 2: [], 3: []}
    for p in pages:
        t = p.get("tier", 3)
        if t in tiers:
            tiers[t].append(p.get("title") or p.get("name", "Unknown"))

    def tier_line(tier_num, titles):
        if not titles:
            return None
        n = len(titles)
        preview = titles[:5]
        items = ", ".join(preview)
        if n > 5:
            items += f", ...and {n - 5} more"
        return f"  Tier {tier_num} ({n} pages): {items}"

    lines = [
        f"📋 [{args.job}] Migration Plan — {source_url}",
        "",
        f"I've audited {total} pages and tiered them by importance:",
    ]

    for t in [1, 2, 3]:
        line = tier_line(t, tiers[t])
        if line:
            lines.append(line)

    lines += [
        "",
        "Migration starting now. I'll send a progress update after each batch of 10 pages, and a full handover report at the end.",
    ]

    message = "\n".join(lines)
    print(message)

    try:
        result = subprocess.run(["cc-notify-operator", message], timeout=60)
        if result.returncode != 0:
            print(f"ERROR: cc-notify-operator exited {result.returncode}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to send notification: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
