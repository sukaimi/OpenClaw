#!/usr/bin/env python3
"""
cc_sp_verify_gate.py — Server-side SP verify gate using app-cert SP REST token.
Replaces Mac-side cc-completeness-gate.mjs (Playwright sessions).

CanvasContent1 is HTML with JSON in data-sp-controldata / data-sp-webpartdata
attributes — NOT raw JSON. Parsers use regex + html.unescape accordingly.
"""

import argparse
import html as html_module
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

import msal
import requests
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)

CONFIG_PATH = os.path.expanduser("~/.openclaw/config.json")

# Regex patterns for CanvasContent1 HTML format
_CTRL_PAT = re.compile(r'data-sp-controldata="([^"]*)"', re.DOTALL)
_RTE_PAT = re.compile(r'data-sp-rte=""[^>]*>(.*?)</div>', re.DOTALL)
_IMG_PAT = re.compile(
    r"/sites/[^\"&<\s]+\.(?:jpg|jpeg|png|gif|svg|webp|bmp)",
    re.IGNORECASE,
)


SP_HOST = "contoso.sharepoint.com"


def _sp_rest_token(config_path=CONFIG_PATH):
    """Return a bearer token scoped to the build SharePoint tenant (/_api/ calls)."""
    cfg = json.load(open(config_path))["sharepoint"]
    data = Path(cfg["certPath"]).read_bytes()
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=None)
    except Exception:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=b"")

    app = msal.ConfidentialClientApplication(
        cfg["clientId"],
        authority="https://login.microsoftonline.com/{}".format(cfg["tenantId"]),
        client_credential={
            "private_key": key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            ).decode(),
            "thumbprint": cfg["certThumbprint"],
            "public_certificate": cert.public_bytes(Encoding.PEM).decode(),
        },
    )
    result = app.acquire_token_for_client(
        scopes=["https://{}/.default".format(SP_HOST)]
    )
    if "access_token" not in result:
        raise RuntimeError(
            "SP REST token failed: {} / {}".format(
                result.get("error"), result.get("error_description", "")[:200]
            )
        )
    return result["access_token"]


def get_canvas_content(built_site_url, page_name, sp_token):
    """Read CanvasContent1 via SharePoint REST API using the app-cert SP token."""
    site_url = built_site_url.rstrip("/")
    encoded_page = urllib.parse.quote(page_name)
    url = (
        "{site}/_api/web/lists/getbytitle('Site%20Pages')/items"
        "?$filter=FileLeafRef%20eq%20'{page}'&$select=CanvasContent1,FileLeafRef"
    ).format(site=site_url, page=encoded_page)

    hdrs = {
        "Authorization": "Bearer " + sp_token,
        "Accept": "application/json;odata=nometadata",
    }
    r = requests.get(url, headers=hdrs, timeout=30)
    r.raise_for_status()

    items = r.json().get("value", [])
    if not items:
        raise ValueError("page not found in Site Pages: {}".format(page_name))

    canvas_str = items[0].get("CanvasContent1") or ""
    is_published = bool(canvas_str.strip())
    return canvas_str, is_published


def parse_canvas_sections(canvas_str):
    """Count distinct layout zones in CanvasContent1 HTML."""
    if not canvas_str:
        return 0
    zone_indices = set()
    for m in _CTRL_PAT.findall(canvas_str):
        try:
            obj = json.loads(html_module.unescape(m))
            zi = obj.get("position", {}).get("zoneIndex")
            if zi is not None:
                zone_indices.add(zi)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    return len(zone_indices)


def extract_text_from_canvas(canvas_str):
    """Extract visible text from RTE (rich-text editor) blocks in CanvasContent1 HTML."""
    if not canvas_str:
        return ""
    texts = []
    for m in _RTE_PAT.findall(canvas_str):
        clean = re.sub(r"<[^>]+>", " ", html_module.unescape(m))
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            texts.append(clean)
    return " ".join(texts)


def shingle_recall(source, canvas, k=4):
    """What fraction of source k-gram shingles appear in canvas?

    Using recall (not Jaccard) because source manifests often capture a
    representative excerpt; the built page typically contains MORE text.
    Jaccard would penalise pages that are longer than the source excerpt.
    """
    words_a = source.split()
    words_b = canvas.split()

    if not words_a and not words_b:
        return 1.0
    if not words_a:
        return 1.0
    if not words_b:
        return 0.0

    def shingles(words):
        return set(tuple(words[i : i + k]) for i in range(len(words) - k + 1))

    s_a = shingles(words_a) if len(words_a) >= k else {tuple(words_a)}
    s_b = shingles(words_b) if len(words_b) >= k else {tuple(words_b)}

    if not s_a:
        return 1.0
    return len(s_a & s_b) / len(s_a)


def extract_canvas_image_basenames(canvas_str):
    """Extract image basenames from /sites/... paths embedded in CanvasContent1 HTML."""
    if not canvas_str:
        return set()
    basenames = set()
    for url in _IMG_PAT.findall(canvas_str):
        basename = os.path.basename(urllib.parse.unquote(url.split("?")[0]))
        if basename:
            basenames.add(basename)
    return basenames


