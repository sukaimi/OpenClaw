#!/usr/bin/env python3
"""cc-build <JOB####> — build a client job from its manifest, deploy (web) or render (EDM),
then email the client the result. Reuses the proven JOB0003 engine builders."""
import sys, os, json, subprocess, re
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

ENGINE = "/srv/projects/JOB0003"


def secret(n):
    for l in open("/root/.openclaw/secrets/cc-secrets.env"):
        l = l.strip()
        if l.startswith("export "):
            l = l[7:]
        if l.startswith(n + "="):
            return l.split("=", 1)[1].strip()
    return ""


def sh(cmd, cwd=None, env=None, t=420):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=t)


def email_client(to, name, subject, inner):
    body = {"message": {"subject": subject,
                        "body": {"contentType": "HTML",
                                 "content": "<div style='font-family:system-ui,Segoe UI,Arial;max-width:520px'>%s<p style='color:#718096;font-size:13px'>— Code&Craft</p></div>" % inner},
                        "toRecipients": [{"emailAddress": {"address": to}}]}, "saveToSentItems": True}
    requests.post("https://graph.microsoft.com/v1.0/users/hello@codeandcraft.ai/sendMail",
                  headers={"Authorization": "Bearer " + graph_token(), "Content-Type": "application/json"},
                  data=json.dumps(body))


def main():
    job = sys.argv[1]
    proj = "/srv/projects/%s" % job
    man = "%s/discovery/manifest-assembler/output/asset-manifest.json" % proj
    m = json.load(open(man))
    to = (m.get("metadata") or {}).get("clientEmail") or ""
    name = m.get("title") or "there"
    typ = m.get("subtype") or "multipage_site"
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    env["VERCEL_TOKEN"] = secret("VERCEL_TOKEN")
    print("[cc-build] %s type=%s client=%s" % (job, typ, to))

    if typ == "edm":
        r = sh(["tsx", "run.ts", "--manifest", man], cwd=ENGINE + "/build/edm", env=env)
        ok = os.path.exists(ENGINE + "/build/edm/output/email.html")
        print("[cc-build] EDM built:", ok, r.stderr[-200:] if not ok else "")
        if ok:
            email_client(to, name, "Your Code&Craft email design is ready",
                         "<p>Hi %s,</p><p>Your email design (EDM) is ready — we'll send the final HTML + preview shortly.</p>" % name)
        return

    r = sh(["tsx", "run.ts", "--manifest", man], cwd=ENGINE + "/build/static-web", env=env)
    out = ENGINE + "/build/static-web/output"
    if not os.path.exists(out + "/index.html"):
        print("[cc-build] BUILD FAILED:", (r.stderr or r.stdout)[-300:]); sys.exit(1)
    print("[cc-build] built index.html")
    d = sh(["vercel", "deploy", "--prod", "--yes", "--token", env["VERCEL_TOKEN"],
            "--scope", "sukaimis-projects"], cwd=out, env=env)
    dep = [x for x in d.stdout.strip().splitlines() if x.startswith("https://")]
    dep = dep[-1] if dep else ""
    am = re.search(r"Aliased\s+(https://[a-z0-9-]+\.vercel\.app)", d.stderr or "")
    url = am.group(1) if am else dep   # PUBLIC production alias preferred (deployment URL is 401-protected)
    print("[cc-build] deployed:", url or ("FAILED " + (d.stderr or "")[-200:]))
    if url:
        # save the canonical URL on the job + email client
        open("%s/deploy-url.txt" % proj, "w").write(url)
        email_client(to, name, "Your Code&Craft site is ready 🎉",
                     "<p>Hi %s,</p><p>Your site is live:</p><p><a href='%s' style='background:#1a202c;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none'>View your site</a></p><p>%s</p>" % (name, url, url))
        print("[cc-build] client emailed the live URL")


if __name__ == "__main__":
    main()
