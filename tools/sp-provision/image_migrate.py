#!/usr/bin/env python3
"""image-migrate.py — IMAGE MIGRATION step for a SharePoint classic->modern CONVERSION job.

PREPARED, NOT WIRED LIVE. Review before adding to the build pipeline.

Given a JOB whose /srv/projects/<JOB>/sp-expect.json was produced by the enhanced sp-audit.py
(each pages[] entry now carries an images[] array of {src, filename, alt}), this:

  1. DOWNLOADS each source image (app READ) from the classic source site, via SP REST
     /_api/web/getfilebyserverrelativeurl('<server-rel>')/$value  (server-relative srcs like
     /sites/CrestfieldClassic/SiteAssets/classic-team.jpg). External (http) srcs are fetched
     directly; data: URIs are skipped by the audit already.
  2. UPLOADS each to the BUILD site's 'Site Assets' library under a per-job folder
     (Migrated/<JOB>/<filename>) via spclient.SP.upload_file (Graph PUT .../content).
  3. RETURNS / writes an old-src -> new build-site URL MAP the BUILD step uses to rewrite
     <img src> when it emits the modern page HTML.

Idempotent: if a target already exists in the build Site Assets it is reused (the Graph PUT
content API overwrites in place; we also short-circuit on a HEAD-style existence check). Re-runs
produce the same map. Read-only on the SOURCE.

USAGE (run on the VPS, openclaw venv, PYTHONPATH=/root/.openclaw/sp-provision):

    image-migrate.py --job JOB0022
    image-migrate.py --job JOB0022 --out /srv/projects/JOB0022/image-map.json
    image-migrate.py --expect /tmp/sp-expect.json --build-host x.sharepoint.com \
                     --build-path /sites/CCBuild-0022 --out /tmp/image-map.json

Emits image-map.json: { "<original-src>": "<new-build-url>", ... } plus a per-image detail list.
The BUILD step loads this map and, for each pages[].images[].src, replaces the <img src> with
the mapped build URL before calling sp.create_page(...).
"""
import sys, os, re, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from urllib.parse import urlparse, unquote
import requests
from spclient import SP, graph_token, GRAPH, _load_sp_config

BUILD_ASSET_DRIVE = "Documents"           # build-site library images land in
MIGRATED_PREFIX = "Migrated"                  # per-job subfolder: Migrated/<JOB>/<file>
_EXT_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
    ".bmp": "image/bmp", ".ico": "image/x-icon",
}


def _arg(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def _mime_for(filename):
    ext = os.path.splitext(filename)[1].lower()
    return _EXT_MIME.get(ext, "application/octet-stream")


def _sp_rest_token(host, tenant=None):
    """Host-scoped SharePoint-resource bearer token from the app cert (mirrors
    sp-audit.py._sp_rest_token / cc_provision_intake._sp_rest_token)."""
    import msal
    from pathlib import Path
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption,
    )
    cfg = _load_sp_config()
    _tenant = tenant or cfg["tenantId"]
    data = Path(cfg["certPath"]).read_bytes()
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=None)
    except Exception:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=b"")
    app = msal.ConfidentialClientApplication(
        cfg["clientId"],
        authority="https://login.microsoftonline.com/%s" % _tenant,
        client_credential={
            "private_key": key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode(),
            "thumbprint": cfg["certThumbprint"],
            "public_certificate": cert.public_bytes(Encoding.PEM).decode(),
        })
    r = app.acquire_token_for_client(scopes=["https://%s/.default" % host])
    if "access_token" not in r:
        raise RuntimeError("SP REST token failed: %s / %s"
                           % (r.get("error"), str(r.get("error_description"))[:200]))
    return r["access_token"]


