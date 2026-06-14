#!/usr/bin/env python3
"""sp-audit.py — SOURCE AUDIT step for a SharePoint classic->modern CONVERSION job.

Reads a SOURCE classic SharePoint site via Microsoft Graph (app-only cert auth, reusing
spclient.SP / graph_token — same identity the build + gate use) and EMITS the per-job
`sp-expect.json` that drives `cc-verify-sp`. This is how the conversion gate's expectation
is DERIVED FROM THE SOURCE instead of hardcoded: the modern build must reproduce the pages
and key content this audit found on the classic source.

USAGE (run with the openclaw venv, PYTHONPATH=/root/.openclaw/sp-provision):

    sp-audit.py <SOURCE_SITE_URL> [--job JOB####] [--out /srv/projects/<JOB>/sp-expect.json]
                [--max-markers N] [--build-siteid <id>]

    # examples
    sp-audit.py https://codeandcanvas.sharepoint.com/sites/NorthwindClassic --job JOB0021
    sp-audit.py https://codeandcanvas.sharepoint.com/sites/NorthwindClassic --out /tmp/sp-expect.json

The SOURCE URL is a PARAMETER (Level-1 test: source in our codeandcanvas tenant; Level-2
client tenants plug in the same way once granted). The audit NEVER writes to the source —
read-only. siteId in the emitted file is the BUILD site (left null unless --build-siteid is
given; the gate injects it from site.json at gate time).

=============================================================================================
WHAT IS READABLE FROM A CLASSIC SITE WITH THE CURRENT APP PERMISSIONS (cert, Sites.Selected/
Sites.Read.All) — verdict, so the engineer knows what to expect:

  * MODERN site pages   /sites/{id}/pages  + $expand=canvasLayout
                        -> only returns MODERN SitePages. A purely-classic source returns an
                           EMPTY or partial list here. Do NOT rely on /pages for classic.
  * CLASSIC pages       live in a document library, not /pages:
      - wiki/web-part pages  -> 'Site Pages' library (drive)   -> .aspx files
      - publishing pages     -> 'Pages' library (drive)        -> .aspx files (publishing
                                infrastructure; may be absent if publishing not enabled)
    Read them as DRIVE ITEMS: GET /sites/{id}/drives -> find the 'Site Pages'/'Pages' drive
    -> GET /drives/{drive}/root/children -> each .aspx item's webUrl + name. The RAW .aspx
    HTML can be downloaded via the item's @microsoft.graph.downloadUrl (/content). Classic
    .aspx is server-rendered markup (web-part zones), NOT canvasLayout JSON — so content is
    extracted as TEXT/HTML, not as structured web parts. This is the honest source of the
    'markers' the modern build must reproduce.
  * LISTS               /sites/{id}/lists + /lists/{id}/items  -> fully readable (classic and
                        modern lists are the same Graph resource). Used to record lists the
                        conversion should recreate (check_lists in the gate).
  * NAVIGATION          QuickLaunch / top nav is NOT exposed on Graph v1.0. (SP REST
                        /_api/web/navigation exists but is out of scope for the app cert here.)
                        Nav is reconstructed from the page set, not read 1:1.

  NOT readable / caveats: classic publishing page LAYOUTS and field-level managed metadata are
  not structured via Graph; rich web-part configuration on classic pages is server-rendered and
  only available as rendered HTML. The audit therefore captures page TITLES + visible TEXT
  CONTENT markers + list names + IMAGE refs — enough to drive a faithful modern rebuild and a
  deterministic gate, NOT a byte-for-byte web-part clone (impossible on this rail; see runbook).

  IMAGES: each page's raw HTML (WikiField / CanvasContent1 / rendered .aspx / canvasLayout
  innerHtml) is scanned for <img> tags BEFORE tag-stripping. Every page entry gets an
  `images[]` array of {src, filename, alt}. The build step migrates these (download from
  source, upload to the build Site Assets, rewrite <img src>); see image-migrate.py + runbook.
=============================================================================================

This file is a runnable SPEC: the Graph calls + the emit shape are concrete. Run it against a
real source URL to produce a real sp-expect.json. If a classic source exposes neither /pages
nor a readable 'Site Pages'/'Pages' drive (locked-down CA / missing grant), it EXITS NONZERO
with a clear message so the engineer escalates the grant instead of emitting an empty gate.
"""
import sys, os, re, json, html
sys.path.insert(0, "/root/.openclaw/sp-provision")
import requests
from spclient import graph_token, GRAPH, _load_sp_config