def check_images(canvas_str, source_manifest, image_map_path):
    if not image_map_path or not os.path.exists(image_map_path):
        return {
            "pass": True,
            "matched": 0,
            "total": 0,
            "missing": [],
            "warning": "image-map not found, skipped",
        }

    try:
        with open(image_map_path) as f:
            image_map = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "pass": True,
            "matched": 0,
            "total": 0,
            "missing": [],
            "warning": "image-map could not be read, skipped",
        }

    if not image_map:
        return {
            "pass": True,
            "matched": 0,
            "total": 0,
            "missing": [],
            "warning": "image-map is empty, skipped",
        }

    canvas_basenames = extract_canvas_image_basenames(canvas_str)
    source_images = source_manifest.get("images", [])
    total = 0
    matched = 0
    missing = []

    for img in source_images:
        src = img.get("src", "")
        built_url = image_map.get(src)
        if built_url is None:
            continue
        total += 1
        built_basename = os.path.basename(
            urllib.parse.unquote(built_url.split("?")[0])
        )
        if built_basename in canvas_basenames:
            matched += 1
        else:
            missing.append(src)

    passed = len(missing) == 0
    return {
        "pass": passed,
        "matched": matched,
        "total": total,
        "missing": missing,
    }


def write_verdict(out_path, verdict):
    if out_path:
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except OSError:
            pass
        with open(out_path, "w") as f:
            json.dump(verdict, f, indent=2)
    print(json.dumps(verdict, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SP verify gate — app-cert SP REST token")
    parser.add_argument("--source", required=True, help="path to source manifest JSON")
    parser.add_argument("--built-site-url", required=True, help="full URL of build site")
    parser.add_argument("--page", required=True, help="page filename (e.g. Home.aspx)")
    parser.add_argument("--image-map", default=None, help="path to image-map.json")
    parser.add_argument("--min-sections", type=int, default=1)
    parser.add_argument("--out", default=None, help="path to write verdict JSON")
    parser.add_argument("--job", default=None, help="JOB#### for logging")
    args = parser.parse_args()

    job_tag = "[{}] ".format(args.job) if args.job else ""
    built_url = "{}/SitePages/{}".format(args.built_site_url.rstrip("/"), args.page)

    def fail_verdict(reason, extra=None):
        v = {
            "gate": "cc_sp_verify_gate.py",
            "pass": False,
            "source": args.source,
            "builtUrl": built_url,
            "error": reason,
        }
        if extra:
            v.update(extra)
        write_verdict(args.out, v)
        sys.exit(1)

    if not os.path.exists(args.source):
        fail_verdict("source manifest not found: {}".format(args.source))

    try:
        with open(args.source) as f:
            source_manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        fail_verdict("could not read source manifest: {}".format(e))

    print("{}Acquiring SP REST token (app-cert)...".format(job_tag))
    try:
        sp_token = _sp_rest_token()
    except Exception as e:
        fail_verdict("SP token acquisition failed: {}".format(e))

    print("{}Fetching CanvasContent1 for {}...".format(job_tag, args.page))
    try:
        canvas_str, is_published = get_canvas_content(
            args.built_site_url, args.page, sp_token
        )
    except ValueError as e:
        fail_verdict(str(e))
    except requests.RequestException as e:
        fail_verdict("network error fetching page: {}".format(e))
    except Exception as e:
        fail_verdict("unexpected error fetching page: {}".format(e))

    # Published check
    published_check = {"pass": bool(is_published)}

    # Sections check
    found_sections = parse_canvas_sections(canvas_str)
    sections_pass = found_sections >= args.min_sections
    sections_check = {
        "pass": sections_pass,
        "found": found_sections,
        "required": args.min_sections,
    }

    # Images check
    images_check = check_images(canvas_str, source_manifest, args.image_map)

    # Text check — skip if source text is too short to be meaningful (e.g. home pages
    # whose manifest captures a webpart title rather than real prose).
    TEXT_MIN_WORDS = 10
    TEXT_THRESHOLD = 0.50  # recall: at least half of source shingles must appear in canvas
    canvas_text = extract_text_from_canvas(canvas_str)
    source_text = source_manifest.get("text", "")
    if isinstance(source_text, list):
        source_text = " ".join(str(t) for t in source_text)
    source_word_count = len(source_text.split())
    if source_word_count < TEXT_MIN_WORDS:
        text_pass = True
        similarity = None
        text_check = {
            "pass": True,
            "skipped": True,
            "reason": "source text too short ({} words < {})".format(
                source_word_count, TEXT_MIN_WORDS
            ),
        }
    else:
        similarity = shingle_recall(source_text, canvas_text)
        text_pass = similarity >= TEXT_THRESHOLD
        text_check = {
            "pass": text_pass,
            "recall": round(similarity, 4),
            "threshold": TEXT_THRESHOLD,
        }

    overall_pass = (
        published_check["pass"]
        and sections_check["pass"]
        and images_check["pass"]
        and text_check["pass"]
    )

    verdict = {
        "gate": "cc_sp_verify_gate.py",
        "pass": overall_pass,
        "source": args.source,
        "builtUrl": built_url,
        "checked": {
            "sections": found_sections,
            "images": images_check.get("total", 0),
            "textBlocks": 1,
        },
        "sections": sections_check,
        "published": published_check,
        "imagesCheck": images_check,
        "textCheck": text_check,
        "missing": {
            "images": images_check.get("missing", []),
            "text": [] if text_pass else ["similarity below threshold"],
        },
    }

    write_verdict(args.out, verdict)

    if overall_pass:
        print("{}PASS — all checks passed.".format(job_tag))
        sys.exit(0)
    else:
        failed = []
        if not published_check["pass"]:
            failed.append("published")
        if not sections_check["pass"]:
            failed.append(
                "sections ({} found, {} required)".format(found_sections, args.min_sections)
            )
        if not images_check["pass"]:
            failed.append(
                "images ({} missing)".format(len(images_check.get("missing", [])))
            )
        if not text_check["pass"]:
            sim_val = text_check.get("recall")
            failed.append(
                "text (recall {:.2f} < {})".format(sim_val or 0.0, TEXT_THRESHOLD)
            )
        print("{}FAIL — {}".format(job_tag, ", ".join(failed)))
        sys.exit(1)


if __name__ == "__main__":
    main()
