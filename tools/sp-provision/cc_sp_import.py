#!/usr/bin/env python3
"""
cc_sp_import.py — Import a CC export package into a client's SharePoint tenant.

Usage:
  cc_sp_import.py --package <path-to-export-dir> \
                  --target-site <https://client.sharepoint.com/sites/their-site> \
                  --tenant <client-tenant-id> \
                  [--dry-run]

The client tenant must have granted the O/C app registration Sites.Selected
write access on the target site before running this script.
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Auth — build tenant (for image downloads)
# ---------------------------------------------------------------------------

sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token  # noqa: E402

GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"


def build_headers():
    """Headers using OUR (build) tenant token — for downloading images."""
    return {"Authorization": "Bearer " + graph_token()}


def client_headers(token):
    """Headers using CLIENT tenant token."""
    return {"Authorization": "Bearer " + token}


# ---------------------------------------------------------------------------
# Client tenant auth
# ---------------------------------------------------------------------------

def mint_client_token(tenant_id):
    """Acquire a Graph token for the client tenant using the same app cert."""
    import msal

    cfg = json.load(open("/root/.openclaw/config.json"))["sharepoint"]
    key_path = cfg["certPath"].replace(".pfx", "-key.pem")
    app = msal.ConfidentialClientApplication(
        cfg["clientId"],
        authority="https://login.microsoftonline.com/%s" % tenant_id,
        client_credential={
            "thumbprint": cfg["certThumbprint"],
            "private_key": open(key_path).read(),
        },
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise SystemExit(
            "[import] ERROR: failed to mint client token: %s"
            % result.get("error_description", result)
        )
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def graph_get(url, headers, params=None):
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def graph_post(url, headers, body):
    h = {**headers, "Content-Type": "application/json"}
    resp = requests.post(url, headers=h, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def graph_put_bytes(url, headers, data, content_type="application/octet-stream"):
    h = {**headers, "Content-Type": content_type}
    resp = requests.put(url, headers=h, data=data, timeout=60)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Site resolution
# ---------------------------------------------------------------------------

def resolve_site_id(site_url, headers):
    """Resolve a SharePoint site URL to its Graph site ID."""
    parsed = urlparse(site_url)
    hostname = parsed.hostname  # e.g. client.sharepoint.com
    # strip leading /sites/ or /
    path = parsed.path.rstrip("/")  # e.g. /sites/their-site
    url = "%s/sites?hostname=%s&path=%s" % (GRAPH, hostname, path)
    data = graph_get(url, headers)
    items = data.get("value", [])
    if not items:
        raise RuntimeError("No site found for URL: %s" % site_url)
    return items[0]["id"]


def get_site_url_from_id(site_id, headers):
    """Return the webUrl for a site given its id."""
    data = graph_get("%s/sites/%s" % (GRAPH, site_id), headers)
    return data["webUrl"].rstrip("/")


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def find_site_assets_drive(site_id, headers):
    """Return the driveId for the 'Site Assets' document library."""
    data = graph_get("%s/sites/%s/drives" % (GRAPH, site_id), headers)
    for drive in data.get("value", []):
        if drive.get("name", "").lower() in ("site assets", "siteassets"):
            return drive["id"]
    # fallback: first drive
    drives = data.get("value", [])
    if drives:
        return drives[0]["id"]
    raise RuntimeError("No drives found on client site %s" % site_id)


# ---------------------------------------------------------------------------
# Image transfer
# ---------------------------------------------------------------------------

def filename_from_url(url):
    return url.rstrip("/").split("/")[-1]


def upload_image(url, job, drive_id, client_token):
    """
    Download image from build site (build token), upload to client Site Assets.
    Returns the new URL on the client site.
    """
    filename = filename_from_url(url)
    # Download from build site using OUR token
    resp = requests.get(url, headers=build_headers(), timeout=30)
    resp.raise_for_status()
    image_bytes = resp.content
    content_type = resp.headers.get("Content-Type", "application/octet-stream")

    # Upload to client Site Assets under /Migrated/<job>/
    upload_url = (
        "%s/drives/%s/root:/Migrated/%s/%s:/content" % (GRAPH, drive_id, job, filename)
    )
    put_resp = graph_put_bytes(
        upload_url, client_headers(client_token), image_bytes, content_type
    )
    result = put_resp.json()
    return result.get("webUrl") or result.get("@microsoft.graph.downloadUrl", "")


# ---------------------------------------------------------------------------
# Canvas JSON helpers
# ---------------------------------------------------------------------------

def strip_odata_keys(obj):
    """Recursively remove @odata.* keys from a dict/list structure."""
    if isinstance(obj, dict):
        return {
            k: strip_odata_keys(v)
            for k, v in obj.items()
            if not k.startswith("@odata.")
        }
    if isinstance(obj, list):
        return [strip_odata_keys(i) for i in obj]
    return obj


def rewrite_urls(canvas_str, url_map):
    """String-replace all build URLs with client URLs in the canvas JSON string."""
    for old, new in url_map.items():
        if old and new:
            canvas_str = canvas_str.replace(old, new)
    return canvas_str


# ---------------------------------------------------------------------------
# Page import
# ---------------------------------------------------------------------------

def import_page(page_meta, package_dir, job, build_site_url, client_site_id,
                client_site_url, drive_id, client_token, image_map, dry_run):
    name = page_meta["name"]
    title = page_meta["title"]
    canvas_file = os.path.join(package_dir, page_meta["file"])

    if not os.path.exists(canvas_file):
        print("[import] page %s: FAILED canvas file not found: %s" % (name, canvas_file))
        return False

    canvas = json.load(open(canvas_file))
    canvas = strip_odata_keys(canvas)

    # Build old→new URL map: for each image URL in the imageMap values (build-site URLs)
    # key = original source URL, value = build-site URL
    url_map = {}
    for orig_src, build_url in image_map.items():
        if not build_url:
            continue
        if dry_run:
            # Derive what the client URL would be (don't actually upload)
            filename = filename_from_url(build_url)
            fake_client_url = "%s/SiteAssets/Migrated/%s/%s" % (client_site_url, job, filename)
            url_map[build_url] = fake_client_url
            url_map[orig_src] = fake_client_url
        else:
            try:
                new_url = upload_image(build_url, job, drive_id, client_token)
                url_map[build_url] = new_url
                url_map[orig_src] = new_url
            except Exception as e:
                print("[import] page %s: WARNING image upload failed (%s): %s" % (name, build_url, e))
                # continue with unrewritten URL; don't abort the page

    # Rewrite canvas JSON string
    canvas_str = json.dumps(canvas)
    # Also do a bulk prefix replace: buildSiteUrl → clientSiteUrl
    if build_site_url and client_site_url:
        canvas_str = canvas_str.replace(build_site_url.rstrip("/"), client_site_url.rstrip("/"))
    canvas_str = rewrite_urls(canvas_str, url_map)
    canvas = json.loads(canvas_str)

    if dry_run:
        print("[import][dry-run] would POST page '%s' (%s) to site %s" % (title, name, client_site_id))
        print("[import][dry-run]   image rewrites: %d" % len(url_map))
        return True

    # POST page
    body = {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": name,
        "title": title,
        "pageLayout": "article",
        "canvasLayout": canvas,
    }
    try:
        result = graph_post(
            "%s/sites/%s/pages" % (GRAPH_BETA, client_site_id),
            client_headers(client_token),
            body,
        )
        page_id = result.get("id")
    except Exception as e:
        print("[import] page %s: FAILED on POST: %s" % (name, e))
        return False

    # Publish
    try:
        graph_post(
            "%s/sites/%s/pages/%s/microsoft.graph.sitePage/publish"
            % (GRAPH_BETA, client_site_id, page_id),
            client_headers(client_token),
            {},
        )
    except Exception as e:
        print("[import] page %s: WARNING publish failed: %s" % (name, e))
        # Don't fail the page — it was created, just not published

    print("[import] page %s: OK" % name)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Import CC export package to client SharePoint tenant")
    ap.add_argument("--package", required=True, help="Path to export package directory")
    ap.add_argument("--target-site", required=True, help="Client site URL, e.g. https://client.sharepoint.com/sites/their-site")
    ap.add_argument("--tenant", required=True, help="Client tenant ID (GUID)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen; skip all writes")
    args = ap.parse_args()

    package_dir = os.path.abspath(args.package)
    manifest_path = os.path.join(package_dir, "manifest.json")

    if not os.path.isdir(package_dir):
        sys.exit("[import] ERROR: package dir not found: %s" % package_dir)
    if not os.path.exists(manifest_path):
        sys.exit("[import] ERROR: manifest.json not found in %s" % package_dir)

    manifest = json.load(open(manifest_path))
    job = manifest["job"]
    build_site_url = manifest.get("buildSiteUrl", "").rstrip("/")
    image_map = manifest.get("imageMap", {})
    pages = manifest.get("pages", [])

    print("[import] package: %s  job: %s  pages: %d" % (package_dir, job, len(pages)))
    if args.dry_run:
        print("[import] DRY-RUN mode — no writes will occur")

    # Mint client token
    print("[import] minting client token for tenant %s ..." % args.tenant)
    client_token = mint_client_token(args.tenant)

    # Resolve client site ID
    print("[import] resolving client site: %s" % args.target_site)
    try:
        client_site_id = resolve_site_id(args.target_site, client_headers(client_token))
    except Exception as e:
        sys.exit("[import] ERROR: could not resolve client site: %s" % e)

    # Get canonical client site URL
    try:
        client_site_url = get_site_url_from_id(client_site_id, client_headers(client_token))
    except Exception:
        client_site_url = args.target_site.rstrip("/")

    print("[import] client site id: %s  url: %s" % (client_site_id, client_site_url))

    # Find Site Assets drive
    drive_id = None
    if not args.dry_run:
        try:
            drive_id = find_site_assets_drive(client_site_id, client_headers(client_token))
            print("[import] site assets drive: %s" % drive_id)
        except Exception as e:
            sys.exit("[import] ERROR: could not find Site Assets drive: %s" % e)

    # Import pages
    ok = 0
    failed = 0
    for page_meta in pages:
        success = import_page(
            page_meta=page_meta,
            package_dir=package_dir,
            job=job,
            build_site_url=build_site_url,
            client_site_id=client_site_id,
            client_site_url=client_site_url,
            drive_id=drive_id,
            client_token=client_token,
            image_map=image_map,
            dry_run=args.dry_run,
        )
        if success:
            ok += 1
        else:
            failed += 1

    print("[import] %d pages imported, %d failed" % (ok, failed))
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
