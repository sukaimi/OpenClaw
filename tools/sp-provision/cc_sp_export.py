#!/usr/bin/env python3
"""
cc_sp_export.py — Export built SharePoint pages from the CCBuild tenant
for re-import into a client's own SharePoint tenant.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token  # noqa: E402


def get_headers():
    return {"Authorization": "Bearer " + graph_token()}


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

GRAPH_BETA = "https://graph.microsoft.com/beta"


def graph_get(url, params=None):
    resp = requests.get(url, headers=get_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def list_pages(site_id):
    """Return all site pages (id, name, title, webUrl)."""
    url = f"{GRAPH_BETA}/sites/{site_id}/pages"
    params = {"$select": "id,name,title,webUrl", "$top": "200"}
    data = graph_get(url, params)
    pages = data.get("value", [])
    # handle paging
    while "@odata.nextLink" in data:
        data = graph_get(data["@odata.nextLink"])
        pages.extend(data.get("value", []))
    return pages


def get_page_canvas(site_id, page_id):
    """Fetch full sitePage with canvasLayout expanded."""
    url = f"{GRAPH_BETA}/sites/{site_id}/pages/{page_id}/microsoft.graph.sitePage"
    data = graph_get(url, params={"$expand": "canvasLayout"})
    return data


# ---------------------------------------------------------------------------
# Strip @odata.* keys recursively
# ---------------------------------------------------------------------------

ODATA_RE = re.compile(r"^@odata\.")


def strip_odata(obj):
    if isinstance(obj, dict):
        return {k: strip_odata(v) for k, v in obj.items() if not ODATA_RE.match(k)}
    if isinstance(obj, list):
        return [strip_odata(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Export CCBuild SP pages for client re-import")
    parser.add_argument("--job", required=True, help="Job ID, e.g. JOB0023")
    parser.add_argument("--config", help="Path to job.config.json (default: /srv/projects/<JOB>/job.config.json)")
    parser.add_argument("--out", help="Output directory (default: /srv/projects/<JOB>/sp-export-package/)")
    args = parser.parse_args()

    job = args.job
    config_path = args.config or f"/srv/projects/{job}/job.config.json"
    job_dir = os.path.dirname(config_path)

    # Load job config to get jobDir if available
    if os.path.exists(config_path):
        with open(config_path) as f:
            job_config = json.load(f)
        job_dir = job_config.get("jobDir", job_dir)

    out_dir = args.out or os.path.join(job_dir, "sp-export-package")
    pages_dir = os.path.join(out_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    # --- Load inputs ---
    def load_json(name):
        path = os.path.join(job_dir, name)
        if not os.path.exists(path):
            print(f"[export] ERROR: {path} not found", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            return json.load(f)

    site_data = load_json("site.json")
    handover = load_json("sp-handover-summary.json")
    expect = load_json("sp-expect.json")
    image_map_raw = load_json("image-map.json")

    site_id = site_data["siteId"]
    site_url = site_data["siteUrl"]
    source_url = handover.get("source", "")
    image_map = image_map_raw.get("_map", {})

    migrated_names = {p["name"] for p in handover.get("migrated", [])}
    migrated_titles = {p["name"]: p.get("title", "") for p in handover.get("migrated", [])}

    if not migrated_names:
        print("[export] WARNING: no migrated pages found in sp-handover-summary.json")

    # --- Fetch page index from Graph ---
    print(f"[export] Fetching page list for site {site_id} ...")
    try:
        all_pages = list_pages(site_id)
    except requests.HTTPError as e:
        print(f"[export] ERROR fetching pages: {e}", file=sys.stderr)
        sys.exit(1)

    page_index = {p["name"]: p for p in all_pages}

    # --- Export each migrated page ---
    exported = []
    errors = []

    for name in sorted(migrated_names):
        if name not in page_index:
            print(f"[export] WARNING: page '{name}' not found in build site — skipping")
            errors.append({"name": name, "error": "not found in build site"})
            continue

        page_meta = page_index[name]
        page_id = page_meta["id"]

        print(f"[export] Exporting '{name}' (id={page_id}) ...")
        try:
            full_page = get_page_canvas(site_id, page_id)
        except requests.HTTPError as e:
            print(f"[export] ERROR fetching canvas for '{name}': {e}", file=sys.stderr)
            errors.append({"name": name, "error": str(e)})
            continue

        canvas = full_page.get("canvasLayout", {})
        canvas_clean = strip_odata(canvas)

        page_file = f"pages/{name}.json"
        page_export = {
            "name": name,
            "title": full_page.get("title", migrated_titles.get(name, "")),
            "id": page_id,
            "webUrl": page_meta.get("webUrl", ""),
            "canvasLayout": canvas_clean,
        }

        with open(os.path.join(out_dir, page_file), "w") as f:
            json.dump(page_export, f, indent=2)

        exported.append({
            "name": name,
            "title": page_export["title"],
            "file": page_file,
        })

    # --- Write manifest ---
    manifest = {
        "job": job,
        "sourceUrl": source_url,
        "buildSiteId": site_id,
        "buildSiteUrl": site_url,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "pages": exported,
        "imageMap": image_map,
    }
    if errors:
        manifest["exportErrors"] = errors

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[export] wrote {len(exported)} pages to {out_dir}")
    if errors:
        print(f"[export] WARNING: {len(errors)} page(s) failed — see manifest.exportErrors")

    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
