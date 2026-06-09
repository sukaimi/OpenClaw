#!/usr/bin/env python3
"""cc-verify — deterministic acceptance check for a JOB0003 card.
Usage: verify.py <cardId> [projectRoot]
Prints "PASS <id> — <reason>" or "FAIL <id> — <reason>". Exit 0 = pass, 1 = fail, 2 = unknown card.
The agent CANNOT close a card; only a PASS here promotes Internal QA -> Closed.
"""
import sys, os, json, glob, re

ROOT = sys.argv[2] if len(sys.argv) > 2 else "/srv/projects/JOB0003"


def _read(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


def _glob1(pat):
    m = glob.glob(os.path.join(ROOT, pat), recursive=True)
    return m[0] if m else None


def _valid_json(p):
    try:
        return bool(json.load(open(p, encoding="utf-8"))) or True
    except Exception:
        return False


def c29():
    a = _glob1("**/intake-schema.json"); b = _glob1("**/type-taxonomy.json")
    if a and b and _valid_json(a) and _valid_json(b):
        return True, "intake-schema.json + type-taxonomy.json present and valid JSON"
    return False, "missing or invalid schema/taxonomy JSON"


def c30():
    r = _glob1("**/router*.ts") or _glob1("**/*router*.ts")
    rec = _glob1("**/intake-record.json")
    if r and os.path.getsize(r) > 2000 and rec and _valid_json(rec):
        return True, "router.ts (substantial) + a valid classified intake-record.json"
    return False, "no substantial router.ts or no valid classified output record"


def c31():
    outs = glob.glob(os.path.join(ROOT, "discovery/vision-pass/output/*.vision.json"))
    if not outs:
        return False, "no vision output produced"
    # Unambiguous fake-tell: the 'analysis' is of fictional images (example.com / placeholder).
    if any(re.search(r"example\.com|/placeholder", _read(p), re.I) for p in outs):
        return False, "vision 'analyzed' fictional example.com images — not a real analysis"
    tsfiles = glob.glob(os.path.join(ROOT, "discovery/vision-pass/**/*.ts"), recursive=True)
    code = " ".join(_read(p) for p in tsfiles)
    # Require an ACTUAL model API call, not a keyword in a comment.
    real_call = re.search(r"fetch\(|axios|googleapis|generativelanguage|api\.anthropic|api\.openai", code, re.I)
    uses_mock = re.search(r"new\s+MockImageAnalyzer|MockImageAnalyzer\(", code)
    if uses_mock and not real_call:
        return False, "vision uses MockImageAnalyzer with no real model API call"
    if real_call:
        return True, "vision invokes a real image-model API on real images"
    return False, "no real vision model invocation found"


def c32():
    p = _glob1("**/copy-manifest.json")
    if p and _valid_json(p) and ("segment" in _read(p).lower() or "section" in _read(p).lower()):
        return True, "copy-manifest.json valid with parsed segments"
    return False, "missing/invalid copy-manifest.json"


def c33():
    p = _glob1("**/asset-manifest.json")
    if p and _valid_json(p):
        try:
            d = json.load(open(p))
            if isinstance(d, dict) and len(d) >= 4:
                return True, "asset-manifest.json valid with %d keys" % len(d)
        except Exception:
            pass
    return False, "missing/invalid/thin asset-manifest.json"


def c34():
    p = _glob1("**/pexels*assets*.json") or _glob1("assets/pexels/output/*.json")
    if not p:
        return False, "no Pexels output file produced (card closed with nothing)"
    body = _read(p)
    if re.search(r"pexels\.com|images\.pexels", body, re.I):
        return True, "Pexels output contains real pexels.com photo URLs"
    return False, "Pexels output exists but has no real pexels.com URLs"


def c36():
    p = _glob1("build/static-web/output/index.html") or _glob1("**/static-web/**/index.html")
    if not p:
        return False, "no static-web index.html"
    html = _read(p)
    lines = html.count("\n")
    tags = len(re.findall(r"<(div|section|header|footer|h1|h2|h3|p|a|img|ul|li|nav|main)\b", html, re.I))
    if "lorem ipsum" in html.lower():
        return False, "index.html contains lorem-ipsum filler"
    if lines >= 80 and tags >= 30:
        return True, "index.html real markup: %d lines, %d structural tags, no lorem filler" % (lines, tags)
    return False, "index.html too thin: %d lines, %d tags" % (lines, tags)


def c37():
    p = _glob1("build/edm/output/email.html") or _glob1("**/edm/**/email.html")
    if not p:
        return False, "no EDM email.html"
    html = _read(p)
    tables = html.lower().count("<table")
    inline = len(re.findall(r"style=", html, re.I))
    scripts = html.lower().count("<script")
    if tables >= 3 and inline >= 10 and scripts == 0:
        return True, "email.html: %d tables, %d inline styles, 0 scripts (email-safe)" % (tables, inline)
    return False, "email.html not email-safe: tables=%d inline=%d scripts=%d" % (tables, inline, scripts)


def c38():
    f = _glob1("**/deploy-result.json") or _glob1("**/deploy*url*")
    body = _read(f) if f else ""
    urls = [u for u in re.findall(r"https://[a-z0-9-]+\.vercel\.app", body)]
    if not urls or "REPLACE_WITH" in body:
        return False, "no real deploy URL recorded (placeholders / never deployed)"
    import urllib.request
    last = None
    for url in urls:
        try:
            code = urllib.request.urlopen(url, timeout=12).status
        except Exception as e:
            last = "%s -> %s" % (url, str(e)[:40]); continue
        if code == 200:
            return True, "live deploy verified: %s returns 200" % url
        last = "%s -> HTTP %s" % (url, code)
    return False, "no recorded deploy URL returns 200 (%s)" % last


def c39():
    img = _glob1("**/edm/**/preview.*") or _glob1("**/deploy/edm/output/preview.*")
    if not img:
        return False, "no EDM preview image"
    sz = os.path.getsize(img)
    if sz < 4000:
        return False, "preview image is a %d-byte placeholder, not a real screenshot" % sz
    return True, "real preview image (%d bytes)" % sz


def c40():
    p = _glob1("**/e2e-result*.json")
    if not p:
        return False, "no e2e-results.json"
    try:
        d = json.load(open(p))
    except Exception:
        return False, "e2e-results.json invalid"
    summ = d.get("summary", {}) or {}
    result = str(summ.get("result", "")).upper()
    failed = summ.get("failed", 1)
    web = _glob1("build/static-web/output/index.html"); edm = _glob1("build/edm/output/email.html")
    if result == "PASS" and failed == 0 and web and edm:
        return True, "e2e gate PASS (0 failures) + real web build + real EDM present"
    return False, "e2e result=%s, failed=%s (or missing artifacts)" % (result or "?", failed)


CHECKS = {29: c29, 30: c30, 31: c31, 32: c32, 33: c33, 34: c34,
          36: c36, 37: c37, 38: c38, 39: c39, 40: c40}


def main():
    cid = int(sys.argv[1])
    fn = CHECKS.get(cid)
    if not fn:
        print("UNKNOWN %d — no check defined" % cid); sys.exit(2)
    ok, reason = fn()
    print(("PASS " if ok else "FAIL ") + str(cid) + " — " + reason)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
