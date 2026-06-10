#!/usr/bin/env python3
"""cc-deploy <JOB####> — deploy a client job's built site to its OWN Vercel project (per-job
isolation, BL-002). Web only. Reads the build output under /srv/projects/<JOB>/build/static-web,
copies it into a uniquely-named folder (cc-<job>) so Vercel creates a DISTINCT project + public
alias per job (no more shared static-web-ashy that corrupts verification), captures the alias, and
writes /srv/projects/<JOB>/deploy-url.txt. Prints the live URL on the last line."""
import sys, os, re, json, glob, shutil, subprocess


def secret(n):
    for l in open("/root/.openclaw/secrets/cc-secrets.env"):
        l = l.strip()
        if l.startswith("export "):
            l = l[7:]
        if l.startswith(n + "="):
            return l.split("=", 1)[1].strip()
    return ""


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    job = sys.argv[1]
    proj = "/srv/projects/%s" % job
    try:
        is_edm = json.load(open(proj + "/brief.json")).get("type") == "edm"
    except Exception:
        is_edm = False
    # EDM is deployed as a browser PREVIEW of the email (served as index.html). 3A.
    # Be tolerant of WHERE the agent put the email — accept email.html or index.html, in the edm OR web dir.
    if is_edm:
        search = [("build/edm/output", "email.html"), ("build/edm", "email.html"),
                  ("build/edm/output", "index.html"), ("build/edm", "index.html"),
                  ("build/static-web/output", "index.html"), ("build/static-web", "index.html"),
                  ("build/static-web/output", "email.html"), ("build/static-web", "email.html")]
    else:
        # tolerate common output dirs the agent might use (NOT the project root — that holds client data)
        webdirs = ("build/static-web/output", "build/static-web", "build/web", "dist", "public", "www", "site", "output")
        search = [(c, "index.html") for c in webdirs]
    src = next((os.path.join(proj, d) for d, fn in search
               if os.path.exists(os.path.join(proj, d, fn))), None)
    if not src:
        print("[cc-deploy] no built %s under %s — build first" %
              ("email/index.html" if is_edm else "index.html", proj)); sys.exit(1)

    # BL-013: guarantee the site is SELF-CONTAINED — bundle the job's images into the build output's
    # assets/ (overwriting any placeholder the builder may have written), so the live site + the source
    # zip carry their own images and depend on no external host.
    job_assets = os.path.join(proj, "assets")
    if os.path.isdir(job_assets) and os.listdir(job_assets):
        dest_assets = os.path.join(src, "assets")
        os.makedirs(dest_assets, exist_ok=True)
        for f in glob.glob(job_assets + "/*"):
            if os.path.isfile(f):
                shutil.copy(f, os.path.join(dest_assets, os.path.basename(f)))
        print("[cc-deploy] bundled %d image(s) into %s/assets" % (len(os.listdir(job_assets)), src))

    slug = ("cc-" + job).lower()                 # deterministic per-job Vercel project name
    dep = os.path.join(proj, "deploy", slug)
    shutil.rmtree(dep, ignore_errors=True)
    os.makedirs(dep, exist_ok=True)
    for f in glob.glob(src + "/*"):
        if os.path.basename(f) == ".vercel":
            continue
        (shutil.copytree if os.path.isdir(f) else shutil.copy)(f, os.path.join(dep, os.path.basename(f)))

    # EDM: Vercel serves index.html at the root, so expose the email as the preview's index.
    if is_edm and not os.path.exists(os.path.join(dep, "index.html")):
        shutil.copy(os.path.join(dep, "email.html"), os.path.join(dep, "index.html"))

    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    tok = secret("VERCEL_TOKEN")
    print("[cc-deploy] %s -> project %s (source %s)" % (job, slug, src))
    d = subprocess.run(["vercel", "deploy", "--prod", "--yes", "--token", tok,
                        "--scope", "sukaimis-projects"], cwd=dep, env=env,
                       capture_output=True, text=True, timeout=420)
    am = re.search(r"Aliased\s+(https://[a-z0-9-]+\.vercel\.app)", d.stderr or "")
    std = [x for x in (d.stdout or "").splitlines() if x.startswith("https://")]
    url = am.group(1) if am else (std[-1] if std else "")
    if not url:
        print("[cc-deploy] DEPLOY FAILED:", (d.stderr or d.stdout)[-300:]); sys.exit(1)
    open(proj + "/deploy-url.txt", "w").write(url)
    print("[cc-deploy] live:", url)
    print(url)


if __name__ == "__main__":
    main()