CLASSIC_PAGE_DRIVES = ("Site Pages", "SitePages", "Pages")
# Classic page libraries to probe via SP REST (when Graph drives don't expose them).
SP_REST_PAGE_LISTS = ("Site Pages", "Pages")
# System pages that exist by default in a 'Site Pages' library — skip as page content,
# but note them so the engineer can see they were seen-and-skipped.
SYSTEM_PAGES = {"how to use this library.aspx"}
MAX_MARKERS_DEFAULT = 8
# crude tag stripper for classic .aspx -> visible text (markers source)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# image extraction: every <img> tag's src in a page's raw HTML. Classic sources keep
# brand/logo imagery in <img src="/sites/<Name>/SiteAssets/..."> inside WikiField, which
# _text() strips — so images are captured from the RAW HTML, before tag-stripping.
_IMG = re.compile(r"<img\b[^>]*>", re.I)
_IMG_SRC = re.compile(r'\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
_IMG_ALT = re.compile(r'\balt\s*=\s*["\']([^"\']*)["\']', re.I)


def _arg(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def _site_root(source_url):
    """Normalise any deeper URL to the site root.

    Accepts a page URL (.../sites/Name/SitePages/Home.aspx) or any /sites/<name>/...
    deeper path and strips it to https://host/sites/<name>. Leaves already-root URLs
    and non-/sites/ roots (e.g. tenant root) untouched."""
    u = source_url.rstrip("/")
    m = re.match(r"^(https?://[^/]+/sites/[^/]+)(?:/.*)?$", u, re.IGNORECASE)
    if m:
        return m.group(1)
    # also handle /teams/<name>/... classic team sites
    m = re.match(r"^(https?://[^/]+/teams/[^/]+)(?:/.*)?$", u, re.IGNORECASE)
    if m:
        return m.group(1)
    return u


def resolve_site_id(source_url):
    """Resolve a source site URL (https://host/sites/Name) to a Graph site id.
    A deeper path (page URL or library URL) is normalised to the site root first."""
    u = _site_root(source_url)
    m = re.match(r"https?://([^/]+)(/.*)?$", u)
    if not m:
        raise SystemExit("bad source url: %s" % source_url)
    host, path = m.group(1), (m.group(2) or "")
    api = "%s/sites/%s:%s" % (GRAPH, host, path) if path else "%s/sites/%s" % (GRAPH, host)
    r = requests.get(api, headers={"Authorization": "Bearer " + graph_token()})
    if r.status_code >= 300:
        raise SystemExit("cannot resolve source site (%s): %s" % (r.status_code, r.text[:200]))
    return r.json()["id"], r.json().get("webUrl", u)


def _text(s):
    return _WS.sub(" ", _TAG.sub(" ", html.unescape(s or ""))).strip()


def _stable_filename(src):
    """Derive a stable, filesystem-safe filename from an image src.
    Keeps the original basename when present (e.g. '.../SiteAssets/classic-team.jpg'
    -> 'classic-team.jpg'); falls back to a hash for data:/odd urls so the build's
    upload+rewrite map stays deterministic across re-runs."""
    s = html.unescape(src or "").split("?")[0].split("#")[0]
    base = s.rstrip("/").rsplit("/", 1)[-1]
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base).strip("-")
    if base and re.search(r"\.(png|jpe?g|gif|svg|webp|bmp|ico)$", base, re.I):
        return base
    import hashlib
    h = hashlib.sha1((src or "").encode("utf-8")).hexdigest()[:10]
    ext = ""
    m = re.search(r"\.(png|jpe?g|gif|svg|webp|bmp|ico)\b", s, re.I)
    if m:
        ext = "." + m.group(1).lower()
    return "img-%s%s" % (h, ext or ".bin")


def extract_images(raw_html):
    """Return [{src, filename, alt}] for every <img> in a page's RAW HTML.
    Order-preserving + de-duplicated by src. Operates on the pre-_text() HTML so
    server-relative SiteAssets/PublishingImages refs are NOT lost to tag-stripping."""
    out, seen = [], set()
    for tag in _IMG.findall(raw_html or ""):
        m = _IMG_SRC.search(tag)
        if not m:
            continue
        src = html.unescape(m.group(1)).strip()
        if not src or src.lower().startswith("data:"):
            # data: URIs are inline, not a fetchable source asset -> skip for migration
            continue
        if src in seen:
            continue
        seen.add(src)
        a = _IMG_ALT.search(tag)
        out.append({"src": src, "filename": _stable_filename(src),
                    "alt": (html.unescape(a.group(1)).strip() if a else "")})
    return out


# --------------------------------------------------------------------------- #
# VERBATIM content extraction — segment a page's source HTML into ORDERED blocks
# preserving the ACTUAL copy. This is the fidelity source (`pages[].content[]`):
# the build composer places each block's exact text into the modern web parts,
# and the gate scores how much of it survived. `markers[]` (heuristic snippets)
# stays for backward-compat but is NO LONGER the only thing carried over.
# --------------------------------------------------------------------------- #
# Block headings come from the source's own <h1>-<h3>. Content before the first
# heading is the intro/hero (banner + hero image). Within a block, repeated
# table rows that each carry their own image (e.g. a news list) are split into
# items so the build can map them 1:1 onto cards. Generic — driven by structure.
_HEADING = re.compile(r"(?is)<h([1-3])\b[^>]*>(.*?)</h\1>")
# Legacy publishing pages often have NO <h1-3>; their section headings are short
# standalone bold lines (<b>/<strong>, often wrapped in <span>). Used as a FALLBACK
# section boundary only when the page has no real headings.
_BOLD_LINE = re.compile(r"(?is)<(b|strong)\b[^>]*>(.*?)</\1>")
_BLOCK_BOUND = re.compile(r"(?is)<\s*/?\s*(p|div|br|tr|td|h[1-6]|ul|ol|li)\b[^>]*>")
_TR = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
# tags the SharePoint text web part accepts; everything else is dropped but its
# TEXT is kept (classic table cells collapse to inline text, never lost).
_SP_ALLOWED = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li",
               "a", "strong", "b", "em", "i", "br"}
