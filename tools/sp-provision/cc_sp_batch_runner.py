#!/usr/bin/env python3
"""
cc_sp_batch_runner.py — Phase 3 batch execution runner for SP classic→modern migration.
Usage: python3 cc_sp_batch_runner.py --config <path/to/job.config.json>
"""

import argparse
import json
import os
import subprocess
import sys

BATCH_SIZE = 10
CANVAS_COMPOSE = "/root/.openclaw/sp-provision/canvas_compose.py"
HOMEPAGES = {"home.aspx", "default.aspx"}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def notify(message):
    try:
        subprocess.run(["cc-notify-operator", message], timeout=60)
    except Exception as e:
        print(f"[batch-runner] WARNING: notify failed: {e}")


def log_exceptions(exceptions_path, pages, batch_num, reason_template):
    existing = {"exceptions": []}
    if os.path.exists(exceptions_path):
        try:
            existing = load_json(exceptions_path)
        except Exception:
            pass
    for page in pages:
        existing["exceptions"].append({
            "name": page,
            "reason": reason_template % batch_num,
            "batch": batch_num,
        })
    save_json(exceptions_path, existing)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    job = config["job"]
    job_dir = config["jobDir"]
    heavy_cap = config.get("heavyWebpartCap", 6)
    build_cap = config.get("buildCap", None)

    scored_path = os.path.join(job_dir, "sp-scored.json")
    exceptions_path = os.path.join(job_dir, "sp-exceptions.json")

    scored_data = load_json(scored_path)
    all_pages = [p["name"] for p in scored_data.get("scored", [])]

    # Filter out homepages (handled separately by sp_home_compose.py)
    pages = [p for p in all_pages if p.lower() not in HOMEPAGES]

    # Apply buildCap
    if build_cap is not None:
        pages = pages[:build_cap]

    total_pages = len(pages)
    batches = [pages[i:i + BATCH_SIZE] for i in range(0, total_pages, BATCH_SIZE)]
    total_batches = len(batches)

    print(f"[batch-runner] {job}: {total_pages} pages across {total_batches} batches (heavy-cap={heavy_cap})")

    exception_count = 0

    for i, batch in enumerate(batches, start=1):
        print(f"\n=== BATCH {i}/{total_batches} ===")
        for name in batch:
            print(f"  {name}")

        pages_arg = ",".join(batch)
        cmd = [
            sys.executable,
            CANVAS_COMPOSE,
            "--job", job,
            "--pages", pages_arg,
            "--heavy-cap", str(heavy_cap),
        ]

        result = subprocess.run(cmd)

        if result.returncode != 0:
            log_exceptions(exceptions_path, batch, i, "compose failed (batch %d)")
            exception_count += len(batch)
            print(f"[batch-runner] EXCEPTION: batch {i} failed, pages logged, continuing")

        exc_note = f"{exception_count} exception(s) so far"
        notify(
            f"[{job}] Batch {i}/{total_batches} complete. "
            f"Pages: {pages_arg}. {exc_note}."
        )

    print(f"\n[batch-runner] Done. {exception_count} exception(s) total.")
    # Fail-closed: a partial/failed build must NOT report success to automation.
    if exception_count > 0:
        print(f"[batch-runner] FAILURE: {exception_count} page(s) failed to compose; exiting non-zero.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
