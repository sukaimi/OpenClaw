#!/usr/bin/env python3
"""cc-closeout <JOB####> [--dry] — Phase 3 end-of-engagement wind-down for a DELIVERED client job.

Locked flow (project_web_edm_delivery_line): hand client the bundle -> take the site down ->
archive (3 months) -> triggers: feedback email to client + case-study ping to Sukaimi.

Steps:
  1. Guard: job must be delivered (card Closed). Refuse otherwise (unless --force).
  2. Bundle the source (zip) -> /srv/cc-archive/<JOB>/<JOB>-site.zip
  3. Email the client from hello@ with the bundle attached + a feedback ask (the 'hand bundle' + 'feedback' triggers in one mail).
  4. Take the hosted preview DOWN: `vercel remove cc-<job>`.
  5. Archive brief + manifest + bundle + deploy-url into /srv/cc-archive/<JOB>/ and stamp archived.json (purgeAfter = +90d). cc-archive-purge enforces retention.
  6. Ping Sukaimi (Telegram+Teams): closed out + make a case study.
  7. Annotate the card; write .closedout to prevent re-runs.
--dry prints what it WOULD do; sends/removes/writes nothing irreversible."""
import sys, os, json, time, base64, zipfile, shutil, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)
ARCHIVE = "/srv/cc-archive"
RETAIN_DAYS = 90
FROM = "hello@codeandcraft.ai"


def secret(n):
    for l in open("/root/.openclaw/secrets/cc-secrets.env"):
        l = l.strip()
        if l.startswith("export "):
            l = l[7:]
        if l.startswith(n + "="):
            return l.split("=", 1)[1].strip()
    return ""


def card(job):
    r = requests.get(BASE + "/items?expand=fields&top=400",
                     headers={"Authorization": "Bearer " + graph_token()})
    for it in r.json().get("value", []):
        if (it.get("fields") or {}).get("ProjectNo") == job:
            return it["id"], (it.get("fields") or {}).get("Stage")
    return None, None


def patch_notes(item, note):
    requests.patch(BASE + "/items/%s/fields" % item,
                   headers={"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"},
                   data=json.dumps({"Notes": note[:480]}))


def email_bundle(to, name, zippath, had_site):
    data = base64.b64encode(open(zippath, "rb").read()).decode()
    inner = ("<div style='font-family:system-ui,Segoe UI,Arial;max-width:520px;color:#1a202c'>"
             "<p>Hi %s,</p><p>Thanks for working with Code&Craft. As we wrap up, your site's full "
             "source code is <b>attached</b> — it's yours to host anywhere.</p>"
             "%s"
             "<p>We'd love <b>30 seconds of feedback</b> — just reply to this email.</p>"
             "<p style='color:#718096;font-size:13px;margin-top:24px'>— Code&Craft</p></div>"
             % (name,
                "<p>Our hosted preview will be taken offline shortly; use the attached files going forward.</p>"
                if had_site else ""))
    body = {"message": {"subject": "Your Code&Craft project — files + a quick favour",
                        "body": {"contentType": "HTML", "content": inner},
                        "toRecipients": [{"emailAddress": {"address": to}}],
                        "attachments": [{"@odata.type": "#microsoft.graph.fileAttachment",
                                         "name": os.path.basename(zippath),
                                         "contentType": "application/zip", "contentBytes": data}]},
            "saveToSentItems": True}
    r = requests.post("https://graph.microsoft.com/v1.0/users/%s/sendMail" % FROM,
                      headers={"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"},
                      data=json.dumps(body))
    return r.status_code