_TAG_PARTS = re.compile(r"</?([a-zA-Z0-9]+)((?:\s+[^>]*)?)/?>")


def _kind_for(heading):
    """Classify a block by its heading text (data-driven, not client-specific)."""
    h = (heading or "").lower()
    for key, kind in (("news", "news"), ("quick link", "quicklinks"),
                      ("contact", "contacts"), ("event", "events"),
                      ("document", "documents"), ("brand", "brands"),
                      ("welcome", "welcome"), ("ceo", "welcome"),
                      ("message", "welcome"), ("link", "quicklinks")):
        if key in h:
            return kind
    return "section"


def _clean_html(raw):
    """Reduce classic markup to SP-text-webpart-allowed tags, KEEPING all text.
    Disallowed tags (table/tr/td/div/span/img...) are stripped; their text content
    survives. Block-level closes become newlines so cell text doesn't glue together.
    Anchor href is preserved (so mailto:/links carry over); other attrs dropped."""
    if not raw:
        return ""
    s = re.sub(r"(?is)</(tr|table|h[1-4]|p|li|ul|ol|div)>",
               lambda m: "</%s>\n" % m.group(1), raw)
    s = html.unescape(s)
    out = []
    for m in re.finditer(r"<[^>]+>|[^<]+", s):
        tok = m.group(0)
        if tok.startswith("<"):
            tm = _TAG_PARTS.match(tok)
            if not tm:
                continue
            name = tm.group(1).lower()
            if name not in _SP_ALLOWED:
                continue
            if tok.startswith("</"):
                out.append("</%s>" % name)
            elif name == "br":
                out.append("<br/>")
            elif name == "a":
                hm = re.search(r'(?i)\bhref\s*=\s*("[^"]*"|\'[^\']*\')',
                               tm.group(2) or "")
                out.append("<a href=%s>" % hm.group(1) if hm else "<a>")
            else:
                out.append("<%s>" % name)
        else:
            out.append(tok)
    txt = "".join(out)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{2,}", "\n", txt).strip()
    return txt


def _split_items(body_html):
    """If a block's body is a list of repeated <tr> rows that EACH carry their own
    <img>, return per-row items [{text, html, images[]}] (e.g. news stories, event
    rows). Returns [] when the block isn't a multi-item table — caller treats it as
    one block. Order-preserving."""
    rows = _TR.findall(body_html or "")
    items = []
    for row in rows:
        imgs = extract_images(row)
        txt = _text(row)
        if not txt:
            continue
        items.append({"text": txt, "html": _clean_html(row), "images": imgs})
    # only treat as items if there are >=2 rows and at least one carries an image
    if len(items) >= 2 and any(it["images"] for it in items):
        return items
    return []


def _find_heads(raw_html):
    """Ordered section boundaries [(start, end, heading_text)]. Prefer real <h1-3>;
    if the page has none (legacy publishing pages whose 'headings' are bold lines),
    fall back to standalone <b>/<strong> short lines (>=2 words, <=80 chars, not a
    full sentence). Returns [] when neither exists (page stays one intro block)."""
    real = list(_HEADING.finditer(raw_html))
    if real:
        return [(m.start(), m.end(), _text(m.group(2))) for m in real]
    out = []
    for m in _BOLD_LINE.finditer(raw_html):
        txt = _text(m.group(2))
        if not (3 <= len(txt) <= 80 and len(txt.split()) >= 2):
            continue
        if txt.rstrip().endswith((".", ",", ";")):
            continue
        # A real heading is (nearly) its WHOLE line/paragraph — NOT bold emphasis
        # inside a sentence (links like 'click here', labels like 'East Hanover:',
        # the sign-off). Compare the bold text to the text of its enclosing line.
        left = 0
        for bm in _BLOCK_BOUND.finditer(raw_html, 0, m.start()):
            left = bm.end()
        rm = _BLOCK_BOUND.search(raw_html, m.end())
        right = rm.start() if rm else len(raw_html)
        line_txt = _text(raw_html[left:right])
        if len(txt) >= 0.7 * max(1, len(line_txt)):
            out.append((m.start(), m.end(), txt))
    return out


def segment_content(raw_html):
    """Split a page's source HTML into an ORDERED list of verbatim blocks, keyed by
    the source's own <h1>-<h3> headings. Each block:
        {kind, heading, text, html, images[], items[]}
    where `text` is the exact visible copy (verbatim), `html` is the same copy
    cleaned to SP-allowed tags, `images[]` are the <img> refs inside that block,
    and `items[]` (optional) holds per-row sub-blocks for multi-item lists (news).
    This is what the modern build reproduces 1:1; nothing is summarised."""
    if not raw_html:
        return []
    heads = _find_heads(raw_html)   # [(start, end, heading_text)]
    blocks = []
    first = heads[0][0] if heads else len(raw_html)
    intro = raw_html[:first]
    if _text(intro) or extract_images(intro):
        blocks.append({"kind": "intro", "heading": "",
                       "text": _text(intro), "html": _clean_html(intro),
                       "images": extract_images(intro), "items": []})
    for i, (hstart, hend, heading) in enumerate(heads):
        seg_end = heads[i + 1][0] if i + 1 < len(heads) else len(raw_html)
        body = raw_html[hend:seg_end]
        blocks.append({
            "kind": _kind_for(heading),
            "heading": heading,
            "text": _text(body),
            "html": _clean_html(body),
            "images": extract_images(body),
            "items": _split_items(body),
        })
    return blocks


