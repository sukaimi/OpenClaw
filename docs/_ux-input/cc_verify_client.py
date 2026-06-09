#!/usr/bin/env python3
"""cc-verify-client <JOB####> — DETERMINISTIC delivery gate for a CLIENT job (BL-001).

The agent CANNOT self-close a client card; only a PASS here may. Checks the live, per-job deploy
(BL-002 gives each job its own URL so this can't be fooled by a shared alias):
  - homepage returns 200
  - real page count >= paid pages (crawls homepage nav, canonicalises, counts 200 pages w/ content)
  - no lorem/placeholder text
  - hero image loads (200)
EDM jobs are checked file-based (rendered email html exists, has content, no placeholder).

On PASS  -> write /srv/projects/<JOB>/.verified, email client (delivered), move card Closed, ping op.
On FAIL  -> remove marker, bounce card to Build (BLOCKED note on 2nd fail), ping op with the reasons;
            client is NOT emailed. Exit code: 0 PASS, 1 FAIL.
The .verified marker is also enforced by cc-board (it refuses to close a client card without it)."""
import sys, os, json, re, time, subprocess, base64, zipfile
from urllib.parse import urljoin, urlparse
import urllib.request as U
sys.path.insert(0, "/root/.openclaw/sp-provision")
import requests
from spclient import graph_token

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)


def fetch(url):
    try:
        r = U.urlopen(url, timeout=20)
        return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:
        return getattr(e, "code", 0), ""


def canon(u):
    p = urlparse(u)
    path = p.path
    if path.endswith("/index.html"):
        path = path[:-10]
    path = path.rstrip("/")
    return "%s://%s%s" % (p.scheme, p.netloc, path)


def card_id(job):
    r = requests.get(BASE + "/items?expand=fields&top=400",
                     headers={"Authorization": "Bearer " + graph_token()})
    for it in r.json().get("value", []):
        if (it.get("fields") or {}).get("ProjectNo") == job:
            return it["id"]
    return None


def move(item, stage, note):
    if not item:
        return
    requests.patch(BASE + "/items/%s/fields" % item,
                   headers={"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"},
                   data=json.dumps({"Stage": stage, "Notes": note[:480]}))


def ping(msg):
    try:
        subprocess.run(["cc-notify-operator", msg], timeout=60)
    except Exception:
        pass


def zip_source(proj, job, typ):
    cands = ("build/edm/output", "build/edm") if typ == "edm" else ("build/static-web/output", "build/static-web")
    src = next((os.path.join(proj, c) for c in cands
               if os.path.isdir(os.path.join(proj, c)) and os.listdir(os.path.join(proj, c))), None)
    if not src:
        return None
    zp = os.path.join(proj, "%s-source.zip" % job)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _d, files in os.walk(src):
            for f in files:
                fp = os.path.join(root, f)
                z.write(fp, os.path.relpath(fp, src))
    return zp


def deliver(to, name, url, job, proj, typ):
    """Delivery email from hello@ — live URL (web) + the source-code bundle attached."""
    zp = zip_source(proj, job, typ)
    if typ == "edm":
        subj = "Your email design is ready"
        link = ("<p>Preview it here:</p><p><a href='%s'>%s</a></p>" % (url, url)) if url else ""
        inner = ("<p>Hi %s,</p><p>Your email design is <b>ready</b>.</p>%s"
                 "<p>The <b>HTML source is attached</b>. When you send it from your email tool, re-host the "
                 "images on your own server/CDN — the preview hosts them just for viewing.</p>" % (name, link))
    elif url:
        subj = "Your project is ready 🎉"
        inner = ("<p>Hi %s,</p><p>Your site is <b>ready</b> and live:</p>"
                 "<p><a href='%s'>%s</a></p>"
                 "<p>Your full <b>source code is attached</b> as a zip — it's yours to keep. "
                 "Have a look and tell us what you think.</p>" % (name, url, url))
    else:
        subj = "Your project is ready"
        inner = ("<p>Hi %s,</p><p>Your project is <b>ready</b> — the source is <b>attached</b>.</p>" % name)
    msg = {"message": {"subject": subj,
                       "body": {"contentType": "HTML",
                                "content": "<div style='font-family:system-ui,Segoe UI,Arial;max-width:520px;color:#1a202c'>%s"
                                           "<p style='color:#718096;font-size:13px;margin-top:24px'>— Code&Craft</p></div>" % inner},
                       "toRecipients": [{"emailAddress": {"address": to}}]},
           "saveToSentItems": True}
    if zp:
        msg["message"]["attachments"] = [{"@odata.type": "#microsoft.graph.fileAttachment",
                                          "name": os.path.basename(zp), "contentType": "application/zip",
                                          "contentBytes": base64.b64encode(open(zp, "rb").read()).decode()}]
    r = requests.post("https://graph.microsoft.com/v1.0/users/hello@codeandcraft.ai/sendMail",
                      headers={"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"},
                      data=json.dumps(msg))
    return r.status_code, bool(zp)