def ping(msg):
    try:
        subprocess.run(["cc-notify-operator", msg], timeout=60)
    except Exception:
        pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    force = "--force" in sys.argv
    if not args:
        print(__doc__); sys.exit(1)
    job = args[0]
    proj = "/srv/projects/%s" % job
    if not os.path.exists(proj + "/brief.json"):
        print("[closeout] %s not a client job (no brief.json)" % job); sys.exit(2)
    if os.path.exists(proj + "/.closedout") and not force:
        print("[closeout] %s already closed out (use --force to repeat)" % job); sys.exit(0)
    brief = json.load(open(proj + "/brief.json"))
    to = brief.get("clientEmail", "")
    name = brief.get("clientName") or brief.get("brand") or "there"

    item, stage = card(job)
    if stage != "Closed" and not force:
        print("[closeout] %s card stage is %r, not Closed — deliver first (or --force)" % (job, stage)); sys.exit(3)

    # locate source to bundle
    src = None
    for c in ("build/static-web/output", "build/static-web", "build/edm/output", "build/edm", "site"):
        p = os.path.join(proj, c)
        if os.path.isdir(p) and os.listdir(p):
            src = p; break
    adir = "%s/%s" % (ARCHIVE, job)
    zippath = "%s/%s-site.zip" % (adir, job)
    url = open(proj + "/deploy-url.txt").read().strip() if os.path.exists(proj + "/deploy-url.txt") else ""
    slug = ("cc-" + job).lower()

    print("[closeout]%s %s | client=%s | src=%s | url=%s" % (" DRY" if dry else "", job, to, src, url or "-"))
    if dry:
        print("  would: zip %s -> %s; email bundle+feedback to %s; vercel remove %s; archive+stamp; ping Sukaimi; annotate card %s"
              % (src, zippath, to or "(none)", slug, item))
        return

    os.makedirs(adir, exist_ok=True)
    # 2. bundle
    if src:
        with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _d, files in os.walk(src):
                for f in files:
                    fp = os.path.join(root, f)
                    z.write(fp, os.path.relpath(fp, src))
        print("  bundled:", zippath, "(%d bytes)" % os.path.getsize(zippath))
    else:
        print("  WARN no source dir found — skipping bundle")

    # 3. hand bundle + feedback to client
    if to and src:
        print("  client email:", email_bundle(to, name, zippath, bool(url)), "(<300=sent)")
    elif not to:
        print("  no client email on brief — skipped client mail")

    # 4. takedown
    env = os.environ.copy(); env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    rm = subprocess.run(["vercel", "remove", slug, "--yes", "--token", secret("VERCEL_TOKEN"),
                         "--scope", "sukaimis-projects"], env=env, capture_output=True, text=True, timeout=180)
    took_down = rm.returncode == 0
    print("  takedown:", "removed " + slug if took_down else "WARN " + (rm.stderr or rm.stdout)[-160:])

    # 5. archive artifacts + stamp
    for fn in ("brief.json", "discovery/manifest-assembler/output/asset-manifest.json", "deploy-url.txt", ".verified"):
        sp = os.path.join(proj, fn)
        if os.path.exists(sp):
            shutil.copy(sp, os.path.join(adir, os.path.basename(fn)))
    now = time.time()
    json.dump({"job": job, "clientEmail": to, "url": url, "tookDown": took_down,
               "archivedAt": now, "purgeAfter": now + RETAIN_DAYS * 86400,
               "retainDays": RETAIN_DAYS}, open(adir + "/archived.json", "w"), indent=2)
    print("  archived ->", adir, "| purge after", RETAIN_DAYS, "days")

    # 6. case-study trigger
    ping("📸 %s closed out — bundle sent to %s, site %s, archived (purge +%dd). Make a case study? Source: %s"
         % (job, to or "(no email)", "taken down" if took_down else "takedown FAILED", RETAIN_DAYS, adir))

    # 7. log to durable registry + REMOVE the card from the live board (best practice: Closed -> logged -> removed)
    reg = "%s/REGISTRY.md" % ARCHIVE
    if not os.path.exists(reg):
        open(reg, "w").write("# Code&Craft — Job Registry (archived / closed-out)\n\n"
                             "Durable ledger of completed jobs removed from the live Kanban.\n\n"
                             "| Job | Date | Type | Client | Detail |\n|---|---|---|---|---|\n")
    open(reg, "a").write("| %s | %s | %s | %s | %sp, %s%s |\n" % (
        job, time.strftime("%Y-%m-%d"), brief.get("type", "?"), to or "-", brief.get("pages", "?"),
        url or "(edm)", "" if took_down else " [TAKEDOWN FAILED]"))
    if item:
        try:
            requests.delete(BASE + "/items/%s" % item,
                            headers={"Authorization": "Bearer " + graph_token()})
            print("  card removed from board -> logged in REGISTRY.md")
        except Exception as e:
            print("  card remove WARN:", str(e)[:90])
    open(proj + "/.closedout", "w").write(str(now))
    print("[closeout] done:", job)


if __name__ == "__main__":
    main()