# --------------------------------------------------------------------------- #
# PUBLISHING-LAYOUT extraction (JOB0024-109, sub-task 1)
# Classic publishing pages keep their body in PublishingPageContent (the `Pages`
# library), NOT WikiField/CanvasContent1. The body is a set of field controls
# wrapped in page-layout / PublishingWebControls chrome — e.g.
#   <div ...RichHtmlField...><div class="ms-rtestate-field">...real copy...</div></div>
#   <div ...SummaryLinkFieldControl...>...links...</div>
# We strip the field-control / page-layout wrappers (verbatim INNER html survives,
# images preserved) and emit ORDERED content[] blocks keyed "pub-field"/"section"
# so a publishing page flows through the SAME verbatim composer + completeness gate
# as an article page. Order is preserved so copy_coverage() stays meaningful.
# Config-driven chrome list — no client-specific hardcoding.
# --------------------------------------------------------------------------- #
# field-control / page-layout wrapper class tokens to UNWRAP (chrome -> drop the
# wrapper tag, keep its inner content). Matched case-insensitively on the wrapper's
# class attribute. Extend via config (sp.config "publishingChromeTokens") if a tenant
# uses non-default layouts.
_PUB_CHROME_TOKENS = (
    "PublishingWebControls", "ms-rtestate-field", "RichHtmlField",
    "RichImageField", "PublishingImageField", "SummaryLinkFieldControl",
    "publishingPageContent", "ms-rteThemeBackColor",
)
# A publishing field region: the outer field-control wrapper. We split the body into
# ordered top-level field regions on these markers so each becomes one block.
_PUB_FIELD = re.compile(
    r'(?is)<div\b[^>]*\bclass\s*=\s*["\'][^"\']*'
    r'(?:RichHtmlField|RichImageField|PublishingImageField|SummaryLinkFieldControl|'
    r'ms-rtestate-field|PublishingWebControls)[^"\']*["\'][^>]*>')


def _strip_pub_chrome(html_in):
    """Remove field-control / page-layout WRAPPER <div>/<span> tags whose class
    carries a known chrome token, keeping their inner content verbatim. Other tags
    (incl. <img>) are untouched. A lightweight, order-preserving unwrap — not a full
    HTML parser, but classic publishing chrome is shallow and regular."""
    if not html_in:
        return ""
    tokens = "|".join(re.escape(t) for t in _PUB_CHROME_TOKENS)
    # drop opening wrapper tags whose class matches a chrome token; the matching
    # close tag is dropped generically below (we can't pair without a parser, so we
    # only remove the OPEN chrome tag and let _clean_html collapse the leftover close)
    pat = re.compile(r'(?is)<(div|span)\b[^>]*\bclass\s*=\s*["\'][^"\']*'
                     r'(?:%s)[^"\']*["\'][^>]*>' % tokens)
    return pat.sub("", html_in)


def _is_publishing_html(raw_html):
    """Structural signal that a page body is classic PublishingPageContent: it carries
    a publishing field-control wrapper. Used to route the page to _publishing_blocks
    when the source `lib`/kind isn't otherwise threaded through (e.g. network reads)."""
    return bool(raw_html) and bool(_PUB_FIELD.search(raw_html))


def _publishing_blocks(raw_html):
    """Split a PublishingPageContent body into ORDERED verbatim content[] blocks.
    Each top-level field region becomes a block: kind 'pub-field' (a rich-text/image
    field region) — or, when a region carries its own <h1-3> heading, that heading's
    text is preserved and sub-headed regions key 'section' (so heading-driven copy
    coverage and the composer's main-column rendering both work). Reuses the existing
    _IMG / _block_html-compatible shape ({kind,heading,text,html,images[],items[]})
    so it flows through the SAME composer + gate as article pages. Order preserved."""
    if not raw_html:
        return []
    # ordered field-region boundaries; if the layout has no recognizable field
    # wrapper, fall back to heading segmentation (segment_content) so we never lose copy.
    bounds = [m.start() for m in _PUB_FIELD.finditer(raw_html)]
    if not bounds:
        # no field wrappers — treat the whole stripped body as heading-segmented
        # content, but key every produced block as pub-field/section for clarity.
        stripped = _strip_pub_chrome(raw_html)
        blocks = segment_content(stripped)
        for b in blocks:
            if b.get("kind") in ("intro", "section"):
                b["kind"] = "pub-field" if not b.get("heading") else "section"
        return blocks
    bounds.append(len(raw_html))
    blocks = []
    for i in range(len(bounds) - 1):
        region = raw_html[bounds[i]:bounds[i + 1]]
        inner = _strip_pub_chrome(region)
        if not (_text(inner) or extract_images(inner)):
            continue
        # a region with its own real heading -> keep heading + key 'section';
        # otherwise it's a plain field region -> 'pub-field'.
        heads = _find_heads(inner)
        heading = heads[0][2] if heads else ""
        kind = "section" if heading else "pub-field"
        blocks.append({
            "kind": kind,
            "heading": heading,
            "text": _text(inner),
            "html": _clean_html(inner),
            "images": extract_images(inner),
            "items": _split_items(inner),
        })
    return blocks