def _download_source_image(src, source_host, source_web, src_tenant=None):
    """Return (bytes, ok). Server-relative src -> SP REST getfilebyserverrelativeurl/$value
    on the SOURCE host. Absolute http(s) -> direct GET. Returns (b'', False) on failure."""
    s = src.strip()
    if s.lower().startswith("http://") or s.lower().startswith("https://"):
        # external image; fetch directly (still read-only)
        g = requests.get(s)
        return (g.content, True) if g.status_code < 300 else (b"", False)
    # server-relative (e.g. /sites/CrestfieldClassic/SiteAssets/classic-team.jpg)
    serverrel = s if s.startswith("/") else "/" + s
    tok = _sp_rest_token(source_host, src_tenant)
    h = {"Authorization": "Bearer " + tok, "Accept": "application/octet-stream"}
    # target the SOURCE SITE web (/sites/<name>), not the root web — the app's grant is site-scoped
    _p = unquote(serverrel).split("/")
    _webpath = "/".join(_p[:3]) if len(_p) > 2 and _p[1] in ("sites", "teams") else ""
    url = ("https://%s%s/_api/web/getfilebyserverrelativeurl('%s')/$value"
           % (source_host, _webpath, unquote(serverrel).replace("'", "''")))
    g = requests.get(url, headers=h)
    return (g.content, True) if g.status_code < 300 else (b"", False)


def _build_target_url(sp, server_path):
    """Resolve the webUrl of an uploaded build asset (the <img src> the page will use)."""
    did = sp.drive_id(BUILD_ASSET_DRIVE)
    path = server_path.lstrip("/")
    r = requests.get("%s/drives/%s/root:/%s" % (GRAPH, did, path), headers=sp.H)
    if r.status_code < 300:
        return r.json().get("webUrl")
    return None


def _exists_on_build(sp, server_path):
    did = sp.drive_id(BUILD_ASSET_DRIVE)
    path = server_path.lstrip("/")
    r = requests.get("%s/drives/%s/root:/%s?$select=id,size,webUrl" % (GRAPH, did, path),
                     headers=sp.H)
    if r.status_code < 300 and (r.json().get("size") or 0) > 0:
        return r.json().get("webUrl")
    return None


def migrate(expect, sp, job, source_host, source_web, src_tenant=None, capture_imgs=None):
    """Download+upload every images[] entry, return (url_map, details).
    url_map = {original_src: new_build_url}. Idempotent."""
    url_map, details = {}, []
    seen = set()
    for pg in expect.get("pages", []):
        for img in pg.get("images", []):
            src, fname = img.get("src"), img.get("filename")
            if not src or not fname or src in seen:
                continue
            seen.add(src)
            target = "%s/%s/%s" % (MIGRATED_PREFIX, job, fname)
            existing = _exists_on_build(sp, target)
            if existing:
                url_map[src] = existing
                details.append({"src": src, "filename": fname, "buildUrl": existing,
                                "status": "reused"})
                continue
            if capture_imgs is not None:
                fp = capture_imgs.get(src)
                data = open(fp, "rb").read() if (fp and os.path.exists(fp)) else b""
                ok = bool(data)
            else:
                data, ok = _download_source_image(src, source_host, source_web, src_tenant)
            if not ok or not data:
                details.append({"src": src, "filename": fname, "buildUrl": None,
                                "status": ("capture-missing" if capture_imgs is not None else "download-failed")})
                continue
            sp.upload_file(BUILD_ASSET_DRIVE, target, data, _mime_for(fname))
            new_url = _build_target_url(sp, target) or ""
            url_map[src] = new_url
            details.append({"src": src, "filename": fname, "buildUrl": new_url,
                            "status": "uploaded", "bytes": len(data)})
    return url_map, details


def rewrite_img_src(inner_html, url_map):
    """Helper the BUILD step calls: replace every <img src="<old>"> with the mapped build URL.
    Leaves srcs not in the map untouched (build can warn). Idempotent."""
    def repl(m):
        tag = m.group(0)
        sm = re.search(r'(\bsrc\s*=\s*["\'])([^"\']+)(["\'])', tag, re.I)
        if not sm:
            return tag
        old = sm.group(2)
        new = url_map.get(old)
        if not new:
            return tag
        return tag[:sm.start(2)] + new + tag[sm.end(2):]
    return re.sub(r"<img\b[^>]*>", repl, inner_html or "", flags=re.I)


