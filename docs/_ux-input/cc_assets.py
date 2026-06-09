#!/usr/bin/env python3
"""cc-assets <JOB####> [--dry] — populate a client job's images so they actually render (BL-011).

Two failures this fixes:
  (a) client's Tally upload was a private, expiring, &amp;-corrupted URL -> never loaded;
  (b) Pexels was never fetched for client jobs at all.

What it does:
  1. Downloads each client Tally upload (un-escapes &amp;) to a stable PUBLIC, self-hosted URL.
  2. Fetches relevant Pexels photos (query built from the brief) to top up to a sensible count.
  3. Saves them to /srv/projects/<JOB>/assets/ (local, inside the build workspace).
  4. Rewrites the manifest images[] with RELATIVE paths (assets/img-0N.jpg) so the built site bundles its
     own images (self-contained — no dependency on our infra). Client uploads first (hero), Pexels gallery.
cc-deploy copies these into the deploy + the source zip, so the live site AND the client's code are portable.
All HTTP uses a browser User-Agent (Pexels/Tally sit behind Cloudflare, which 1010-blocks Python-urllib).
"""
import sys, os, json, re, shutil, mimetypes
import urllib.request as U
from urllib.parse import urlparse

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
STOP = set("the a an and or of for to in on with your you we our this that need page site website "
           "email edm single multi multipage business company brand main message copy body".split())


def secret(n):
    for l in open("/root/.openclaw/secrets/cc-secrets.env"):
        l = l.strip()
        if l.startswith("export "):
            l = l[7:]
        if l.startswith(n + "="):
            return l.split("=", 1)[1].strip()
    return ""


def get(url, headers=None, timeout=25):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    return U.urlopen(U.Request(url, headers=h), timeout=timeout).read()


def ext_for(url, data=None):
    p = urlparse(url).path.lower()
    for e in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if p.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    return ".jpg"


def keywords(brief):
    txt = " ".join(str(s.get("headline", "") + " " + s.get("body", "")) for s in brief.get("sections", []))
    txt += " " + " ".join(brief.get("moods", []))
    words, seen = [], set()
    for w in re.findall(r"[a-zA-Z]{4,}", txt.lower()):
        if w in STOP or w in seen:
            continue
        seen.add(w); words.append(w)
        if len(words) >= 4:
            break
    return " ".join(words) if words else "modern professional business"


def pexels(query, n):
    if n <= 0:
        return []
    key = secret("PEXELS_API_KEY")
    url = "https://api.pexels.com/v1/search?query=%s&per_page=%d&orientation=landscape" % (
        U.quote(query), n)
    try:
        d = json.loads(get(url, headers={"Authorization": key}))
        return [p["src"]["large"] for p in d.get("photos", [])][:n]
    except Exception as e:
        print("  [pexels] WARN:", str(e)[:120]); return []


def save(url, dest, headers=None):
    data = get(url, headers=headers)
    open(dest, "wb").write(data)
    return len(data)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    job = args[0]
    proj = "/srv/projects/%s" % job
    man_path = "%s/discovery/manifest-assembler/output/asset-manifest.json" % proj
    if not os.path.exists(man_path):
        print("[assets] no manifest at", man_path); sys.exit(2)
    brief = json.load(open(proj + "/brief.json"))
    manifest = json.load(open(man_path))
    paid = int(brief.get("pages") or 1)
    client_urls = [u.replace("&amp;", "&") for u in brief.get("imageUrls", [])]
    target = max(3, paid + 1)                      # hero + a few gallery
    need_pexels = max(0, target - len(client_urls))
    query = keywords(brief)
    print("[assets]%s %s | client uploads=%d | pexels needed=%d | query=%r" %
          (" DRY" if dry else "", job, len(client_urls), need_pexels, query))
    if dry:
        print("  would download %d images to %s/assets and set RELATIVE manifest paths (assets/img-NN)" %
              (target, proj))
        return

    loc = "%s/assets" % proj
    shutil.rmtree(loc, ignore_errors=True); os.makedirs(loc, exist_ok=True)
    images, idx = [], 0

    def add(src_url, use, headers=None):
        nonlocal idx
        idx += 1
        fn = "img-%02d%s" % (idx, ext_for(src_url))
        dest = os.path.join(loc, fn)
        try:
            n = save(src_url, dest, headers=headers)
        except Exception as e:
            print("  download FAIL (%s): %s" % (fn, str(e)[:90])); return
        rel = "assets/" + fn   # relative path -> site bundles its own images (self-contained)
        images.append({"id": "img-%02d" % idx, "filename": fn, "path": rel, "sourceUrl": rel,
                       "localPath": dest, "suggestedUse": use, "description": ""})
        print("  +%s (%s, %d bytes) -> %s" % (fn, use, n, rel))

    for i, cu in enumerate(client_urls):
        add(cu, "hero" if i == 0 else "gallery")
    for j, pu in enumerate(pexels(query, need_pexels)):
        add(pu, "hero" if not images else "gallery")

    if not images:
        print("[assets] WARN: no images could be sourced — leaving manifest unchanged"); sys.exit(1)
    manifest["images"] = images
    json.dump(manifest, open(man_path, "w"), indent=2)
    print("[assets] done: %d images wired into manifest (%d client + %d pexels)" %
          (len(images), min(len(client_urls), len(images)), max(0, len(images) - len(client_urls))))


if __name__ == "__main__":
    main()