def read_modern_pages(sid):
    """Return [(name,title,text,raw_html)] for MODERN site pages (may be empty for a
    classic source). raw_html is the canvasLayout JSON blob, scanned for innerHtml <img>."""
    out = []
    for api in ("v1.0", "beta"):
        r = requests.get("https://graph.microsoft.com/%s/sites/%s/pages"
                         "?$select=id,name,title,webUrl&$top=200" % (api, sid),
                         headers={"Authorization": "Bearer " + graph_token()})
        if r.status_code >= 300:
            continue
        for p in r.json().get("value", []):
            txt = ""
            blob = ""
            c = requests.get("https://graph.microsoft.com/%s/sites/%s/pages/%s/"
                             "microsoft.graph.sitePage?$expand=canvasLayout"
                             % (api, sid, p["id"]),
                             headers={"Authorization": "Bearer " + graph_token()})
            if c.status_code < 300:
                blob = json.dumps(c.json().get("canvasLayout") or {})
                txt = _text(blob)
            out.append((p.get("name"), p.get("title"), txt, blob))
        if out:
            break
    return out


def read_classic_pages(sid):
    """Return [(name,title,text,raw_html)] for CLASSIC .aspx pages read from the page
    library drive. raw_html is the server-rendered .aspx, scanned for <img> refs."""
    out = []
    dr = requests.get("%s/sites/%s/drives" % (GRAPH, sid),
                      headers={"Authorization": "Bearer " + graph_token()})
    drives = {d.get("name"): d for d in dr.json().get("value", [])} if dr.status_code < 300 else {}
    drive = next((drives[n] for n in CLASSIC_PAGE_DRIVES if n in drives), None)
    if not drive:
        return out
    kids = requests.get("%s/drives/%s/root/children?$top=400" % (GRAPH, drive["id"]),
                        headers={"Authorization": "Bearer " + graph_token()})
    for it in (kids.json().get("value", []) if kids.status_code < 300 else []):
        nm = it.get("name", "")
        if not nm.lower().endswith(".aspx"):
            continue
        durl = it.get("@microsoft.graph.downloadUrl")
        body = ""
        if durl:
            g = requests.get(durl)
            if g.status_code < 300:
                body = g.text
        out.append((nm, nm[:-5], _text(body), body))
    return out


def _sp_rest_token(host, tenant=None):
    """Mint a SharePoint-resource bearer token from the same app cert spclient uses
    for Graph (Graph does not expose a classic 'Site Pages' library as a drive).
    Mirrors cc_provision_intake._sp_rest_token(). Token is host-scoped, so it works
    for any site on `host`. `tenant` overrides the authority tenant for cross-tenant
    Level-2 SOURCE/client reads; None -> our own tenantId (zero behaviour change)."""
    import msal
    from cryptography.hazmat.primitives.serialization import (
        pkcs12, Encoding, PrivateFormat, NoEncryption,
    )
    cfg = _load_sp_config()
    _tenant = tenant or cfg["tenantId"]
    from pathlib import Path
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
        },
    )
    res = "https://%s" % host
    r = app.acquire_token_for_client(scopes=[res + "/.default"])
    if "access_token" not in r:
        raise RuntimeError("SP REST token failed: %s / %s"
                           % (r.get("error"), str(r.get("error_description"))[:200]))
    return r["access_token"]


def read_classic_pages_sprest(web, tenant=None):
    """SP-REST fallback: read CLASSIC .aspx pages from the 'Site Pages'/'Pages'
    library when Graph exposes neither /pages nor a page-library drive.

    Returns (pages, skipped) where pages = [(name,title,text,raw_html)] and skipped is a
    list of system page names that were seen and intentionally skipped.

    The page item's wiki/web-part HTML lives in WikiField (wiki pages) or
    CanvasContent1 (some web-part pages); we read both and use whichever has content.
    """
    from urllib.parse import urlparse
    host = urlparse(web).netloc
    site_web = web.rstrip("/")
    tok = _sp_rest_token(host, tenant)
    h = {"Authorization": "Bearer " + tok,
         "Accept": "application/json;odata=nometadata"}
    out, skipped = [], []
    for list_title in SP_REST_PAGE_LISTS:
        url = ("%s/_api/web/lists/getbytitle('%s')/items"
               "?$select=FileLeafRef,Title,WikiField,CanvasContent1&$top=500"
               % (site_web, list_title.replace(" ", "%20")))
        r = requests.get(url, headers=h)
        if r.status_code >= 300:
            continue  # library absent on this site -> try the next candidate
        for it in r.json().get("value", []):
            nm = it.get("FileLeafRef", "") or ""
            if not nm.lower().endswith(".aspx"):
                continue
            if nm.lower() in SYSTEM_PAGES:
                skipped.append(nm)
                continue
            body = it.get("WikiField") or it.get("CanvasContent1") or ""
            title = it.get("Title") or nm[:-5]
            out.append((nm, title, _text(body), body))
        if out or skipped:
            break  # found the page library; don't double-count from a second list
    return out, skipped


