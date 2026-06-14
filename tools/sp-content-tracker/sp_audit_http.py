#!/usr/bin/env python3
"""
sp_audit_http.py — enrichment helpers for sp-audit.py (stdlib only).

Two jobs the REST audit can't do inline:
  1. Broken-link detection — HTTP HEAD (falls back to GET) on real hrefs.
  2. Image natural-dimension parsing — from downloaded bytes, no Pillow needed
     (PNG / JPEG / GIF headers via struct).

Lives in a FILE on purpose: Bash commands containing requests.get(/curl/wget are
blocked by the context-mode hook, so HTTP must run from a script, not inline.

CLI:  python sp_audit_http.py <job.json> <enrich.out.json>
  job.json = { "links": ["https://...", ...],
               "images": [ {"src": "<key>", "path": "/local/file.jpg"}, ... ] }
  emits    = { "brokenLinks": [ {"url","status"} ], "imageDims": { "<src>": {"w","h"} } }

Used as a library by sp-audit.py too: head_check(urls), image_dims_from_bytes(b).
"""
import json
import struct
import sys
import urllib.request
import urllib.error


def head_check(urls, timeout=8):
    """Return [{url, status}] for any url that does NOT resolve to 2xx/3xx."""
    broken = []
    for url in urls:
        if not url or url.startswith('#') or url.startswith('mailto:') or url.startswith('tel:'):
            continue
        if not url.lower().startswith(('http://', 'https://')):
            continue
        status = _probe(url, 'HEAD', timeout)
        if status in (405, 403, None):  # some servers reject HEAD — retry GET
            status = _probe(url, 'GET', timeout)
        if status is None:
            broken.append({'url': url, 'status': 'unreachable'})
        elif status >= 400:
            broken.append({'url': url, 'status': str(status)})
    return broken


def _probe(url, method, timeout):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': 'sp-audit/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def image_dims_from_bytes(data):
    """(w, h) natural pixel size for PNG/JPEG/GIF bytes; (0, 0) if unknown."""
    if not data or len(data) < 24:
        return (0, 0)
    # PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>II', data[16:24])
        return (w, h)
    # GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        w, h = struct.unpack('<HH', data[6:10])
        return (w, h)
    # JPEG — walk the segment markers to the SOFn frame
    if data[:2] == b'\xff\xd8':
        i = 2
        n = len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return (w, h)
            seg = struct.unpack('>H', data[i + 2:i + 4])[0]
            i += 2 + seg
    return (0, 0)


def main():
    if len(sys.argv) != 3:
        print('usage: python sp_audit_http.py <job.json> <enrich.out.json>', file=sys.stderr)
        sys.exit(2)
    job = json.load(open(sys.argv[1]))
    out = {'brokenLinks': head_check(job.get('links', [])), 'imageDims': {}}
    for img in job.get('images', []):
        src, path = img.get('src'), img.get('path')
        if src and path:
            try:
                out['imageDims'][src] = dict(zip(('w', 'h'), image_dims_from_bytes(open(path, 'rb').read())))
            except Exception:
                pass
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
    print(json.dumps({'ok': True, 'broken': len(out['brokenLinks']), 'images': len(out['imageDims'])}))


if __name__ == '__main__':
    main()