def check_web(proj, paid):
    fails = []
    dpath = proj + "/deploy-url.txt"
    if not os.path.exists(dpath):
        return "", ["no deploy-url.txt — not deployed (run cc-deploy)"]
    url = open(dpath).read().strip()
    st, home = fetch(url)
    if st != 200:
        return url, ["homepage not 200 (got %s) at %s" % (st, url)]
    ASSET = (".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico",
             ".pdf", ".zip", ".woff", ".woff2", ".ttf", ".mp4", ".json", ".xml", ".txt")
    links = {"/"}
    for m in re.findall(r'href="([^"]+)"', home):
        m = m.split("#")[0].strip()
        if not m or m[:4] == "http" or m.startswith(("mailto:", "tel:", "data:", "javascript:")):
            continue
        if m.lower().endswith(ASSET):
            continue
        links.add(m)   # count ANY internal route — clean URLs (/about), .html, or subdir/
    seen, ok_pages = set(), 0
    for l in links:
        full = canon(urljoin(url + "/", l.lstrip("/")))
        if full in seen:
            continue
        seen.add(full)
        s, b = fetch(full if full else url)
        if s == 200 and len(b) > 300 and any(t in b.lower() for t in ("<html", "<body", "<div", "<table")):
            ok_pages += 1
    if ok_pages < paid:
        fails.append("page count %d < paid %d" % (ok_pages, paid))
    if "lorem ipsum" in home.lower() or "placeholder text" in home.lower():
        fails.append("placeholder/lorem text on homepage")
    im = re.search(r'<img[^>]+src="([^"]+)"', home)
    if im:
        isrc = im.group(1) if im.group(1).startswith("http") else urljoin(url + "/", im.group(1))
        if not isrc.startswith("data:"):
            s, _ = fetch(isrc)
            if s != 200:
                fails.append("hero image not loading (got %s)" % s)
    return url, fails


def check_edm(proj):
    for c in (proj + "/build/edm/output/email.html",
              "/srv/projects/JOB0003/build/edm/output/email.html"):
        if os.path.exists(c):
            html = open(c, encoding="utf-8", errors="ignore").read()
            f = []
            if len(html) < 500:
                f.append("EDM html too small")
            if "lorem ipsum" in html.lower() or "placeholder text" in html.lower():
                f.append("EDM contains placeholder/lorem")
            return "", f
    return "", ["EDM html not found"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check-only" in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    job = args[0]
    proj = "/srv/projects/%s" % job
    if not os.path.exists(proj + "/brief.json"):
        print("[verify] %s is not a client job (no brief.json)" % job); sys.exit(2)
    brief = json.load(open(proj + "/brief.json"))
    paid = int(brief.get("pages") or 1)
    typ = brief.get("type", "multipage_site")
    to = brief.get("clientEmail", "")
    name = brief.get("clientName") or brief.get("brand") or "there"

    # EDM now deploys a browser preview (3A), so verify it like a single deployed page.
    url, fails = check_web(proj, 1 if typ == "edm" else paid)

    if check_only:
        print(("FAIL: " + "; ".join(fails)) if fails else ("PASS: " + (url or "edm")))
        sys.exit(1 if fails else 0)

    item = card_id(job)

    if fails:
        try:
            os.remove(proj + "/.verified")
        except OSError:
            pass
        fc = proj + "/.failcount"
        n = (int(open(fc).read()) if os.path.exists(fc) else 0) + 1
        open(fc, "w").write(str(n))
        note = ("BLOCKED: " if n >= 2 else "") + ("VERIFY FAIL #%d: " % n) + "; ".join(fails)
        move(item, "Build", note)
        ping("❌ %s verify FAIL #%d: %s" % (job, n, "; ".join(fails)))
        print("FAIL:", "; ".join(fails))
        sys.exit(1)

    json.dump({"job": job, "url": url, "paid": paid, "pages_ok": True, "ts": time.time()},
              open(proj + "/.verified", "w"))
    if to:
        try:
            code, hadzip = deliver(to, name, url, job, proj, typ)
            print("  delivered email %s | source attached: %s" % (code, hadzip))
        except Exception as e:
            print("  deliver WARN:", str(e)[:120])
    move(item, "Closed", "VERIFIED + delivered (with source): %s" % (url or "edm"))
    ping("✅ %s VERIFIED & delivered: %s" % (job, url or "(edm)"))
    print("PASS:", url or "edm")


if __name__ == "__main__":
    main()