def main():
    job = _arg("--job")
    expect_path = _arg("--expect") or (("/srv/projects/%s/sp-expect.json" % job) if job else None)
    out = _arg("--out") or (("/srv/projects/%s/image-map.json" % job) if job else "image-map.json")
    if not expect_path or not os.path.exists(expect_path):
        raise SystemExit("need --job <JOB> (with /srv/projects/<JOB>/sp-expect.json) or --expect <path>")
    expect = json.load(open(expect_path))

    source_web = expect.get("sourceUrl") or ""
    source_host = urlparse(source_web).netloc
    if not source_host:
        raise SystemExit("sp-expect.json missing sourceUrl; re-run sp-audit.py")

    # Cross-tenant Level-2 overrides. SOURCE reads can target the client tenant;
    # BUILD writes stay on our tenant. Both default None -> our own tenant.
    src_tenant = _arg("--src-tenant")
    build_tenant = _arg("--build-tenant")

    # Level-2: source images were captured Mac-side (cc-sp-capture). Read them from the
    # local bundle instead of an authed source download. Build upload stays our-tenant.
    capture_dir = _arg("--from-capture")
    capture_imgs = None
    if capture_dir:
        mp = os.path.join(capture_dir, "images-map.json")
        _m = json.load(open(mp)) if os.path.exists(mp) else {}
        # SECURITY (path traversal): images-map.json is untrusted and its values become
        # upload sources. Only accept paths that resolve to a regular file strictly
        # beneath the capture dir; reject absolute paths and `..` escapes.
        cap_root = os.path.realpath(capture_dir)
        capture_imgs = {}
        for src, rel in _m.items():
            fp = os.path.realpath(os.path.join(capture_dir, rel))
            if (os.path.commonpath([cap_root, fp]) == cap_root and fp != cap_root
                    and os.path.isfile(fp)):
                capture_imgs[src] = fp
            else:
                print("[img-migrate] SECURITY: rejected out-of-bundle image source %r -> %r" % (src, rel))

    # BUILD site: from site.json (preferred) or explicit flags
    build_host = _arg("--build-host")
    build_path = _arg("--build-path")
    if not (build_host and build_path) and job:
        site = json.load(open("/srv/projects/%s/site.json" % job))
        bu = urlparse(site.get("siteUrl") or site.get("webUrl") or site.get("url") or "")
        build_host = build_host or bu.netloc
        build_path = build_path or bu.path
    if not (build_host and build_path):
        raise SystemExit("need build site: --build-host + --build-path, or --job with site.json")

    sp = SP(site_host=build_host, site_path=build_path)
    total = sum(len(p.get("images", [])) for p in expect.get("pages", []))
    if total == 0:
        print("[img-migrate] source has 0 image refs in sp-expect.json — nothing to migrate.")
        json.dump({"_map": {}, "_details": []}, open(out, "w"), indent=2)
        return

    url_map, details = migrate(expect, sp, job or "JOB", source_host, source_web, src_tenant, capture_imgs)
    payload = {"_comment": "old-src -> new build-site URL. Build step rewrites <img src> with _map.",
               "job": job, "sourceUrl": source_web,
               "buildSite": "https://%s%s" % (build_host, build_path),
               "_map": url_map, "_details": details}
    json.dump(payload, open(out, "w"), indent=2, ensure_ascii=False)
    ok = sum(1 for d in details if d["status"] in ("uploaded", "reused"))
    print("[img-migrate] %d/%d image(s) migrated -> %s (%s)"
          % (ok, total, out, "; ".join("%s:%s" % (d["filename"], d["status"]) for d in details)))


if __name__ == "__main__":
    main()