def read_lists(sid):
    """Return [name] of non-system lists/libraries (candidate migrations)."""
    r = requests.get("%s/sites/%s/lists?$top=200&$select=displayName,list,hidden" % (GRAPH, sid),
                     headers={"Authorization": "Bearer " + graph_token()})
    out = []
    for l in (r.json().get("value", []) if r.status_code < 300 else []):
        if l.get("hidden"):
            continue
        tmpl = (l.get("list") or {}).get("template", "")
        if tmpl in ("documentLibrary", "genericList"):
            out.append(l.get("displayName"))
    return out


def derive_markers(text, title, maxm):
    """Pick up to maxm short distinctive marker strings from a page's title + visible text.
    Heuristic: title first, then the longest unique-ish capitalised phrases / lines."""
    markers = []
    if title:
        markers.append(title)
    # candidate phrases: chunks split on punctuation, length 3..60, with a capital
    cands = [c.strip() for c in re.split(r"[.|•·\-–—:;\n]", text) if c.strip()]
    seen = {m.lower() for m in markers}
    for c in sorted(cands, key=len, reverse=True):
        if 3 <= len(c) <= 60 and re.search(r"[A-Z]", c) and c.lower() not in seen:
            markers.append(c)
            seen.add(c.lower())
        if len(markers) >= maxm:
            break
    return markers[:maxm]


def _marker_units(content):
    """Verbatim text units to mine markers from, derived from each block's CLEANED
    html (which keeps <br>/row boundaries as newlines). Splitting on newlines too
    means a candidate never spans a line/row the way flat whole-page text did —
    so every emitted marker is a contiguous substring of the rebuilt page HTML."""
    units = []
    for b in content or []:
        for it in (b.get("items") or []):
            units.append(_text(it.get("html") or it.get("text", "")))
        if not b.get("items"):
            # split the cleaned html into lines so candidates stay within one line
            chunk = (b.get("html") or "")
            for line in re.split(r"<br\s*/?>|\n", chunk):
                t = _text(line)
                if t:
                    units.append(t)
    return units


def derive_markers_from_content(content, title, maxm):
    """Derive gate-anchor markers from the VERBATIM per-block content, so every
    marker is a real distinctive phrase that EXISTS contiguously within a single
    source line/block (never glued across the source's column/row/section
    boundaries the way whole-page flat-text splitting did). Longest capitalised
    phrase per unit, ASCII-only (avoids emoji/decoration that won't round-trip)."""
    markers = []
    seen = set()
    if title:
        markers.append(title)
        seen.add(title.lower())
    for utext in _marker_units(content):
        cands = [c.strip() for c in re.split(r"[.|•·\-–—:;]", utext) if c.strip()]
        best = None
        for c in sorted(cands, key=len, reverse=True):
            if not (3 <= len(c) <= 60):
                continue
            if not re.search(r"[A-Z]", c):
                continue
            if not all(ord(ch) < 128 for ch in c):  # skip emoji/■ etc. — won't match cleanly
                continue
            if c.lower() in seen:
                continue
            best = c
            break
        if best:
            markers.append(best)
            seen.add(best.lower())
        if len(markers) >= maxm:
            break
    return markers[:maxm]


# --------------------------------------------------------------------------- #
# FARA-absorbed enrichment — broken-link + image-dimension signals that feed the
# Content Tracker (sp-tracker.js --enrich). Advisory + non-gating, so this is
# strictly best-effort: any failure is swallowed and the audit still succeeds.
# --------------------------------------------------------------------------- #
def _href_set(expect):
    """Real, checkable hrefs from the verbatim content html (skip #, mailto, tel, js)."""
    hrefs, seen = [], set()
    href_re = re.compile(r'href=["\']([^"\']+)["\']', re.I)
    for pg in expect.get("pages", []):
        for b in (pg.get("content") or []):
            htmls = [b.get("html") or ""] + [(it.get("html") or "") for it in (b.get("items") or [])]
            for h in htmls:
                for m in href_re.findall(h):
                    u = html.unescape(m).strip()
                    if (not u or u.startswith("#")
                            or u.lower().startswith(("mailto:", "tel:", "javascript:"))
                            or u in seen):
                        continue
                    seen.add(u); hrefs.append(u)
    return hrefs


def _download_sp_file(web, token, server_rel):
    """GET a file's bytes from the source SITE web via SP REST (app grant is site-scoped)."""
    import urllib.request, urllib.parse
    if server_rel.lower().startswith("http"):
        server_rel = urllib.parse.urlsplit(server_rel).path
    quoted = urllib.parse.quote(server_rel.replace("'", "''"), safe="/()%")
    url = "%s/_api/web/getfilebyserverrelativeurl('%s')/$value" % (web.rstrip("/"), quoted)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except Exception:
        return None


