#!/usr/bin/env python3
"""cc-intake — turn a PAID + operator-approved client brief into a buildable client job.
Usage: cc-intake <brief.json> [--dry]
brief.json = {
  "type": "multipage_site|single_page|edm",
  "pages": 3,
  "clientName": "Acme", "clientEmail": "x@y.com", "brand": "Acme Corp",
  "sections": [{"type":"hero","headline":"...","body":"...","cta":"..."}],
  "imageUrls": ["https://...jpg"],
  "palette": ["#1a365d"], "moods": ["professional"]
}
Creates: a new JOB#### project dir + asset-manifest the engine can build, + a tracking card in Intake.
This is the POST-'go' action (the notify + 'go' checkpoint live in the operator-ping card).
"""
import sys, json, re, os
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)


def _h():
    return {"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"}


def next_job():
    # Monotonic numbering across ALL sources so pruning the board never reuses a number:
    # live board cards + /srv/projects dirs + the archived registry.
    mx = 0
    try:
        r = requests.get(BASE + "/items?expand=fields&top=400", headers={"Authorization": "Bearer " + graph_token()})
        for it in r.json().get("value", []):
            m = re.match(r"JOB(\d+)$", it.get("fields", {}).get("ProjectNo") or "")
            if m:
                mx = max(mx, int(m.group(1)))
    except Exception:
        pass
    for d in os.listdir("/srv/projects") if os.path.isdir("/srv/projects") else []:
        m = re.match(r"JOB(\d+)$", d)
        if m:
            mx = max(mx, int(m.group(1)))
    reg = "/srv/cc-archive/REGISTRY.md"
    if os.path.exists(reg):
        for m in re.findall(r"JOB(\d+)", open(reg).read()):
            mx = max(mx, int(m))
    return "JOB%04d" % (mx + 1)


def assemble_manifest(brief, job):
    is_web = brief.get("type") in ("multipage_site", "single_page")
    imgs = brief.get("imageUrls", [])
    return {
        "$schema": "../schemas/asset-manifest-schema.json",
        "manifestId": job, "briefId": job,
        "title": brief.get("brand") or brief.get("clientName") or job,
        "type": "web" if is_web else "edm",
        "subtype": {"multipage_site": "multipage", "single_page": "single", "edm": "edm"}.get(brief.get("type"), "multipage"),
        "deployTarget": "vercel" if is_web else None,
        "images": [{"id": "img-%03d" % (i + 1), "filename": "img-%03d.jpg" % (i + 1),
                    "path": u, "sourceUrl": u,
                    "suggestedUse": "hero" if i == 0 else "gallery",
                    "description": ""} for i, u in enumerate(imgs)],
        "copySegments": [{"type": s.get("type", "section"), "headline": s.get("headline", ""),
                          "body": s.get("body", ""), "cta": s.get("cta", "")}
                         for s in brief.get("sections", [])],
        "colorPalette": {"commonColors": brief.get("palette", ["#1a365d", "#2b6cb0", "#ffffff"])},
        "moodTone": {"dominantMoods": brief.get("moods", ["professional"])},
        "ctaUrl": brief.get("ctaUrl", ""),
        "metadata": {"source": "cc-intake", "clientName": brief.get("clientName"),
                     "clientEmail": brief.get("clientEmail"), "pages": brief.get("pages"),
                     "ctaUrl": brief.get("ctaUrl", "")},
    }


def create_card(job, brief):
    title = "%s · CLIENT %s — %s (%s, %sp)" % (
        job, brief.get("clientName", "?"), brief.get("brand", ""), brief.get("type"), brief.get("pages", "?"))
    notes = ("Client job from cc-intake (paid + 'go' approved). Client: %s <%s>. Type: %s, %s page(s). "
             "Brief + manifest in /srv/projects/%s. Build via engine -> deploy -> deliver -> close." % (
                 brief.get("clientName", "?"), brief.get("clientEmail", "?"),
                 brief.get("type"), brief.get("pages", "?"), job))
    body = {"fields": {"Title": title[:255], "Stage": "Intake", "Notes": notes, "ProjectNo": job}}
    r = requests.post(BASE + "/items", headers=_h(), data=json.dumps(body))
    return r.status_code < 300, r.status_code


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    brief = json.load(open(args[0]))
    job = next_job()
    manifest = assemble_manifest(brief, job)
    print("JOB:", job, "| type:", brief.get("type"), "| pages:", brief.get("pages"),
          "| images:", len(brief.get("imageUrls", [])), "| sections:", len(brief.get("sections", [])))
    if dry:
        print("DRY — manifest preview:")
        print(json.dumps({k: manifest[k] for k in ("title", "type", "subtype", "deployTarget")}, indent=1))
        print("DRY — %d images wired, %d copy segments. No project/card created." %
              (len(manifest["images"]), len(manifest["copySegments"])))
        return
    proj = "/srv/projects/%s" % job
    os.makedirs(proj + "/discovery/manifest-assembler/output", exist_ok=True)
    json.dump(brief, open(proj + "/brief.json", "w"), indent=2)
    json.dump(manifest, open(proj + "/discovery/manifest-assembler/output/asset-manifest.json", "w"), indent=2)
    ok, code = create_card(job, brief)
    print("project:", proj, "| brief+manifest saved | card:", "OK" if ok else "FAIL %s" % code)
    # BL-011: populate real, loading images (client uploads re-hosted + Pexels fills) into the manifest.
    import subprocess
    try:
        a = subprocess.run(["cc-assets", job], capture_output=True, text=True, timeout=200)
        print((a.stdout.strip()[-400:]) or ("cc-assets stderr: " + a.stderr.strip()[-200:]))
    except Exception as e:
        print("cc-assets WARN (images not populated):", str(e)[:120])
    print("NEXT: engine builds %s from its manifest -> deploy -> deliver to %s" % (job, brief.get("clientEmail")))


if __name__ == "__main__":
    main()