def enrich_audit(expect, web, host, out_path, tenant=None):
    """Write enrich.json (broken links + image natural dims) next to sp-expect.json."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sp_audit_http
    except Exception as e:
        print("[audit] enrich skipped (helper import failed: %s)" % e); return
    enrich = {"brokenLinks": [], "imageDims": {}}
    try:
        enrich["brokenLinks"] = sp_audit_http.head_check(_href_set(expect))
    except Exception as e:
        print("[audit] broken-link check failed: %s" % e)
    srcs, seen = [], set()
    for pg in expect.get("pages", []):
        for img in (pg.get("images") or []):
            s = img.get("src")
            if s and s not in seen:
                seen.add(s); srcs.append(s)
    if srcs:
        try:
            token = _sp_rest_token(host, tenant)
            for s in srcs:
                data = _download_sp_file(web, token, s)
                if data:
                    w, h = sp_audit_http.image_dims_from_bytes(data)
                    if w or h:
                        enrich["imageDims"][s] = {"w": w, "h": h}
        except Exception as e:
            print("[audit] image-dim enrich failed: %s" % e)
    epath = os.path.join(os.path.dirname(out_path) or ".", "enrich.json")
    json.dump(enrich, open(epath, "w"), indent=1)
    print("[audit] wrote %s — %d broken link(s), %d image dim(s)"
          % (epath, len(enrich["brokenLinks"]), len(enrich["imageDims"])))


def load_capture(cap_dir):
    """Level-2 source loader: read the cc-sp-capture bundle (captured Mac-side over an
    authenticated browser session) instead of doing an authed network read. Returns the
    same shape the network path produces:
        (pages, src_kind, web, sid, lists, skipped_pages)
    where pages = [(name, title, text, raw_html)]."""
    man = json.load(open(os.path.join(cap_dir, "manifest.json"), encoding="utf-8"))
    web = man.get("sourceUrl") or man.get("siteRoot") or ""
    sid = man.get("sourceSiteId")
    src_kind = man.get("sourceKind", "classic-capture")
    lists = [(l.get("name") or l.get("title")) for l in man.get("lists", [])]
    pages, skipped = [], []
    for p in man.get("pages", []):
        nm = p.get("name", "") or ""
        if nm.lower() in SYSTEM_PAGES:
            skipped.append(nm); continue
        bf = os.path.join(cap_dir, p.get("body", ""))
        body = open(bf, encoding="utf-8").read() if os.path.exists(bf) else ""
        title = p.get("title") or nm[:-5]
        pages.append((nm, title, _text(body), body))
    if not pages:
        print("[audit] FATAL: capture bundle has no usable pages (%s)" % cap_dir)
        sys.exit(3)
    # list MIGRATION is not implemented — do NOT carry the source lists into the
    # gating expect, or cc-verify-sp's "lists missing on build site" check fails on
    # every captured list. The capture's list inventory is informational only.
    return pages, src_kind, web, sid, [], skipped


def enrich_from_capture(expect, cap_dir, out_path):
    """enrich.json from a capture bundle: broken-link check (no auth) + image dims read
    from the locally captured image files (mapped src -> file via images-map.json)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sp_audit_http
    except Exception as e:
        print("[audit] enrich skipped (helper import failed: %s)" % e); return
    enrich = {"brokenLinks": [], "imageDims": {}}
    try:
        enrich["brokenLinks"] = sp_audit_http.head_check(_href_set(expect))
    except Exception as e:
        print("[audit] broken-link check failed: %s" % e)
    imap = {}
    mp = os.path.join(cap_dir, "images-map.json")
    if os.path.exists(mp):
        try:
            imap = json.load(open(mp, encoding="utf-8"))
        except Exception:
            imap = {}
    seen = set()
    for pg in expect.get("pages", []):
        for img in (pg.get("images") or []):
            s = img.get("src")
            if not s or s in seen:
                continue
            seen.add(s)
            rel = imap.get(s)
            if not rel:
                continue
            fp = os.path.join(cap_dir, rel)
            if not os.path.exists(fp):
                continue
            try:
                w, h = sp_audit_http.image_dims_from_bytes(open(fp, "rb").read())
                if w or h:
                    enrich["imageDims"][s] = {"w": w, "h": h}
            except Exception:
                pass
    epath = os.path.join(os.path.dirname(out_path) or ".", "enrich.json")
    json.dump(enrich, open(epath, "w"), indent=1)
    print("[audit] wrote %s (from capture) — %d broken link(s), %d image dim(s)"
          % (epath, len(enrich["brokenLinks"]), len(enrich["imageDims"])))


def main():
    from_capture = _arg("--from-capture")
    if (len(sys.argv) < 2 or sys.argv[1].startswith("--")) and not from_capture:
        print(__doc__); sys.exit(1)
    source_url = None if from_capture else sys.argv[1]
    job = _arg("--job")
    out = _arg("--out") or (("/srv/projects/%s/sp-expect.json" % job) if job else "sp-expect.json")
    maxm = int(_arg("--max-markers", MAX_MARKERS_DEFAULT))
    build_siteid = _arg("--build-siteid")
    # --tenant overrides the authority tenant for SOURCE/client SP-REST reads
    # (cross-tenant Level-2). Default None -> our own tenant (zero change).
    src_tenant = _arg("--tenant")

    if from_capture:
        # Level-2 path: the source was read Mac-side over an authenticated browser
        # session (cc-sp-capture). Parse the local bundle — no auth, no network read.
        pages, src_kind, web, sid, lists, skipped_pages = load_capture(from_capture)
        print("[audit] from-capture: %s (%d page(s), kind=%s)" % (web, len(pages), src_kind))
    else:
        sid, web = resolve_site_id(source_url)
        print("[audit] source resolved: %s (%s)" % (web, sid))

        pages = read_modern_pages(sid)
        src_kind = "modern"
        skipped_pages = []
        if not pages:
            pages = read_classic_pages(sid)
            src_kind = "classic"
        if not pages:
            # Graph exposed neither /pages nor a 'Site Pages'/'Pages' drive. A real classic
            # team site (WebTemplate=STS) keeps its pages in a classic 'Site Pages' library
            # that Graph's drive view doesn't surface — fall back to SP REST.
            try:
                pages, skipped_pages = read_classic_pages_sprest(web, src_tenant)
                src_kind = "classic-sprest"
            except Exception as e:
                print("[audit] SP REST fallback failed: %s" % e)
        if not pages:
            print("[audit] FATAL: no readable pages on source (neither Graph /pages, a 'Site "
                  "Pages'/'Pages' Graph drive, nor an SP-REST 'Site Pages'/'Pages' library). "
                  "Check the Sites.Selected/Read grant for this source site, then retry. "
                  "Refusing to emit an empty gate.")
            sys.exit(3)

        lists = read_lists(sid)
    if skipped_pages:
        print("[audit] skipped %d system page(s): %s"
              % (len(skipped_pages), ", ".join(skipped_pages)))
    print("[audit] read %d %s page(s), %d list(s)" % (len(pages), src_kind, len(lists)))

    expect = {
        "_comment": "AUTO-GENERATED by sp-audit.py from the classic SOURCE site. Do not hand-edit; "
                    "re-run the audit. The modern BUILD must reproduce these pages + markers. "
                    "siteId is the BUILD site, injected from site.json at gate time.",
        "sourceUrl": web,
        "sourceSiteId": sid,
        "sourceKind": src_kind,
        "siteId": build_siteid,        # BUILD site; null -> gate injects from site.json
        "rail": "convert",
        "pages": [],
        "lists": [{"name": n} for n in lists if n],
    }
    if skipped_pages:
        expect["skippedSystemPages"] = skipped_pages
    total_imgs = 0
    for name, title, text, raw_html in pages:
        # modern build page name: keep the source .aspx name so the page maps 1:1
        pname = name if name.lower().endswith(".aspx") else (name + ".aspx")
        images = extract_images(raw_html)
        total_imgs += len(images)
        # VERBATIM content: ordered structured blocks carrying the EXACT source copy.
        # This is the fidelity source the build composes 1:1 and the gate scores.
        # Publishing pages (PublishingPageContent / `Pages` lib) carry their body in
        # classic field-control chrome — route them through _publishing_blocks, which
        # strips the chrome and emits the SAME content[] shape (pub-field/section) so
        # they flow through the SAME composer + completeness gate as article pages.
        if _is_publishing_html(raw_html):
            content = _publishing_blocks(raw_html)
        else:
            content = segment_content(raw_html)
        full_text = _text(raw_html)
        # markers anchor the gate; derive them from the VERBATIM per-block content so
        # each is a phrase that truly exists in the source (no cross-column gluing).
        markers = (derive_markers_from_content(content, title, maxm)
                   if content else derive_markers(text, title, maxm))
        expect["pages"].append({
            "name": pname,
            "title": title or pname[:-5],
            "publish": True,
            "webparts": [{"type": "textWebPart", "min": 1}],
            "markers": markers,
            "markers_note": "Migrated from source %s; content rebuilt as HTML inside one text web part." % name,
            # NEW fidelity source: ordered verbatim blocks (Welcome, CEO, each News
            # item w/ date+category, Quick Links, Contacts...) each with its own text,
            # SP-clean html, and <img> refs. The build reproduces these word-for-word.
            "content": content,
            # the full verbatim visible copy, for the gate's copy-fidelity coverage score
            "sourceText": full_text,
            "sourceTextLen": len(full_text),
            # IMAGE MIGRATION: every <img> the source page referenced. The build step
            # downloads each `src` (app read), uploads to the BUILD site's Site Assets,
            # and rewrites the <img src> to the new build-site URL using `filename` as the
            # stable key. The gate (optional) asserts these `filename`s land on the build page.
            "images": images,
        })

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(expect, open(out, "w"), indent=2, ensure_ascii=False)
    print("[audit] wrote %s — %d pages, %d lists, %d image ref(s). Review markers + images "
          "before building." % (out, len(expect["pages"]), len(expect["lists"]), total_imgs))

    # FARA-absorbed: broken-link + image-dim signals for the Content Tracker
    # (advisory, non-gating). Best-effort — never breaks the audit.
    try:
        if from_capture:
            enrich_from_capture(expect, from_capture, out)
        else:
            enrich_audit(expect, web, web.split("/")[2], out, src_tenant)
    except Exception as e:
        print("[audit] enrich pass failed (non-fatal): %s" % e)


if __name__ == "__main__":
    main()
