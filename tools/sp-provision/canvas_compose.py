#!/usr/bin/env python3
"""canvas_compose.py — rebuild a converted SharePoint page as a PROPER modern page.

PROBLEM this solves
-------------------
spclient.create_page emits ONE single-column #microsoft.graph.textWebPart whose
custom HTML+CSS (margins/padding) is STRIPPED by SharePoint's modern text web part,
with no columns and no native Image web parts. Result: cramped, no real layout.

WHAT THIS DOES
--------------
Authors a modern page's `canvasLayout` with REAL SharePoint structure — multiple
horizontalSections, multi-column sections (columnFactor in a 12-grid), native
Image web parts (#microsoft.graph.standardWebPart, OOTB Image GUID), and clean
text web parts — so SharePoint renders correct spacing/layout (its own column
grid, not stripped CSS).

It is REUSABLE: driven entirely by sp-expect.json (pages + markers[] + images[])
and image-map.json (_map: source-src -> migrated build URL). Not hardcoded to any
one client. A small content model groups the page's markers into MAIN vs SIDEBAR
vs NEWS buckets using cheap keyword heuristics; every marker is guaranteed to land
somewhere on the page (the conversion gate asserts all markers survive).

GRAPH canvasLayout SCHEMA (verified empirically on CCBuild-0022, 2026-06-11)
---------------------------------------------------------------------------
POST /sites/{id}/pages  (v1.0; @odata.type #microsoft.graph.sitePage) with:
  canvasLayout.horizontalSections[] = {
     id, emphasis, layout, columns[] }
  layout is an ENUM (horizontalSectionLayoutType). Allowed + resulting widths:
     oneColumn            -> [12]
     twoColumns           -> [6,6]
     threeColumns         -> [4,4,4]
     oneThirdLeftColumn   -> [4,8]
     oneThirdRightColumn  -> [8,4]
     fullWidth            -> [12] (full-bleed)
  *** You CANNOT set arbitrary column.width — Graph validates width against the
      named layout ("mismatch of column width, should be 6 but found 8"). To get
      an 8/4 split use layout=oneThirdRightColumn, NOT width=8+4 on twoColumns. ***
  column = { id, width, webparts[] }
  text web part  = { @odata.type:#microsoft.graph.textWebPart, innerHtml }
  image web part = { @odata.type:#microsoft.graph.standardWebPart,
                     webPartType:"d1d91016-032f-456d-98a4-721247c305e8",  # OOTB Image
                     data:{ dataVersion:"1.9", properties:{...},
                            serverProcessedContent:{ imageSources:[{key:"imageSource",
                                                     value:<image URL>}] } } }
  The image URL persists in data.serverProcessedContent.imageSources[].value and
  renders natively. (cc-verify-sp folds non-text web parts to JSON, so the image
  URL also counts toward marker/structure checks.)
Then publish: POST .../pages/{id}/microsoft.graph.sitePage/publish .

USAGE
-----
  PYTHONPATH=/root/.openclaw/sp-provision /root/.openclaw/venv/bin/python \
    canvas_compose.py --job JOB0022 [--page Home.aspx] [--dry-run]

  # or point at explicit files / site
  canvas_compose.py --expect /srv/projects/JOB0022/sp-expect.json \
                    --imagemap /srv/projects/JOB0022/image-map.json \
                    --site-path /sites/CCBuild-0022 --page Home.aspx
"""
import sys, os, re, json, uuid, argparse, requests

sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import SP  # noqa: E402

IMAGE_WEBPART_GUID = "d1d91016-032f-456d-98a4-721247c305e8"  # OOTB "Image" web part

# Graph sitePage compose returns HTTP 400 when a page has more than ~6 heavy
# media web parts (Image, Embed, File-viewer, Hero, Quick Links).
# Empirically confirmed on CCBuild-0022/JOB0023 (ref_sp_page_compose_limits).
MAX_HEAVY_WEBPARTS_PER_PAGE = 6
# Additional native OOTB web parts (shapes verified empirically on CCBuild-0022,
# 2026-06-11). NOTE: Hero / Quick Links / Embed are only accepted by the BETA
# Graph pages endpoint ("not supported in current version of API" on v1.0) — so
# apply_page prefers beta. File/media (File viewer) works on both.
HERO_WEBPART_GUID = "c4bd7b2f-7b6e-4599-8485-16504575f590"        # OOTB "Hero"
QUICKLINKS_WEBPART_GUID = "c70391ea-0b10-4ee9-b2b4-006d3fcad0cd"  # OOTB "Quick links"
EMBED_WEBPART_GUID = "490d7c76-1824-45b2-9de3-676421c997fa"       # OOTB "Embed"
FILEMEDIA_WEBPART_GUID = "b7dd04e1-19ce-4b24-9132-b60a1c2b910d"   # OOTB "File and media"
SITE_HOST = "contoso.sharepoint.com"

# web parts that require the BETA pages endpoint to be accepted by Graph.
BETA_ONLY_WEBPARTS = {HERO_WEBPART_GUID, QUICKLINKS_WEBPART_GUID, EMBED_WEBPART_GUID}
BUILD_ASSET_DRIVE = "Documents"           # build-site library uploaded video lands in
MIGRATED_PREFIX = "Migrated"              # per-job subfolder: Migrated/<JOB>/<file>
PEXELS_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

# layout enum -> column widths (verified). Used to validate/derive widths.
LAYOUT_WIDTHS = {
    "oneColumn": [12], "fullWidth": [0],
    "twoColumns": [6, 6], "threeColumns": [4, 4, 4],
    "oneThirdLeftColumn": [4, 8], "oneThirdRightColumn": [8, 4],
}


# --------------------------------------------------------------------------- #
# web-part builders
# --------------------------------------------------------------------------- #
def text_wp(inner_html):
    return {"@odata.type": "#microsoft.graph.textWebPart",
            "id": str(uuid.uuid4()), "innerHtml": inner_html}


def image_wp(image_url, alt="", site_id="", caption=""):
    """Native Image web part referencing an uploaded asset URL."""
    parts = (site_id or ",,").split(",")
    site_guid = parts[1] if len(parts) > 2 else ""
    web_guid = parts[2] if len(parts) > 2 else ""
    return {
        "@odata.type": "#microsoft.graph.standardWebPart",
        "id": str(uuid.uuid4()),
        "webPartType": IMAGE_WEBPART_GUID,
        "data": {
            "dataVersion": "1.9",
            "title": "Image", "description": "Image",
            "properties": {
                "imageSourceType": 2,
                "altText": alt or "", "overlayText": "",
                "siteId": site_guid, "webId": web_guid,
                "listId": "00000000-0000-0000-0000-000000000000",
                "uniqueId": "00000000-0000-0000-0000-000000000000",
                "imgWidth": 1200, "imgHeight": 675,
                "fixAspectRatio": False,
                "captionText": caption or "", "alignment": "Center",
            },
            "serverProcessedContent": {
                "htmlStrings": [], "searchablePlainTexts": [], "links": [],
                "imageSources": [{"key": "imageSource", "value": image_url}],
            },
        },
    }


def hero_wp(title, tagline="", image_url="", link_url=""):
    """Native Hero web part (single full-width tile). Image is optional (text-only
    hero still renders). title + tagline land verbatim in serverProcessedContent
    so the fidelity gate counts them. BETA endpoint only."""
    tid = str(uuid.uuid4())
    tile = {
        "id": tid, "description": "", "altText": title or "",
        "title": title or "", "calloutText": tagline or "",
        "imageDisplayOption": 2,
        "isImageSelected": bool(image_url),
        "linkSettings": {"linkUrl": link_url or "", "openInNewTab": False},
        "textAlignmentVertical": 1, "textAlignmentHorizontal": 1,
        "showButton": False, "buttonText": "",
    }
    spc = {
        "htmlStrings": [],
        "searchablePlainTexts": [
            {"key": "tiles[0].title", "value": title or ""},
            {"key": "tiles[0].calloutText", "value": tagline or ""},
        ],
        "imageSources": ([{"key": "tiles[0].imageSource", "value": image_url}]
                         if image_url else []),
        "links": [{"key": "tiles[0].link", "value": link_url or ""}],
    }
    return {
        "@odata.type": "#microsoft.graph.standardWebPart",
        "id": str(uuid.uuid4()), "webPartType": HERO_WEBPART_GUID,
        "data": {
            "dataVersion": "1.5", "title": "Hero", "description": "Hero",
            "properties": {"heroLayoutThreshold": 640, "layout": 1,
                           "hideButtons": False, "tiles": [tile]},
            "serverProcessedContent": spc,
        },
    }


def quicklinks_wp(items, heading="Quick links", layout_id="List"):
    """Native Quick Links web part. `items` = list of {title, url, (description)}.
    IMPORTANT: Graph's JSON parser rejects a `properties.items` array of objects
    ("Parsing JSON Light resource sets ... without entity set is not supported"),
    so the links are carried ENTIRELY in serverProcessedContent (searchablePlainTexts
    for titles + links for urls). This is the only shape the API accepts AND it
    keeps the link titles in the fidelity blob. BETA endpoint only. <=8 enforced
    by caller (overflow noted there)."""
    spt, lks = [], []
    for i, it in enumerate(items):
        spt.append({"key": "items[%d].title" % i, "value": it.get("title", "")})
        if it.get("description"):
            spt.append({"key": "items[%d].description" % i,
                        "value": it.get("description", "")})
        lks.append({"key": "items[%d].sourceItem.url" % i,
                    "value": it.get("url", "") or ""})
    return {
        "@odata.type": "#microsoft.graph.standardWebPart",
        "id": str(uuid.uuid4()), "webPartType": QUICKLINKS_WEBPART_GUID,
        "data": {
            "dataVersion": "2.2", "title": heading or "Quick links",
            "description": "Quick links",
            "properties": {
                "isMigrated": True, "layoutId": layout_id,
                "shouldShowThumbnail": True, "hideWebPartWhenEmpty": True,
                "dataProviderId": "QuickLinks",
                "webId": "", "siteId": "", "listId": "", "baseUrl": "",
                "title": heading or "Quick links",
                "buttonLayoutOptions": {"showDescription": False,
                    "buttonTreatment": 2, "iconPositionType": 2,
                    "textAlignmentVertical": 2, "textAlignmentHorizontal": 2,
                    "linesOfText": 2},
                "listLayoutOptions": {"showDescription": bool(
                    any(it.get("description") for it in items)),
                    "showIcon": True},
                "waffleLayoutOptions": {"iconSize": 48,
                    "onlyShowThumbnail": False},
            },
            "serverProcessedContent": {"htmlStrings": [],
                "searchablePlainTexts": spt, "imageSources": [], "links": lks},
        },
    }


def embed_wp(src_url="", embed_code=""):
    """Native Embed web part. Renders a hosted video/iframe. Provide either a
    direct media URL (wrapped in a <video>) or raw embed_code. BETA endpoint only."""
    code = embed_code or ('<video controls style="width:100%%" src="%s"></video>'
                          % src_url)
    return {
        "@odata.type": "#microsoft.graph.standardWebPart",
        "id": str(uuid.uuid4()), "webPartType": EMBED_WEBPART_GUID,
        "data": {
            "dataVersion": "1.0", "title": "Embed", "description": "Embed",
            "properties": {"embedCode": code, "cachedEmbedCode": "",
                           "shouldUpdateConfiguration": False,
                           "thumbnailUrl": "", "tempState": {}},
            "serverProcessedContent": {"htmlStrings": [],
                "searchablePlainTexts": [], "imageSources": [], "links": []},
        },
    }


def fileviewer_wp(file_url, file_type="mp4"):
    """Native File and media (File viewer) web part for an uploaded build-site file
    (e.g. an mp4). Works on both v1.0 and beta."""
    return {
        "@odata.type": "#microsoft.graph.standardWebPart",
        "id": str(uuid.uuid4()), "webPartType": FILEMEDIA_WEBPART_GUID,
        "data": {
            "dataVersion": "1.1", "title": "File and media",
            "description": "File and media",
            "properties": {"file": file_url, "fileType": file_type,
                           "layout": 1, "showName": True, "overlayText": ""},
            "serverProcessedContent": {"htmlStrings": [],
                "searchablePlainTexts": [], "imageSources": [], "links": []},
        },
    }


# --------------------------------------------------------------------------- #
# Pexels VIDEO (judicious — only when the design-spec calls for it)
# --------------------------------------------------------------------------- #
def _secret(name):
    """Read a key from the shared secret store (same source cc_assets uses)."""
    try:
        for line in open("/root/.openclaw/secrets/cc-secrets.env"):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return os.environ.get(name, "")


def pexels_video_mp4(query, min_height=540):
    """Search Pexels VIDEO api and return one mp4 url (>= min_height) or None.
    Reuses the PEXELS_API_KEY secret store (same as cc_assets)."""
    import urllib.request as U
    key = _secret("PEXELS_API_KEY")
    if not key:
        return None
    url = ("https://api.pexels.com/videos/search?query=%s&per_page=3"
           "&orientation=landscape&size=medium" % U.quote(query))
    try:
        req = U.Request(url, headers={"User-Agent": PEXELS_UA,
                                      "Authorization": key})
        data = json.loads(U.urlopen(req, timeout=25).read())
    except Exception as e:  # noqa: BLE001
        print("  [pexels-video] WARN:", str(e)[:120])
        return None
    for v in data.get("videos", []):
        files = sorted(v.get("video_files", []),
                       key=lambda f: (f.get("height") or 0))
        pick = next((f for f in files if f.get("file_type") == "video/mp4"
                     and (f.get("height") or 0) >= min_height), None)
        if not pick and files:
            pick = files[-1]
        if pick:
            return pick.get("link")
    return None


def upload_video_to_build(sp, job, query):
    """Download a Pexels mp4 and upload it to the build site under
    Documents/Migrated/<JOB>/. Returns the file's webUrl (for File-viewer/Embed)
    or None. Judicious — only called when a spec section requests video."""
    import urllib.request as U
    mp4 = pexels_video_mp4(query or "modern professional business")
    if not mp4:
        print("  [video] no Pexels mp4 for query=%r" % query)
        return None
    try:
        data = U.urlopen(U.Request(mp4, headers={"User-Agent": PEXELS_UA}),
                         timeout=90).read()
    except Exception as e:  # noqa: BLE001
        print("  [video] download FAIL:", str(e)[:120])
        return None
    fname = "stock-%s.mp4" % re.sub(r"[^a-z0-9]+", "-",
                                    (query or "video").lower())[:32]
    target = "%s/%s/%s" % (MIGRATED_PREFIX, job, fname)
    sp.upload_file(BUILD_ASSET_DRIVE, target, data, "video/mp4")
    did = sp.drive_id(BUILD_ASSET_DRIVE)
    r = requests.get("https://graph.microsoft.com/v1.0/drives/%s/root:/%s?$select=webUrl"
                     % (did, target), headers=sp.H)
    return r.json().get("webUrl") if r.status_code < 300 else None


def section(layout, columns_webparts, emphasis="none", sid=None):
    """columns_webparts: list of webpart-lists, one per column."""
    widths = LAYOUT_WIDTHS[layout]
    if len(columns_webparts) != len(widths):
        raise ValueError("layout %s needs %d columns, got %d"
                         % (layout, len(widths), len(columns_webparts)))
    cols = []
    for i, (w, wps) in enumerate(zip(widths, columns_webparts), start=1):
        cols.append({"id": str(i), "width": w, "webparts": wps})
    return {"id": str(sid or uuid.uuid4().int % 100000),
            "emphasis": emphasis, "layout": layout, "columns": cols}


# --------------------------------------------------------------------------- #
# content model: group markers into hero / news / main / sidebar buckets
# --------------------------------------------------------------------------- #
NEWS_HINTS = ("news", "campaign", "launch", "kickoff", "deck", "kit",
              "onboarding", "results", "march", "april", "apr ")
SIDEBAR_HINTS = ("contact it", "service desk", "ext", "key document",
                 "quick link", "upcoming event", "event")


def classify_markers(markers):
    """Return (hero_title, main[], news[], sidebar[]). Heuristic + order-preserving.
    Every marker is placed exactly once so none are dropped (gate requirement)."""
    hero = None
    main, news, sidebar = [], [], []
    for m in markers:
        low = m.lower()
        if hero is None and len(m) <= 12 and "\n" not in m:
            hero = m  # first short marker (e.g. "Home") is the page/hero title
            continue
        if any(h in low for h in SIDEBAR_HINTS):
            sidebar.append(m)
        elif any(h in low for h in NEWS_HINTS):
            news.append(m)
        else:
            main.append(m)
    return hero or (markers[0] if markers else "Home"), main, news, sidebar


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


_COPY_WORD = re.compile(r"[A-Za-z0-9@.+%/&-]+")
_COPY_STRIP = re.compile(r"<[^>]+>")


def _copy_tokens(t):
    """Significant verbatim tokens for fidelity scoring (deterministic)."""
    import html as _h
    txt = _h.unescape(_COPY_STRIP.sub(" ", t or ""))
    out = []
    for w in _COPY_WORD.findall(txt):
        wl = w.lower().strip(".")
        if not wl:
            continue
        if len(wl) >= 2 or re.search(r"[0-9@%]", wl):
            out.append(wl)
    return out


def copy_coverage(source_text, build_html):
    """Fraction of the SOURCE's significant tokens that appear verbatim in the
    build page HTML (multiplicity-aware). Returns (ratio, missing[], total)."""
    from collections import Counter
    src = _copy_tokens(source_text)
    if not src:
        return 1.0, [], 0
    have = Counter(_copy_tokens(build_html))
    seen = Counter()
    present, missing = 0, []
    for w in src:
        if seen[w] < have[w]:
            present += 1
            seen[w] += 1
        else:
            missing.append(w)
    return present / len(src), missing, len(src)


# --------------------------------------------------------------------------- #
# VERBATIM composer — build from sp-expect.json `content[]` (ordered source
# blocks carrying the EXACT copy) instead of heuristic markers. Each block's
# real text lands in a web part; News items -> news grid, Quick Links/Contacts/
# Events/Documents -> sidebar, Welcome/CEO/intro -> hero+main, by the source's
# OWN structure. No filler, no paraphrase, no cross-contamination.
# --------------------------------------------------------------------------- #
# "pub-field" = a classic publishing field-control region (rich-text body / image
# field), extracted verbatim by sp-audit's _publishing_blocks. It renders in the
# MAIN column exactly like a "section" so a publishing page flows through the SAME
# composer + completeness gate as an article page (JOB0024-109).
# "listview" = a STATIC SNAPSHOT of a classic XsltListViewWebPart / ContentByQuery
# list, extracted verbatim by sp-audit's _listview_blocks (JOB0024-109). A link
# list renders as a verbatim <ul> of <a> items, a data list as a verbatim <ul> of
# text rows — both flow through the MAIN column exactly like a "section" so a
# list-driven page goes through the SAME composer + completeness gate.
MAIN_KINDS = {"welcome", "section", "pub-field", "listview"}
SIDEBAR_KINDS = {"quicklinks", "contacts", "events", "documents", "brands"}

# JOB0024-109 sub-task 3: classic HomeTiles (a grid of image+label+link tiles) and a
# classic banner (one large image + title + tagline + link) have NATIVE modern
# equivalents — Quick Links and Hero — so they flip flag->buildable. (CarouselWebPart
# does NOT: its modern equivalent needs an SPFx web part whose source is missing +
# toolchain broken, so a carousel page STAYS flagged 'carousel-spfx' upstream in
# triage; the composer never receives a 'carousel' block.)
_TILE_A = re.compile(
    r'<a\b[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>', re.I | re.S)


def _tile_items(block):
    """Extract ordered {title,url} tiles from a HomeTiles block. Prefers the block's
    parsed items[] (each {title,url|href}); else parses the block html's <a> tags
    (the tile label is the anchor's text with any nested <img> stripped). Verbatim —
    every tile's label + link round-trips."""
    out = []
    for it in (block.get("items") or []):
        title = (it.get("title") or it.get("text") or "").strip()
        url = (it.get("url") or it.get("href") or "").strip()
        if title:
            out.append({"title": title, "url": url})
    if out:
        return out
    html_src = block.get("html") or ""
    for m in _TILE_A.finditer(html_src):
        url = (m.group(1) or "").strip()
        label = re.sub(r"<[^>]+>", " ", m.group(2) or "")
        label = re.sub(r"\s+", " ", label).strip()
        if label:
            out.append({"title": label, "url": "" if url in ("#", "") else url})
    return out


def tiles_from_blocks(block, heading=""):
    """Map a classic HomeTiles block (image+label+link tiles) to a NATIVE Quick Links
    web part. Returns a quicklinks_wp web part (its titles+urls live in
    serverProcessedContent, which the fidelity gate folds in), or None if no tile has
    a label. <=8 tiles (Quick Links cap); overflow tiles are appended verbatim as a
    text web part by the caller's section so nothing is dropped."""
    items = _tile_items(block)
    if not items:
        return None
    heading = heading or (block.get("heading") or "").strip() or "Quick links"
    return quicklinks_wp(items[:8], heading=heading)


def banner_from_blocks(block, image_map, site_id=""):
    """Map a classic banner block (one large image + title + tagline + link) to a
    NATIVE Hero web part. title (the banner heading) + tagline (its copy) land verbatim
    in serverProcessedContent; the banner image becomes the hero background. Returns a
    hero_wp web part."""
    title = (block.get("heading") or block.get("title") or "").strip()
    tagline = (block.get("text") or block.get("tagline") or "").strip()
    link_url = (block.get("url") or block.get("link") or "").strip()
    img = _img_for(block, image_map)
    image_url = img["url"] if img else ""
    if not title and tagline:
        title, tagline = tagline, ""
    return hero_wp(title, tagline=tagline, image_url=image_url, link_url=link_url)


def _block_html(block):
    """The block's verbatim, SP-clean HTML — falls back to escaped text if the
    cleaner produced nothing. A leading <h2> heading is added when the source had
    one and it isn't already the first tag."""
    body = (block.get("html") or "").strip()
    if not body:
        body = "<p>%s</p>" % esc(block.get("text", ""))
    heading = (block.get("heading") or "").strip()
    if heading and not re.match(r"(?is)^\s*<h[1-4]\b", body):
        body = "<h2>%s</h2>\n%s" % (esc(heading), body)
    return body


# Source image natural dims (from enrich.json), keyed by source src. Images narrower
# than _FEATURE_MIN_W are NOT promoted to a hero/feature Image web part — a small asset
# (e.g. a 159px signature) blown up full-width looks broken. They stay INLINE in the
# verbatim body HTML where the source placed them.
_IMG_DIMS = {}
_FEATURE_MIN_W = 400


def _img_for(block, image_map):
    """First migrated image URL for a block that is large enough to FEATURE
    (build-site URL), or None. Known-small images are skipped (kept inline only)."""
    for im in block.get("images", []) or []:
        src = im.get("src")
        url = image_map.get(src)
        if not url:
            continue
        w = (_IMG_DIMS.get(src) or {}).get("w") or 0
        if w and w < _FEATURE_MIN_W:
            continue  # too small to feature — leave it inline in the body copy
        return {"url": url, "alt": im.get("alt", "")}
    return None


def build_canvas_from_content(page_spec, image_map, site_id):
    """Compose the page from `content[]` VERBATIM, mapped to hero/main/sidebar/news.
    Returns None if the page has no content[] (caller falls back to markers)."""
    content = page_spec.get("content") or []
    if not content:
        return None

    intro = next((b for b in content if b.get("kind") == "intro"), None)
    news_blocks = [b for b in content if b.get("kind") == "news"]
    main_blocks = [b for b in content
                   if b.get("kind") in MAIN_KINDS and b is not intro]
    side_blocks = [b for b in content if b.get("kind") in SIDEBAR_KINDS]
    # JOB0024-109/3: classic HomeTiles / banner blocks -> native Quick Links / Hero.
    banner_blocks = [b for b in content if b.get("kind") == "banner"]
    tiles_blocks = [b for b in content if b.get("kind") == "tiles"]

    sections = []

    # 1) HERO — full-width. A classic 'banner' block renders as a NATIVE Hero web part
    #    (image background + verbatim title/tagline). Otherwise the intro image + intro
    #    copy lead the page exactly as before.
    if banner_blocks:
        sections.append(section(
            "oneColumn",
            [[banner_from_blocks(banner_blocks[0], image_map, site_id)]],
            emphasis="neutral", sid="1"))
    else:
        hero_img = _img_for(intro, image_map) if intro else None
        hero_col = []
        if hero_img:
            hero_col.append(image_wp(hero_img["url"], hero_img["alt"], site_id))
        # page title as the hero <h1> (so the title marker has a home), then the
        # source's own intro/banner copy verbatim beneath it.
        title = esc(page_spec.get("title", "") or "")
        intro_html = _block_html(intro) if intro else ""
        hero_col.append(text_wp(("<h1>%s</h1>\n%s" % (title, intro_html)).strip()))
        sections.append(section("oneColumn", [hero_col], emphasis="neutral", sid="1"))

    # 1b) TILES — classic HomeTiles grid -> a NATIVE Quick Links web part (one tile per
    #     link, label+url verbatim). >8 tiles overflow into a verbatim text web part so
    #     no tile is dropped (quicklinks_wp caps at 8). Carousel is NEVER here (flagged
    #     'carousel-spfx' in triage; SPFx-blocked).
    for tb in tiles_blocks:
        tiles_wp = tiles_from_blocks(tb)
        if not tiles_wp:
            continue
        col = [tiles_wp]
        overflow = _tile_items(tb)[8:]
        if overflow:
            extra = "".join('<li><a href="%s">%s</a> %s</li>'
                            % (esc(it["url"]), esc(it["title"]), esc(it["url"]))
                            for it in overflow)
            col.append(text_wp("<ul>%s</ul>" % extra))
        sections.append(section("oneColumn", [col], emphasis="none", sid="tiles"))

    # 2) MAIN (8) + SIDEBAR (4). Main = Welcome/CEO/other body blocks, verbatim.
    #    The CEO portrait (image inside the welcome block) renders as a native
    #    Image web part above the copy.
    if side_blocks:
        # main body + right rail (quicklinks/contacts/events) — intranet-home style
        main_col = []
        for b in main_blocks:
            bi = _img_for(b, image_map)
            if bi:
                main_col.append(image_wp(bi["url"], bi["alt"], site_id,
                                         caption=bi["alt"]))
            main_col.append(text_wp(_block_html(b)))
        if not main_col:
            main_col.append(text_wp("<p>&nbsp;</p>"))
        side_col = [text_wp(_block_html(b)) for b in side_blocks]
        sections.append(section("oneThirdRightColumn", [main_col, side_col],
                                emphasis="none", sid="2"))
    else:
        # text-only article (no sidebar content): each source section becomes its OWN
        # full-width band (its <h2> heading + verbatim body), with alternating
        # background emphasis for rhythm — so the page reads as distinct sections
        # instead of one identical wall of text.
        for idx, b in enumerate(main_blocks):
            col = []
            bi = _img_for(b, image_map)
            if bi:
                col.append(image_wp(bi["url"], bi["alt"], site_id, caption=bi["alt"]))
            col.append(text_wp(_block_html(b)))
            sections.append(section("oneColumn", [col],
                                    emphasis=("neutral" if idx % 2 else "none"),
                                    sid="s%d" % idx))
        if not main_blocks:
            sections.append(section("oneColumn", [[text_wp("<p>&nbsp;</p>")]],
                                    emphasis="none", sid="2"))

    # 3) NEWS GRID — heading section + a 1/2/3-column grid, one card per source
    #    news ITEM (its image + its verbatim headline/body/date/category).
    if news_blocks:
        nb = news_blocks[0]
        items = nb.get("items") or []
        if not items:
            # no per-row items -> emit the whole news block as one card
            items = [{"text": nb.get("text", ""), "html": nb.get("html", ""),
                      "images": nb.get("images", [])}]
        n = min(max(len(items), 1), 3)
        # pack items into n cards (extra items append to the last card, verbatim)
        cards_items = [[] for _ in range(n)]
        for idx, it in enumerate(items):
            cards_items[min(idx, n - 1)].append(it)
        cards = []
        for group in cards_items:
            col = []
            for it in group:
                bi = _img_for(it, image_map)
                if bi:
                    col.append(image_wp(bi["url"], bi["alt"], site_id))
                col.append(text_wp((it.get("html") or "").strip()
                                   or "<p>%s</p>" % esc(it.get("text", ""))))
            if not col:
                col.append(text_wp("<p>&nbsp;</p>"))
            cards.append(col)

        news_heading = nb.get("heading") or "Company News"
        sections.append(section("oneColumn",
                                [[text_wp("<h2>%s</h2>" % esc(news_heading))]],
                                emphasis="none", sid="3"))
        layout = {1: "oneColumn", 2: "twoColumns", 3: "threeColumns"}[n]
        sections.append(section(layout, cards, emphasis="none", sid="4"))

    return {"horizontalSections": sections}


# --------------------------------------------------------------------------- #
# SPEC-DRIVEN composer — build EXACTLY the ux-designer's design-spec.json.
# Each spec section is {layout, webpart, contentBlocks, image|video, ...}. The
# verbatim source copy still lands on the page (fidelity gate stays >=0.9): text
# web parts carry the block HTML verbatim; Hero/Quick Links carry their text in
# serverProcessedContent (which the gate folds into its search blob).
#
# design-spec.json SCHEMA (per page; the composer reads the page matching --page)
# {
#   "page": "Home.aspx",
#   "sections": [
#     { "layout": "fullWidth|oneColumn|twoColumns|threeColumns|
#                   oneThirdLeftColumn|oneThirdRightColumn",
#       "emphasis": "none|neutral|soft|strong",          # optional
#       "columns": [                                       # one entry per column
#         { "webpart": "hero|quicklinks|text|image|news|embed|fileviewer",
#           # --- hero ---
#           "title": "...", "tagline": "...",
#           "image": {"src": "<source-src in image-map>"} | {"url": "..."},
#           # --- text ---
#           "contentBlocks": ["<kind>", ...]  # pull these content[] blocks verbatim
#             | "blocks": [ {"heading","html"} ],
#           # --- quicklinks ---
#           "links": [ {"title","url","description"} ]      # else derived from a
#             "fromBlock": "quicklinks"  block's <a> tags (<=8, overflow note)
#           # --- image ---
#           "image": {"src"|"url", "alt", "caption"},
#           # --- news ---
#           "fromBlock": "news",                            # builds the card grid
#           # --- embed / fileviewer (video) ---
#           "video": {"query": "pexels search terms"}       # judicious; downloads+
#             | {"url": "<already-hosted mp4>"}              # uploads then renders
#         }, ...
#       ]
#     }, ...
#   ]
# }
# A bare section may use "webpart"/"title"/... at the top level as a shorthand for
# a single oneColumn/fullWidth column.
# --------------------------------------------------------------------------- #
_A_TAG = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>',
                    re.I | re.S)


def _links_from_block(block, limit=8):
    """Extract <=limit {title,url} link items from a block's html (its <a> tags).
    Falls back to splitting plain text lines. Returns (items, overflow_count)."""
    items = []
    html = block.get("html", "") or ""
    for m in _A_TAG.finditer(html):
        url = (m.group(1) or "").strip()
        title = re.sub(r"<[^>]+>", "", m.group(2) or "").strip()
        if title:
            items.append({"title": title, "url": "" if url in ("#", "") else url})
    if not items:
        for line in re.split(r"[\n]+", block.get("text", "") or ""):
            line = line.strip()
            if line:
                items.append({"title": line, "url": ""})
    overflow = max(0, len(items) - limit)
    return items[:limit], overflow


def _resolve_image(spec_img, image_map):
    """spec image -> {url, alt, caption} resolving a source 'src' via image_map."""
    if not spec_img:
        return None
    url = spec_img.get("url")
    if not url and spec_img.get("src"):
        url = image_map.get(spec_img["src"])
    if not url:
        return None
    return {"url": url, "alt": spec_img.get("alt", ""),
            "caption": spec_img.get("caption", "")}


_WORD_RE = re.compile(r"[a-z0-9@]+")


def _norm_words(html):
    """Lowercased word set from an HTML/text fragment (tags + entities stripped),
    for detecting when two blocks carry substantially the SAME copy."""
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return set(_WORD_RE.findall(txt.lower()))


def _is_dup(words, emitted_word_sets):
    """True if `words` is largely contained in one already-emitted block's words
    (>=0.8 overlap) — i.e. this block restates copy already on the page."""
    if not words:
        return False
    for ws in emitted_word_sets:
        if not ws:
            continue
        overlap = len(words & ws) / len(words)
        if overlap >= 0.8:
            return True
    return False


def _blocks_html_verbatim(col, content_by_kind):
    """Emit a column's HTML, VERBATIM-first and DE-DUPLICATED.

    A spec column can name 'contentBlocks' (verbatim source copy, by kind) AND carry
    inline 'blocks' (the designer's curated presentation). Sometimes these are the
    SAME content (the sidebar's documents/contacts/brands) and sometimes DIFFERENT
    (the CEO column = verbatim 'welcome' copy + a distinct CEO-quote block). Emitting
    every block unconditionally duplicated the sidebar on the live JOB0022 page; only
    keeping the inline blocks dropped the verbatim 'welcome' copy (fidelity fell).

    So: emit the VERBATIM contentBlocks first (copy is sacred -> keeps fidelity), then
    add each inline block ONLY if it isn't substantially the same copy as something
    already emitted. Distinct curated blocks (CEO quote) survive; mirror blocks
    (Key Documents / Contact IT / Our Brands) are skipped as duplicates."""
    out = []
    emitted = []  # word-sets of what we've emitted, for dedup
    for kind in (col.get("contentBlocks") or []):
        b = content_by_kind.get(kind)
        if b:
            h = _block_html(b)
            out.append(h)
            emitted.append(_norm_words(h))
    for b in (col.get("blocks") or []):
        h = _block_html(b)
        if _is_dup(_norm_words(h), emitted):
            continue
        out.append(h)
        emitted.append(_norm_words(h))
    if col.get("html"):
        out.append(col["html"])
    return "\n".join(out)


def _build_col_webparts(col, ctx):
    """Build the web part(s) for ONE spec column. ctx carries image_map, site_id,
    content_by_kind, sp, job, and a 'notes' list for overflow/fallback messages."""
    # Support design-spec webParts[] format: "type" is an alias for "webpart".
    kind = (col.get("webpart") or col.get("type") or "text").lower()
    image_map, site_id = ctx["image_map"], ctx["site_id"]
    content_by_kind = ctx["content_by_kind"]
    wps = []

    if kind == "hero":
        # HERO IS THE NATIVE PAGE-TITLE HEADER (titleArea), NOT a separate web part.
        # See set_title_area_hero(): the page's native title band carries the brand
        # image as its background + the company-led title. So a spec "hero" column
        # emits NO canvas web part here — it's a no-op (the verbatim intro/banner copy
        # lands via the intro content[] block elsewhere / titleArea title). Returning
        # a sentinel tells the caller to DROP this column entirely (no empty wrapper).
        return ("__titlehero__", col)

    elif kind == "quicklinks":
        items = col.get("links")
        overflow = 0
        if not items and col.get("fromBlock"):
            b = content_by_kind.get(col["fromBlock"])
            if b:
                items, overflow = _links_from_block(b, col.get("limit", 8))
        items = (items or [])[:col.get("limit", 8)]
        if overflow:
            ctx["notes"].append(
                "quicklinks: %d link(s) over the %d cap omitted (overflow)"
                % (overflow, col.get("limit", 8)))
        heading = col.get("heading") or "Quick links"
        wps.append(quicklinks_wp(items, heading=heading))

    elif kind == "listview":
        # STATIC list-view snapshot (JOB0024-109). Pull the verbatim 'listview'
        # content block (by name or kind) and render it: a LINK list goes through
        # the native Quick Links web part (titles+urls carried in serverProcessedContent,
        # which the gate folds in); a DATA list (no <a> tags) stays a verbatim text
        # web part. Either way every item title/href round-trips.
        b = content_by_kind.get(col.get("fromBlock", "listview"))
        if b:
            items, overflow = _links_from_block(b, col.get("limit", 8))
            has_links = any((it.get("url") or "").strip() for it in items)
            if has_links:
                if overflow:
                    ctx["notes"].append(
                        "listview: %d link(s) over the %d cap rendered as text overflow"
                        % (overflow, col.get("limit", 8)))
                wps.append(quicklinks_wp(items, heading=col.get("heading")
                                         or b.get("heading") or "Quick links"))
                if overflow:  # keep the overflow links verbatim in a text wp (gate)
                    wps.append(text_wp(_block_html(b)))
            else:
                wps.append(text_wp(_block_html(b)))

    elif kind == "image":
        # Support both nested {"image": {"src": ...}} and flat {"src": ..., "type": "image"}
        # (the latter is the design-spec webParts[] format).
        img_spec = col.get("image") or (
            {"src": col["src"], "alt": col.get("alt", ""), "caption": col.get("caption", "")}
            if col.get("src") else None)
        img = _resolve_image(img_spec, image_map)
        if img:
            wps.append(image_wp(img["url"], img["alt"], site_id,
                                caption=img.get("caption", "")))

    elif kind in ("embed", "fileviewer"):
        video = col.get("video") or {}
        url = video.get("url")
        if not url and video.get("query") and ctx.get("sp") and ctx.get("job"):
            url = upload_video_to_build(ctx["sp"], ctx["job"], video["query"])
        if url:
            if kind == "fileviewer":
                wps.append(fileviewer_wp(url, video.get("fileType", "mp4")))
            else:
                wps.append(embed_wp(src_url=url,
                                    embed_code=video.get("embedCode", "")))
        else:
            ctx["notes"].append(
                "video: no source resolved for %s -> column left empty" % kind)

    elif kind == "news":
        # reuse the clean image-card grid from the content composer. Returns a
        # LIST of sections (heading + grid); flagged so the caller appends them.
        b = content_by_kind.get(col.get("fromBlock", "news"))
        return ("__news__", b)

    else:  # text (default) — verbatim block copy + optional inline image
        img = _resolve_image(col.get("image"), image_map)
        if img:
            wps.append(image_wp(img["url"], img["alt"], site_id,
                                caption=img.get("caption", "")))
        # Support "contentIndex" (design-spec article format): select a content[] block
        # by positional index and emit it verbatim. Falls back to contentBlocks/blocks.
        ci = col.get("contentIndex")
        if ci is not None:
            try:
                ci = int(ci)   # design-spec often stores it as a STRING ("0")
            except (TypeError, ValueError):
                ci = None
        if ci is not None:
            # content_by_kind is keyed by kind; re-derive ordered list from ctx
            ordered = ctx.get("_content_ordered") or []
            b = ordered[ci] if (ordered and 0 <= ci < len(ordered)) else None
            html = _block_html(b) if b else ""
        else:
            html = _blocks_html_verbatim(col, content_by_kind)
            # Thin article spec = a bare {webpart:text} with no content reference. The
            # source body is N content[] blocks ALL keyed kind="section" — content_by_kind
            # collapses them to the first, so a bare text col would drop the rest of the
            # article body. When no explicit content is named, render the FULL ordered
            # source body verbatim (the article-body fidelity path).
            if (not html.strip() and not col.get("contentBlocks") and not col.get("blocks")
                    and not col.get("html") and col.get("contentIndex") is None):
                ordered = ctx.get("_content_ordered") or []
                html = "\n".join(_block_html(b) for b in ordered if b)
        if html.strip():
            wps.append(text_wp(html))

    if not wps:
        wps.append(text_wp("<p>&nbsp;</p>"))
    return wps


def _news_sections(news_block, image_map, site_id):
    """The clean image-card news grid (heading section + 1/2/3-col grid)."""
    if not news_block:
        return []
    items = news_block.get("items") or []
    if not items:
        items = [{"text": news_block.get("text", ""),
                  "html": news_block.get("html", ""),
                  "images": news_block.get("images", [])}]
    n = min(max(len(items), 1), 3)
    cards_items = [[] for _ in range(n)]
    for idx, it in enumerate(items):
        cards_items[min(idx, n - 1)].append(it)
    cards = []
    for group in cards_items:
        col = []
        for it in group:
            bi = _img_for(it, image_map)
            if bi:
                col.append(image_wp(bi["url"], bi["alt"], site_id))
            col.append(text_wp((it.get("html") or "").strip()
                               or "<p>%s</p>" % esc(it.get("text", ""))))
        if not col:
            col.append(text_wp("<p>&nbsp;</p>"))
        cards.append(col)
    heading = news_block.get("heading") or "Company News"
    secs = [section("oneColumn", [[text_wp("<h2>%s</h2>" % esc(heading))]],
                    emphasis="none")]
    layout = {1: "oneColumn", 2: "twoColumns", 3: "threeColumns"}[n]
    secs.append(section(layout, cards, emphasis="none"))
    return secs


def build_canvas_from_spec(design_spec, page_name, page_spec, image_map,
                           site_id, sp=None, job=None, hero_title="",
                           hero_image=None):
    """Build the canvasLayout EXACTLY from the ux-designer's design-spec.json.
    Returns (canvas, notes) or (None, []) if no spec section matches this page.

    `hero_title`/`hero_image` describe the NATIVE page-title header (the hero). They
    are NOT placed on the canvas (the header is separate from canvasLayout), but the
    marker-safety net below counts markers covered by the hero_title as present so it
    doesn't redundantly re-add the banner words onto the canvas."""
    # find the page entry (design-spec may be a single page or {pages:[...]})
    pages = design_spec.get("pages") if isinstance(design_spec, dict) else None
    spec = None
    if pages:
        spec = next((p for p in pages
                     if (p.get("page") or "").lower() == page_name.lower()), None)
    elif (design_spec.get("page") or "").lower() in ("", page_name.lower()):
        spec = design_spec
    if not spec or not spec.get("sections"):
        return None, []

    content_by_kind = {}
    content_ordered = page_spec.get("content") or []
    for b in content_ordered:
        content_by_kind.setdefault(b.get("kind"), b)
    ctx = {"image_map": image_map, "site_id": site_id,
           "content_by_kind": content_by_kind, "sp": sp, "job": job,
           "page_title": page_spec.get("title", ""), "notes": [],
           "_content_ordered": content_ordered}

    sections = []
    for sec in spec["sections"]:
        layout = sec.get("layout") or "oneColumn"
        if layout not in LAYOUT_WIDTHS:
            ctx["notes"].append("unknown layout %r -> oneColumn" % layout)
            layout = "oneColumn"
        emphasis = sec.get("emphasis", "none")
        # normalize: top-level single-webpart shorthand -> one column.
        # Also accept "webParts" (design-spec article format) as an alias for "columns".
        cols = sec.get("columns") or sec.get("webParts")
        if not cols:
            cols = [dict(sec)]
        ncols = len(LAYOUT_WIDTHS[layout])
        # pad/trim columns to the layout's column count
        if len(cols) < ncols:
            cols = cols + [{"webpart": "text", "html": "<p>&nbsp;</p>"}
                           ] * (ncols - len(cols))
        elif len(cols) > ncols:
            ctx["notes"].append(
                "section has %d columns but layout %s allows %d -> extra trimmed"
                % (len(cols), layout, ncols))
            cols = cols[:ncols]

        col_wps = []
        deferred_news = []
        for c in cols:
            built = _build_col_webparts(c, ctx)
            if isinstance(built, tuple) and built and built[0] == "__news__":
                deferred_news.append(built[1])
                col_wps.append(None)  # sentinel -> column held a news grid
            elif isinstance(built, tuple) and built and built[0] == "__titlehero__":
                # HERO -> native page-title header (titleArea), not a canvas section.
                # Drop the column entirely; the titleArea is set in apply_page.
                continue
            else:
                col_wps.append(built)
        # If EVERY column was a news grid (a pure-news section), emit only the
        # news sections (no empty wrapper). Otherwise keep the section, filling
        # news-held columns with a spacer so the real columns render correctly.
        if not col_wps and not deferred_news:
            # the whole section was the hero -> emit nothing (native header is hero)
            continue
        if any(w is not None for w in col_wps):
            sections.append(section(
                layout, [w if w is not None else [text_wp("<p>&nbsp;</p>")]
                         for w in col_wps], emphasis=emphasis))
        for nb in deferred_news:
            sections.extend(_news_sections(nb, image_map, site_id))

    # MARKER SAFETY NET — the conversion gate asserts every source markers[]
    # entry survives onto the page. Most land via the verbatim content[] blocks,
    # but a page-label/title marker (e.g. "Home") may not appear in any block's
    # copy. Surface any still-missing markers (faithfully — they ARE source
    # headings/labels) so nothing is dropped: fold them into the Hero tile's
    # accessible text if a hero exists, else add a small heading text web part.
    markers = page_spec.get("markers", []) or []
    if markers:
        # the native title header (hero) carries hero_title verbatim — count its
        # words as present so banner markers covered by the header aren't re-added.
        header_blob = (hero_title or "").lower()
        blob = json.dumps({"s": sections}, ensure_ascii=False).lower() + " " + header_blob
        # "Home" is SharePoint's old default page label, NOT source banner copy that
        # belongs on the body — the company-led header replaced it; never re-add it.
        missing = [m for m in markers
                   if m.lower() not in blob and m.strip().lower() != "home"]
        if missing:
            # render the still-missing banner copy as a clean intro/tagline text
            # web part at the very top of the body (verbatim source words), so the
            # fidelity gate counts them and the page opens with the brand tagline
            # right under the native hero header.
            extra = " &middot; ".join(esc(m) for m in missing)
            intro_html = ('<p style="font-size:15px;color:#444;margin:0 0 4px;">'
                          '%s</p>' % extra)
            if sections:
                sections[0]["columns"][0]["webparts"].insert(0, text_wp(intro_html))
            else:
                sections.append(section("oneColumn", [[text_wp(intro_html)]],
                                        emphasis="none", sid="introbanner"))
            ctx["notes"].append("added intro/tagline text wp for banner marker(s): %s"
                                % "  ".join(missing))

    # CONTENT SAFETY NET — the design-spec may address only SOME content[] blocks
    # (e.g. a single contentIndex=0), silently dropping the rest of the article body.
    # Append any source content block whose copy isn't already on the page, so the FULL
    # body survives (mirrors the marker + image nets; source copy is sacred).
    placed_txt = json.dumps({"s": sections}, ensure_ascii=False).lower()
    body_html = []
    for b in (page_spec.get("content") or []):
        bt = (b.get("text") or "").strip()
        if not bt or len(bt) < 25:
            continue
        probe = " ".join(bt.lower().split()[:8])
        if probe and probe not in placed_txt:
            body_html.append(_block_html(b))
    if body_html:
        sections.append(section("oneColumn", [[text_wp("\n".join(body_html))]],
                                emphasis="none", sid="bodynet"))
        ctx["notes"].append("CONTENT SAFETY NET: appended %d unplaced source body block(s)"
                            % len(body_html))

    # IMAGE SAFETY NET — mirror the marker net for images. The completeness gate +
    # verify_structure assert every page_spec['images'] entry (reconciled to the
    # live-capture manifest, the gate's source-of-truth) lands on the page. Most
    # arrive via spec image columns, but a manifest-merged image with no spec column
    # would otherwise be migrated yet never placed. Append any still-unplaced source
    # image as a trailing image web part so nothing in the set is dropped.
    placed_blob = json.dumps({"s": sections}, ensure_ascii=False)
    unplaced = []
    for im in page_spec.get("images", []):
        url = image_map.get(im.get("src"))
        if url and url not in placed_blob:
            unplaced.append({"url": url, "alt": im.get("alt", "")})
    if unplaced:
        for u in unplaced:
            sections.append(section("oneColumn",
                                    [[image_wp(u["url"], u["alt"], site_id)]],
                                    emphasis="none", sid="imgnet"))
        ctx["notes"].append("IMAGE SAFETY NET: placed %d unplaced source image(s): %s"
                            % (len(unplaced),
                               ", ".join(u["url"].rsplit("/", 1)[-1] for u in unplaced)))

    # FOOTER — every design keeps the source footer (DESIGN-PLAYBOOK rule). The
    # designer puts the verbatim footer line in design_spec["footer"]; we render
    # it as a full-width text web part at the very bottom. Skipped only if the
    # spec omits it (no footer authored).
    footer = (spec.get("footer") or design_spec.get("footer") or "").strip() \
        if isinstance(spec, dict) else ""
    if footer:
        f_html = ('<p style="text-align:center;color:#666;font-size:12px;">%s</p>'
                  % esc(footer))
        sections.append(section("oneColumn", [[text_wp(f_html)]],
                                emphasis="neutral", sid="footer"))
        ctx["notes"].append("appended footer section")

    return {"horizontalSections": sections}, ctx["notes"]


# Web part types that count toward the Graph 400 threshold.
_HEAVY_WP_TYPES = {IMAGE_WEBPART_GUID, HERO_WEBPART_GUID,
                   QUICKLINKS_WEBPART_GUID, EMBED_WEBPART_GUID,
                   FILEMEDIA_WEBPART_GUID}


def plan_heavy_webpart_batches(canvas, page_title=""):
    """Partition the canvas into ≤MAX_HEAVY_WEBPARTS_PER_PAGE-heavy batches.

    Nothing is dropped.  Walks sections in order.  The first batch gets sections
    until the next section would push the heavy count over the cap — at that point
    the remaining sections become subsequent batches (same rule applied
    recursively).  A single section whose own heavy count exceeds the cap is kept
    intact in one batch (we cannot split a section; Graph accepts it as-is or
    fails, but we never discard it).

    Returns a list of canvases (each a {"horizontalSections": [...]}) in order.
    If the total heavy count ≤ cap the list has exactly one entry (unchanged).
    Callers use the first canvas for the initial POST/PATCH, then PATCH-append the
    rest via _patch_existing_page / _append_canvas_batches.
    """
    import copy as _copy
    sections = canvas.get("horizontalSections", []) or []
    if not sections:
        return [canvas]

    def _count_heavy(secs):
        n = 0
        for s in secs:
            for c in s.get("columns", []) or []:
                for wp in c.get("webparts", []) or []:
                    if wp.get("webPartType") in _HEAVY_WP_TYPES:
                        n += 1
        return n

    total = _count_heavy(sections)
    if total <= MAX_HEAVY_WEBPARTS_PER_PAGE:
        return [canvas]

    # Partition sections greedily: accumulate into the current batch until
    # adding the next section would push it over the cap.
    batches = []
    cur_secs = []
    cur_heavy = 0
    for sec in sections:
        sec_heavy = _count_heavy([sec])
        if cur_secs and cur_heavy + sec_heavy > MAX_HEAVY_WEBPARTS_PER_PAGE:
            batches.append({"horizontalSections": cur_secs})
            cur_secs = []
            cur_heavy = 0
        cur_secs.append(sec)
        cur_heavy += sec_heavy
    if cur_secs:
        batches.append({"horizontalSections": cur_secs})

    print("[BATCH] total heavy web parts=%d; splitting into %d batch(es) of ≤%d "
          "(page: %s)" % (total, len(batches), MAX_HEAVY_WEBPARTS_PER_PAGE,
                          page_title or "?"))
    for i, b in enumerate(batches):
        print("[BATCH]   batch %d/%d: %d section(s), %d heavy web part(s)"
              % (i + 1, len(batches), len(b["horizontalSections"]),
                 _count_heavy(b["horizontalSections"])))
    return batches


def build_canvas(page_spec, image_map, site_id, design_spec=None,
                 page_name="Home.aspx", sp=None, job=None, hero_title="",
                 hero_image=None):
    """Compose the canvasLayout for one page. PRIORITY:
      1. design-spec.json (the ux-designer's ordered sections/web parts) — build
         EXACTLY that.
      2. VERBATIM content[] heuristic auto-layout (hero/main+sidebar/news).
      3. legacy marker-based layout (oldest audits, no content[]).
    hero_title/hero_image describe the native page-title header (the hero); they let
    the spec marker-net know which banner words the header already covers."""
    if design_spec is not None:
        canvas, notes = build_canvas_from_spec(
            design_spec, page_name, page_spec, image_map, site_id, sp, job,
            hero_title=hero_title, hero_image=hero_image)
        if canvas is not None:
            if notes:
                print("SPEC NOTES:", "; ".join(notes))
            return canvas
    verbatim = build_canvas_from_content(page_spec, image_map, site_id)
    if verbatim is not None:
        return verbatim
    markers = page_spec.get("markers", [])
    images = page_spec.get("images", [])
    # resolve migrated image URLs in order
    img_urls = []
    for im in images:
        url = image_map.get(im.get("src"))
        if url:
            img_urls.append({"url": url, "alt": im.get("alt", "")})

    hero, main_mk, news_mk, side_mk = classify_markers(markers)
    # image allocation: [0]=hero, [1]=CEO portrait in MAIN, rest=news cards.
    # Guarantees every migrated image lands somewhere (gate counts all of them).
    hero_img = img_urls[0] if img_urls else None
    ceo_img = img_urls[1] if len(img_urls) > 1 else None
    news_imgs = img_urls[2:] if len(img_urls) > 2 else []

    sections = []

    # 1) HERO — full-width image + heading
    hero_col = []
    if hero_img:
        hero_col.append(image_wp(hero_img["url"], hero_img["alt"], site_id))
    hero_col.append(text_wp("<h1>%s</h1><p>Welcome to the team intranet.</p>"
                            % esc(hero)))
    sections.append(section("oneColumn", [hero_col], emphasis="neutral", sid="1"))

    # 2) MAIN (8) + SIDEBAR (4) two-column section
    main_html = ["<h2>Welcome &amp; CEO Message</h2>"]
    for m in main_mk:
        main_html.append("<p>%s</p>" % esc(m))
    if not main_mk:
        main_html.append("<p>%s</p>" % esc(hero))
    main_col = []
    if ceo_img:
        main_col.append(image_wp(ceo_img["url"], ceo_img["alt"], site_id,
                                 caption="A message from our CEO"))
    main_col.append(text_wp("".join(main_html)))

    side_html = ["<h2>Key Documents &amp; Contacts</h2>", "<ul>"]
    for m in side_mk:
        side_html.append("<li>%s</li>" % esc(m))
    side_html.append("</ul>")
    if not side_mk:
        side_html = ["<h2>Quick Links</h2><p>See company resources.</p>"]
    side_col = [text_wp("".join(side_html))]

    sections.append(section("oneThirdRightColumn", [main_col, side_col],
                            emphasis="none", sid="2"))

    # 3) NEWS GRID — three columns, each: image + bold headline + text
    if news_mk or news_imgs:
        # build up to 3 news cards
        n = max(len(news_imgs), min(3, len(news_mk)), 1)
        n = min(n, 3)
        cards = [[] for _ in range(n)]
        # distribute images
        for i in range(n):
            if i < len(news_imgs):
                cards[i].append(image_wp(news_imgs[i]["url"],
                                         news_imgs[i]["alt"], site_id))
        # distribute news text markers across cards (headline = first sentence)
        per = (len(news_mk) + n - 1) // n if news_mk else 0
        for i in range(n):
            chunk = news_mk[i * per:(i + 1) * per] if per else []
            html = []
            for j, m in enumerate(chunk):
                if j == 0:
                    html.append("<p><strong>%s</strong></p>" % esc(m))
                else:
                    html.append("<p>%s</p>" % esc(m))
            if html:
                cards[i].append(text_wp("".join(html)))
            elif not cards[i]:
                cards[i].append(text_wp("<p>&nbsp;</p>"))
        # any leftover markers beyond per*n -> append to last card
        used = per * n
        if news_mk and used < len(news_mk):
            extra = "".join("<p>%s</p>" % esc(m) for m in news_mk[used:])
            cards[-1].append(text_wp(extra))

        layout = {1: "oneColumn", 2: "twoColumns", 3: "threeColumns"}[n]
        # news header section first (full width)
        sections.append(section("oneColumn",
                                 [[text_wp("<h2>Company News</h2>")]],
                                 emphasis="none", sid="3"))
        sections.append(section(layout, cards, emphasis="none", sid="4"))

    return {"horizontalSections": sections}


# --------------------------------------------------------------------------- #
# apply + publish
# --------------------------------------------------------------------------- #
def find_page(sp, sid, name):
    for api in ("v1.0", "beta"):
        r = requests.get("https://graph.microsoft.com/%s/sites/%s/pages?$select=id,name,title&$top=200"
                         % (api, sid), headers=sp.H)
        if r.status_code < 300:
            for p in r.json().get("value", []):
                if (p.get("name") or "").lower() == name.lower():
                    return p["id"], api
            return None, api
    return None, "v1.0"


def _fresh_name(basename, attempt):
    """Return a deterministic page name for retry attempt N.
    attempt=0  -> original name unchanged.
    attempt=N  -> <stem>-rN+1.<ext>  e.g. attempt=1 -> "Home-r2.aspx"
    Deterministic and reproducible: same failed-compose + retry sequence always
    picks the same name, so re-running the pipeline is idempotent.
    Any previous -rN suffix is stripped before appending the new one.
    """
    if attempt == 0:
        return basename
    dot = basename.rfind(".")
    if dot > 0:
        stem, ext = basename[:dot], basename[dot:]
    else:
        stem, ext = basename, ""
    stem = re.sub(r"-r\d+$", "", stem)
    return "%s-r%d%s" % (stem, attempt + 1, ext)


def derive_title_hero(page_spec, design_spec, image_map, page_name):
    """Derive the NATIVE page-title header's (titleArea) content from the source:
      - title: the source banner, COMPANY-LED — built from the intro block's
        heading (the company name) + its distinctive descriptor (e.g. 'Global
        Intranet Portal'), verbatim source words. NOT "Home".
      - image: the hero image as the header BACKGROUND — the spec hero column's
        image, else the intro block's first image, resolved to the migrated
        build-site URL via image_map.
    Returns (title, image_url). Either may be "" / None if unavailable."""
    content = page_spec.get("content") or []
    intro = next((b for b in content if b.get("kind") == "intro"), None)

    # --- title (company-led) ---
    title = ""
    heading = (intro.get("heading") or "").strip() if intro else ""
    # the source banner descriptor: prefer the source markers[] phrase that names
    # the portal/intranet (verbatim), else fall back to the intro heading alone.
    descriptor = ""
    for m in page_spec.get("markers", []) or []:
        ml = m.lower()
        if m != heading and any(k in ml for k in
                                ("portal", "intranet", "hub", "home of", "center")):
            descriptor = m.strip()
            break
    if heading and descriptor and descriptor.lower() not in heading.lower():
        title = "%s — %s" % (heading, descriptor)   # Company — Descriptor
    elif heading:
        title = heading
    # design-spec hero title is a fallback only if no source banner heading
    if not title and isinstance(design_spec, dict):
        for sec in design_spec.get("sections", []) or []:
            cols = sec.get("columns") or ([sec] if sec.get("webpart") else [])
            for c in cols:
                if (c.get("webpart") or "").lower() == "hero" and c.get("title"):
                    title = c["title"]
                    break
            if title:
                break
    title = title or page_spec.get("title") or page_name

    # --- hero background image (build-site URL) ---
    img_url = None
    if isinstance(design_spec, dict):
        for sec in design_spec.get("sections", []) or []:
            cols = sec.get("columns") or ([sec] if sec.get("webpart") else [])
            for c in cols:
                if (c.get("webpart") or "").lower() == "hero":
                    spec_img = c.get("image") or {}
                    img_url = spec_img.get("url") or image_map.get(spec_img.get("src"))
                    if img_url:
                        break
            if img_url:
                break
    if not img_url and intro:
        for im in intro.get("images", []) or []:
            src = im.get("src")
            url = image_map.get(src)
            if not url:
                continue
            w = (_IMG_DIMS.get(src) or {}).get("w") or 0
            if w and w < _FEATURE_MIN_W:
                continue  # too small to be a header background — leave it inline
            img_url = url
            break
    return title, img_url


def set_title_area_hero(sp, sid, page_id, api, title, image_url, publish=True):
    """Make the page's NATIVE title header (titleArea) BE the hero: company-led
    title + the brand/hero image as the full-background (layout=imageAndTitle).
    PATCHes the sitePage's titleArea via Graph (beta — v1.0 ignores titleArea image)
    and republishes. Verified empirically (2026-06-12): setting BOTH imageWebUrl and
    serverProcessedContent.imageSources[].value persists the background image across
    publish on a #microsoft.graph.sitePage; layout 'imageAndTitle' renders it behind
    the title. Returns the read-back titleArea dict (or {} on failure)."""
    cast = "microsoft.graph.sitePage"
    ta = {
        "layout": "imageAndTitle" if image_url else "colorBlock",
        "title": title or "",
        "textAlignment": "left",
        "showPublishedDate": False,
        "enableGradientEffect": True,
    }
    if image_url:
        ta["imageWebUrl"] = image_url
        ta["serverProcessedContent"] = {
            "imageSources": [{"key": "imageSource", "value": image_url}]
        }
    body = {"@odata.type": "#microsoft.graph.sitePage", "title": title or "",
            "titleArea": ta}
    # titleArea image only honoured on beta; try beta first, fall back to v1.0.
    for a in ("beta", api, "v1.0"):
        r = requests.patch(
            "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s"
            % (a, sid, page_id, cast), headers=sp.HJ, json=body)
        if r.status_code < 300:
            if publish:
                requests.post(
                    "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s/publish"
                    % (a, sid, page_id, cast), headers=sp.H)
            rb = requests.get(
                "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s?$select=title,titleArea"
                % (a, sid, page_id, cast), headers=sp.H)
            return rb.json().get("titleArea") or {} if rb.status_code < 300 else {}
    return {}


def _canvas_uses_beta_webparts(canvas):
    """True if the canvas contains a web part Graph only accepts on the beta
    pages endpoint (Hero / Quick Links / Embed)."""
    for s in canvas.get("horizontalSections", []) or []:
        for c in s.get("columns", []) or []:
            for wp in c.get("webparts", []) or []:
                if wp.get("webPartType") in BETA_ONLY_WEBPARTS:
                    return True
    return False


def _backup_page(sp, sid, page_id, api, name, backup_dir):
    """Snapshot an existing built page's canvasLayout BEFORE overwrite, so it can
    be deterministically restored (this SharePoint has no version history).
    Best-effort: on any failure the page's recycle-bin copy is the fallback."""
    from datetime import datetime, timezone
    try:
        r = requests.get(
            "https://graph.microsoft.com/%s/sites/%s/pages/%s/microsoft.graph.sitePage?$expand=canvasLayout"
            % (api, sid, page_id), headers=sp.H)
        if r.status_code >= 300:
            print("backup: GET %s failed %d — relying on recycle bin" % (name, r.status_code))
            return None
        pg = r.json()
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(backup_dir, "%s.%s.json" % (name, ts))
        json.dump({"name": name, "title": pg.get("title"), "api": api, "sid": sid,
                   "savedAt": ts, "sourcePageId": page_id,
                   "canvasLayout": pg.get("canvasLayout")},
                  open(path, "w"), indent=1)
        print("backup: %s -> %s" % (name, path))
        return path
    except Exception as e:
        print("backup: %s failed (%s) — relying on recycle bin" % (name, str(e)[:120]))
        return None


def apply_page(sp, sid, name, title, canvas, publish=True, replace=True,
               hero_title=None, hero_image=None, _attempt=0):
    """Create or replace the page with the composed canvas, then publish.
    Replacing = delete existing + recreate (Graph PATCH of canvasLayout on an
    existing sitePage is unreliable; recreate is the robust path).
    Prefers the BETA endpoint when the canvas uses Hero/Quick Links/Embed
    (those return 'not supported in current version of API' on v1.0).

    The HERO is the NATIVE page-title header: after the page is created the
    titleArea is PATCHed (set_title_area_hero) with the company-led hero_title +
    hero_image as the header background. The page `title` is set to hero_title so
    the header band reads the brand banner (NOT 'Home') everywhere SP shows it.

    PHANTOM / SOFT-LOCK HANDLING (_attempt):
    A failed POST soft-locks the page name: Graph lists it via find_page but
    PATCH/GET return 404 (phantom). Re-POSTing the same name returns 409. On
    detection, apply_page recurses with _attempt+1, using _fresh_name() to
    compute a deterministic alternative name (e.g. Home-r2.aspx, Home-r3.aspx).
    The 423-Locked welcome-page (Home.aspx) PATCH-in-place path is preserved.
    """
    if _attempt > 5:
        raise RuntimeError("apply_page %s: exceeded max retry attempts (phantom loop?)" % name)
    work_name = _fresh_name(name, _attempt)
    if _attempt:
        print("apply_page: retry attempt %d — using fresh name %r (original %r)"
              % (_attempt, work_name, name))
    existing_id, api = find_page(sp, sid, work_name)
    page_title = hero_title or title
    if existing_id and replace and os.environ.get("CC_SP_BACKUP_DIR"):
        _backup_page(sp, sid, existing_id, api, work_name, os.environ["CC_SP_BACKUP_DIR"])
    deleted = False
    if existing_id and replace:
        dr = requests.delete("https://graph.microsoft.com/%s/sites/%s/pages/%s"
                             % (api, sid, existing_id), headers=sp.H)
        deleted = dr.status_code in (200, 202, 204)
        if not deleted:
            # Welcome/home page (Home.aspx) can't be deleted via Graph → PATCH in place.
            print("apply_page: delete %s failed (%s) — PATCHing existing page in place"
                  % (work_name, dr.status_code))
            return _patch_existing_page(sp, sid, existing_id, api, work_name, page_title,
                                        canvas, hero_image, publish)
        # Verify the deleted page is truly gone: if find_page still sees it and
        # PATCH returns 404 that's a phantom — treat as create-fresh.
        phantom_id, _ = find_page(sp, sid, work_name)
        if phantom_id:
            pr = requests.patch(
                "https://graph.microsoft.com/%s/sites/%s/pages/%s/microsoft.graph.sitePage"
                % (api, sid, phantom_id), headers=sp.HJ,
                json={"@odata.type": "#microsoft.graph.sitePage", "title": page_title})
            if pr.status_code == 404:
                print("apply_page: phantom detected for %r (find_page visible, PATCH 404)"
                      " — retrying with fresh name" % work_name)
                return apply_page(sp, sid, name, title, canvas, publish=publish,
                                  replace=replace, hero_title=hero_title,
                                  hero_image=hero_image, _attempt=_attempt + 1)
    page = {"@odata.type": "#microsoft.graph.sitePage", "name": work_name,
            "title": page_title, "pageLayout": "article", "canvasLayout": canvas}
    last = None
    order = ("beta", "v1.0") if _canvas_uses_beta_webparts(canvas) else ("v1.0", "beta")
    for a in order:
        r = requests.post("https://graph.microsoft.com/%s/sites/%s/pages" % (a, sid),
                          headers=sp.HJ, json=page)
        last = r
        if r.status_code in (200, 201):
            created = r.json()
            # HERO = native title header: set titleArea (company-led title + bg img)
            ta = set_title_area_hero(sp, sid, created["id"], a, page_title,
                                     hero_image, publish=publish)
            if ta:
                print("TITLE-AREA HERO: layout=%s title=%r imageWebUrl=%s"
                      % (ta.get("layout"), ta.get("title"),
                         "set" if ta.get("imageWebUrl") else "NONE"))
            if publish:
                requests.post(
                    "https://graph.microsoft.com/%s/sites/%s/pages/%s/microsoft.graph.sitePage/publish"
                    % (a, sid, created["id"]), headers=sp.H)
            return created, a
        # 409 nameAlreadyExists: two sub-cases —
        #   (a) existing_id known: this is a welcome-page soft-delete race → PATCH.
        #   (b) no existing_id: this name was never cleanly deleted (phantom) → fresh name.
        if r.status_code == 409:
            if existing_id:
                print("apply_page: POST %s 409 nameAlreadyExists — PATCHing existing page"
                      % work_name)
                return _patch_existing_page(sp, sid, existing_id, api, work_name,
                                            page_title, canvas, hero_image, publish)
            else:
                print("apply_page: POST %s 409 nameAlreadyExists (phantom, no known id)"
                      " — retrying with fresh name" % work_name)
                return apply_page(sp, sid, name, title, canvas, publish=publish,
                                  replace=replace, hero_title=hero_title,
                                  hero_image=hero_image, _attempt=_attempt + 1)
    raise RuntimeError("apply_page %s failed %s: %s"
                       % (work_name, last.status_code, last.text[:400]))


def _patch_existing_page(sp, sid, page_id, api, name, page_title, canvas,
                         hero_image, publish):
    """Replace an existing page's content by PATCHing canvasLayout in place — the
    only path for the site welcome page (Home.aspx), which Graph won't delete.
    Tries beta first when the canvas needs beta-only web parts."""
    cast = "microsoft.graph.sitePage"
    body = {"@odata.type": "#microsoft.graph.sitePage", "title": page_title,
            "canvasLayout": canvas}
    order = ("beta", api, "v1.0") if _canvas_uses_beta_webparts(canvas) else (api, "beta", "v1.0")
    last = None
    seen = set()
    for a in order:
        if a in seen:
            continue
        seen.add(a)
        r = requests.patch(
            "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s"
            % (a, sid, page_id, cast), headers=sp.HJ, json=body)
        last = r
        if r.status_code < 300:
            ta = set_title_area_hero(sp, sid, page_id, a, page_title, hero_image,
                                     publish=publish)
            if ta:
                print("TITLE-AREA HERO: layout=%s title=%r imageWebUrl=%s"
                      % (ta.get("layout"), ta.get("title"),
                         "set" if ta.get("imageWebUrl") else "NONE"))
            if publish:
                requests.post(
                    "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s/publish"
                    % (a, sid, page_id, cast), headers=sp.H)
            r2 = requests.get(
                "https://graph.microsoft.com/%s/sites/%s/pages/%s/%s?$select=id,name,title,webUrl"
                % (a, sid, page_id, cast), headers=sp.H)
            return (r2.json() if r2.status_code < 300 else {"id": page_id}), a
    raise RuntimeError("apply_page PATCH %s failed %s: %s"
                       % (name, last.status_code, last.text[:400]))


def verify_structure(sp, sid, page_id, api, page_spec, image_map):
    """Read the page back and assert: >=2 sections, >=1 multi-col (width<12),
    images referenced, all markers present, published. Returns a report dict."""
    cast = "microsoft.graph.sitePage"
    r = requests.get("https://graph.microsoft.com/%s/sites/%s/pages/%s/%s?$expand=canvasLayout,webparts&$select=id,title,titleArea,canvasLayout"
                     % (api, sid, page_id, cast), headers=sp.H)
    j = r.json()
    layout = j.get("canvasLayout") or {}
    secs = layout.get("horizontalSections", []) or []
    widths = []
    blob = []
    img_count = 0
    for s in secs:
        for c in s.get("columns", []) or []:
            widths.append(c.get("width"))
            for wp in c.get("webparts", []) or []:
                t = wp.get("@odata.type", "")
                if "standardWebPart" in t and wp.get("webPartType") == IMAGE_WEBPART_GUID:
                    img_count += 1
                blob.append(wp.get("innerHtml") or json.dumps(wp))
    # The HERO is the native title header (titleArea): fold its title + background
    # image URL into the blob so banner markers/the hero image count toward the
    # checks (the header sits OUTSIDE canvasLayout but IS part of the page).
    ta = j.get("titleArea") or {}
    title_area = (j.get("title") or "") + " " + (ta.get("title") or "")
    ta_img = ta.get("imageWebUrl") or ""
    blob.append(title_area)
    blob.append(ta_img)
    all_html = "\n".join(blob)
    want_urls = [image_map.get(im.get("src")) for im in page_spec.get("images", [])]
    want_urls = [u for u in want_urls if u]
    imgs_referenced = sum(1 for u in want_urls if u in all_html)
    markers = page_spec.get("markers", [])
    missing = [m for m in markers
               if m.lower() not in all_html.lower() and m.strip().lower() != "home"]
    multicol = [w for w in widths if w and 0 < w < 12]

    # COPY FIDELITY: how much of the source's verbatim copy appears on the build
    cov, cov_missing, cov_total = copy_coverage(
        page_spec.get("sourceText") or
        " ".join(b.get("text", "") for b in page_spec.get("content", [])),
        all_html)

    # published?
    state = ""
    pr = requests.get("https://graph.microsoft.com/%s/sites/%s/pages/%s/%s?$select=publishingState,webUrl"
                      % (api, sid, page_id, cast), headers=sp.H)
    if pr.status_code < 300:
        state = ((pr.json().get("publishingState") or {}).get("level") or "")

    return {
        "sections": len(secs),
        "column_widths": widths,
        "multi_column_widths": multicol,
        "has_multi_column": bool(multicol),
        "image_webparts": img_count,
        "images_referenced": imgs_referenced,
        "images_expected": len(want_urls),
        "markers_total": len(markers),
        "markers_missing": missing,
        "all_markers_present": not missing,
        "copy_coverage": round(cov, 4),
        "copy_tokens_total": cov_total,
        "copy_tokens_missing": cov_missing[:40],
        "published_state": state,
        "web_url": pr.json().get("webUrl") if pr.status_code < 300 else None,
    }


def _append_canvas_batches(sp, sid, page_id, api, batches, page_title, hero_image,
                            publish):
    """PATCH-append remainder canvas batches (batch 2..N) onto an already-created
    page.  Reuses _patch_existing_page with the ACCUMULATED canvas (all previously
    appended sections + the new batch) so each PATCH replaces the full canvasLayout
    with everything placed so far.  Logs each append."""
    accumulated = []
    # batch[0] already on the page — start from batch[1]
    for i, batch in enumerate(batches[1:], start=2):
        accumulated.extend(batch.get("horizontalSections", []))
        n_heavy = sum(
            1 for s in accumulated
            for c in s.get("columns", []) or []
            for wp in c.get("webparts", []) or []
            if wp.get("webPartType") in _HEAVY_WP_TYPES
        )
        print("[BATCH] appending %d section(s) (batch %d/%d, %d heavy total so far)"
              % (len(batch.get("horizontalSections", [])), i, len(batches), n_heavy))
        # Build the full canvas up to this point (first batch + all accumulated)
        full_sections = (batches[0].get("horizontalSections", [])
                         + accumulated)
        full_canvas = {"horizontalSections": full_sections}
        _patch_existing_page(sp, sid, page_id, api, page_title, page_title,
                             full_canvas, hero_image, publish)


def _norm_source_src(src):
    """Normalize a live-captured image URL to the server-relative source path
    used in sp-expect/image-map (strip scheme+host+query, unwrap afdcache)."""
    s = (src or "").split("?")[0]
    if "://" in s:
        rest = s.split("://", 1)[1]
        slash = rest.find("/")
        s = rest[slash:] if slash >= 0 else "/"
    marker = "/_vti_bin/afdcache.ashx/authitem"
    if marker in s:
        s = s.split(marker, 1)[1]
    return s


def _merge_manifest_images(expect, proj):
    """SINGLE SOURCE-OF-TRUTH: merge each page's CONTENT images from the
    live-capture manifest (proj/manifests/<stem>.json — the SAME manifest the
    completeness gate diffs against) into page['images'], so the build's image
    set matches the gate's by construction. sp-audit under-captures (it missed
    jes_red.jpg on an article); the live manifest is authoritative. Chrome
    images (zone 'lnkLogo' or 's4-*') are excluded, mirroring the gate."""
    if not proj:
        return
    mdir = os.path.join(proj, "manifests")
    if not os.path.isdir(mdir):
        return
    for pg in expect.get("pages", []):
        name = pg.get("name", "")
        stem = name[:-5] if name.lower().endswith(".aspx") else name
        mpath = os.path.join(mdir, stem + ".json")
        if not os.path.exists(mpath):
            continue
        try:
            man = json.load(open(mpath))
        except Exception:
            continue
        have = {_norm_source_src(im.get("src")) for im in pg.get("images", [])}
        added = []
        for im in man.get("images", []):
            zone = (im.get("zone") or "").strip()
            if zone == "lnkLogo" or zone.startswith("s4-"):
                continue  # chrome — out of scope (mirror the gate)
            norm = _norm_source_src(im.get("src"))
            if not norm or norm in have:
                continue
            have.add(norm)
            # filename convention (matches sp-audit): basename with '%' -> '-'.
            # REQUIRED — image_migrate.migrate() skips any image lacking a filename.
            fname = norm.rsplit("/", 1)[-1].replace("%", "-")
            pg.setdefault("images", []).append(
                {"src": norm, "filename": fname, "alt": im.get("alt", "")})
            added.append(norm)
        if added:
            print("[MANIFEST-IMG] %s: +%d content image(s) from live-capture "
                  "manifest (single source-of-truth): %s"
                  % (name, len(added), ", ".join(added)))


def _merge_manifest_text(expect, proj):
    """TEXT analog of _merge_manifest_images: merge each page's CONTENT text blocks
    from the live-capture manifest that are NOT already in the build's content[]
    (e.g. a signature/byline the audit under-captured), so the full source text
    survives. Only adds genuinely-missing copy (most manifest text already matches a
    content block and is skipped); the content safety net then renders the additions."""
    if not proj:
        return
    mdir = os.path.join(proj, "manifests")
    if not os.path.isdir(mdir):
        return
    norm = lambda s: re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    for pg in expect.get("pages", []):
        name = pg.get("name", "")
        stem = name[:-5] if name.lower().endswith(".aspx") else name
        mpath = os.path.join(mdir, stem + ".json")
        if not os.path.exists(mpath):
            continue
        try:
            man = json.load(open(mpath))
        except Exception:
            continue
        # include heading (headings render via _block_html as <h2>) so they aren't
        # re-merged as duplicate blocks — only genuinely-missing copy (the signature).
        have = norm(" ".join((b.get("text") or "") + " " + (b.get("html") or "")
                             + " " + (b.get("heading") or "")
                             for b in pg.get("content", [])))
        added = []
        for t in man.get("text", []):
            tn = (t or "").strip()
            if len(tn) < 8:
                continue
            words = norm(tn).split()
            key = " ".join(words[:6])              # first-6-word signature of the block
            if not key or key in have:
                continue                           # already in the build's content
            pg.setdefault("content", []).append(
                {"kind": "section", "text": tn, "html": "<p>%s</p>" % esc(tn)})
            have += " " + " ".join(words)
            added.append(tn.replace("\n", " ")[:48])
        if added:
            print("[MANIFEST-TXT] %s: +%d text block(s) from manifest "
                  "(under-captured copy): %s" % (name, len(added), " | ".join(added)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--expect")
    ap.add_argument("--imagemap")
    ap.add_argument("--site-path")
    ap.add_argument("--site-id")
    ap.add_argument("--page", default="Home.aspx")
    ap.add_argument("--pages", help="comma-separated list of page filenames to compose")
    ap.add_argument("--build-cap", type=int, default=None,
                    help="process at most N pages (applied to --pages list order)")
    ap.add_argument("--heavy-cap", type=int, default=None,
                    help="override MAX_HEAVY_WEBPARTS_PER_PAGE for this run")
    ap.add_argument("--spec", help="design-spec.json (default: <proj>/design-spec.json)")
    ap.add_argument("--no-spec", action="store_true",
                    help="ignore design-spec.json and use the heuristic fallback")
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # --heavy-cap: override the module-level constant before any batching.
    if a.heavy_cap is not None:
        global MAX_HEAVY_WEBPARTS_PER_PAGE
        MAX_HEAVY_WEBPARTS_PER_PAGE = a.heavy_cap

    # Build the list of pages to process.
    # --pages (csv) takes priority; fall back to legacy --page (single).
    if a.pages:
        pages_list = [p.strip() for p in a.pages.split(",") if p.strip()]
    else:
        pages_list = [a.page]
    if a.build_cap is not None:
        pages_list = pages_list[:a.build_cap]

    proj = "/srv/projects/%s" % a.job if a.job else None
    expect_path = a.expect or (proj + "/sp-expect.json")
    imagemap_path = a.imagemap or (proj + "/image-map.json")
    expect = json.load(open(expect_path))
    image_map = json.load(open(imagemap_path)).get("_map", {})

    # Reconcile the build's image set to the gate's source-of-truth (the live-capture
    # manifest) BEFORE migration/compose, so build and gate agree by construction.
    _merge_manifest_images(expect, proj)
    _merge_manifest_text(expect, proj)

    # image natural dims (enrich.json) → skip featuring tiny images (e.g. signatures) as heroes
    try:
        enrich_path = (proj or os.path.dirname(expect_path) or ".") + "/enrich.json"
        if os.path.exists(enrich_path):
            _IMG_DIMS.update(json.load(open(enrich_path)).get("imageDims", {}) or {})
    except Exception:
        pass

    # Resolve the build site + init the SP client BEFORE migration — migration uploads
    # images via `sp`, so it must exist first (else NameError -> migration silently skipped
    # -> images never uploaded). This block was previously AFTER migration (the bug).
    site_path = a.site_path
    site_id = a.site_id or expect.get("siteId")
    if proj and os.path.exists(proj + "/site.json"):
        sj = json.load(open(proj + "/site.json"))
        site_id = site_id or sj.get("siteId")
        if not site_path:
            url = sj.get("siteUrl", "")
            site_path = "/sites/" + url.rstrip("/").split("/sites/")[-1] if "/sites/" in url else None
    if not site_path:
        raise SystemExit("need --site-path or a resolvable site.json")
    if not a.dry_run:
        sp = SP(site_host=SITE_HOST, site_path=site_path)
        sid = site_id or sp.site_id()
    else:
        sp = None
        sid = site_id or "dry-run-sid"

    # IMAGE MIGRATION — ensure every page's source images are on the build site.
    # For each pages[].images[] entry not yet in image_map, upload via image_migrate
    # and write the new entries back to image-map.json.  Idempotent: already-uploaded
    # images are reused (image_migrate._exists_on_build short-circuits).
    # In --dry-run mode this step is SKIPPED (no SP client); map additions are logged.
    _imagemap_data = json.load(open(imagemap_path)) if os.path.exists(imagemap_path) else {}
    _new_map_entries = {}  # src -> built_url for entries added this run (for dry-run report)

    if not a.dry_run:
        try:
            import image_migrate as _imig
            _src_host = (_imagemap_data.get("sourceUrl") or "").replace("https://", "").split("/")[0]
            _src_web = _imagemap_data.get("sourceUrl") or ""
            _cap_imgs_json = (os.path.join(proj, "capture", "images-map.json")
                              if proj else None)
            _cap_imgs = (json.load(open(_cap_imgs_json))
                         if (_cap_imgs_json and os.path.exists(_cap_imgs_json)) else None)
            # image_migrate opens these values directly, but the map stores them CWD-relative
            # ("images/<file>"). The driver runs compose from the home dir, NOT the capture dir,
            # so resolve to ABSOLUTE under <proj>/capture or the byte silently won't be found
            # (-> capture-missing -> text-only article, the exact bug that dropped article images).
            if _cap_imgs:
                _cap_dir = os.path.join(proj, "capture")
                _cap_imgs = {k: (v if os.path.isabs(v) else os.path.join(_cap_dir, v))
                             for k, v in _cap_imgs.items()}
            # Build a minimal expect with only unmapped images so migrate() is idempotent.
            _unmapped_pages = []
            for _pg in expect.get("pages", []):
                _unmapped = [im for im in _pg.get("images", [])
                             if im.get("src") not in image_map]
                if _unmapped:
                    _unmapped_pages.append({"name": _pg.get("name"),
                                            "images": _unmapped})
            if _unmapped_pages:
                print("[IMG-MIGRATE] uploading %d unmapped image(s) across %d page(s)"
                      % (sum(len(p["images"]) for p in _unmapped_pages),
                         len(_unmapped_pages)))
                _mig_expect = {"pages": _unmapped_pages}
                _new_urls, _new_details = _imig.migrate(
                    _mig_expect, sp, a.job or "JOB", _src_host, _src_web,
                    capture_imgs=_cap_imgs)
                image_map.update(_new_urls)
                _new_map_entries.update(_new_urls)
                # Write back image-map.json with new entries.
                _imagemap_data["_map"] = image_map
                _imagemap_data["_details"] = (
                    _imagemap_data.get("_details", []) + _new_details)
                with open(imagemap_path, "w") as _f:
                    json.dump(_imagemap_data, _f, indent=2)
                print("[IMG-MIGRATE] image-map.json updated (%d new entries)"
                      % len(_new_urls))
            else:
                print("[IMG-MIGRATE] all images already in map — skip upload")
        except Exception as _e:
            print("[IMG-MIGRATE] WARN: migration step failed: %s" % str(_e)[:200])
    else:
        # Dry-run: report which images WOULD be added to image-map.json.
        _would_add = []
        for _pg in expect.get("pages", []):
            for _im in _pg.get("images", []):
                _src = _im.get("src")
                if _src and _src not in image_map:
                    _fname = _im.get("filename", os.path.basename(_src))
                    _target = "%s/%s/%s" % ("Migrated", a.job or "JOB", _fname)
                    _would_add.append({"page": _pg.get("name"),
                                       "src": _src, "target": _target})
        if _would_add:
            print("[IMG-MIGRATE DRY-RUN] would upload %d image(s):" % len(_would_add))
            for _w in _would_add:
                print("  %s -> %s" % (_w["src"][:60], _w["target"]))
        else:
            print("[IMG-MIGRATE DRY-RUN] all images already in map — no uploads needed")

    # design-spec.json (ux-designer output). If present -> build EXACTLY that;
    # absent (or --no-spec) -> heuristic auto-layout fallback.
    design_spec = None
    spec_path = a.spec or (proj + "/design-spec.json" if proj else None)
    if not a.no_spec and spec_path and os.path.exists(spec_path):
        design_spec = json.load(open(spec_path))
        print("USING design-spec: %s" % spec_path)

    # (build site resolved + SP client initialized above, before migration)
    overall_ok = True
    for page_name in pages_list:
        print("=== COMPOSE page=%s ===" % page_name)
        page_spec = next((p for p in expect.get("pages", [])
                          if (p.get("name") or "").lower() == page_name.lower()), None)
        if not page_spec:
            print("SKIP: page %s not in sp-expect.json" % page_name)
            overall_ok = False
            continue

        # HERO = native page-title header: company-led title + brand image background.
        hero_title, hero_image = derive_title_hero(page_spec, design_spec, image_map,
                                                   page_name)

        canvas = build_canvas(page_spec, image_map, sid, design_spec=design_spec,
                              page_name=page_name, sp=sp, job=a.job,
                              hero_title=hero_title, hero_image=hero_image)

        # Split into ≤MAX_HEAVY_WEBPARTS_PER_PAGE-heavy batches.  Nothing is dropped.
        batches = plan_heavy_webpart_batches(canvas, page_title=page_name)

        if a.dry_run:
            total_heavy = sum(
                1 for b in batches
                for s in b.get("horizontalSections", [])
                for c in s.get("columns", []) or []
                for wp in c.get("webparts", []) or []
                if wp.get("webPartType") in _HEAVY_WP_TYPES
            )
            # Collect image web-part refs for the dry-run canvas summary.
            _img_refs = []
            for _s in canvas.get("horizontalSections", []):
                for _c in _s.get("columns", []) or []:
                    for _wp in _c.get("webparts", []) or []:
                        if _wp.get("webPartType") == IMAGE_WEBPART_GUID:
                            _isrc = ((_wp.get("data") or {})
                                     .get("serverProcessedContent") or {})
                            _isrc = _isrc.get("imageSources", [])
                            _val = _isrc[0].get("value", "") if _isrc else ""
                            _img_refs.append(_val)
            # Planned image-map entries (already in map or would be added by migration).
            _page_map_adds = {
                _src: image_map.get(_src)
                for _im in page_spec.get("images", [])
                for _src in [_im.get("src")]
                if _src and image_map.get(_src)
            }
            print(json.dumps({"page": page_name,
                              "sections": len(canvas["horizontalSections"]),
                              "batches": len(batches),
                              "total_heavy_webparts": total_heavy,
                              "heavy_cap": MAX_HEAVY_WEBPARTS_PER_PAGE,
                              "layouts": [s["layout"] for s in canvas["horizontalSections"]],
                              "hero_title": hero_title, "hero_image": hero_image,
                              "image_webparts_in_canvas": len(_img_refs),
                              "image_webpart_refs": _img_refs,
                              "source_images_count": len(page_spec.get("images", [])),
                              "image_map_entries_for_page": _page_map_adds}, indent=1))
            continue

        # Apply the first batch (creates or PATCHes the page).
        created, api = apply_page(sp, sid, page_name, page_spec.get("title") or page_name,
                                  batches[0], publish=not a.no_publish,
                                  hero_title=hero_title, hero_image=hero_image)

        # PATCH-append any remaining batches (preserves ALL heavy web parts).
        if len(batches) > 1:
            _append_canvas_batches(sp, sid, created["id"], api, batches,
                                   page_spec.get("title") or page_name, hero_image,
                                   publish=not a.no_publish)

        rep = verify_structure(sp, sid, created["id"], api, page_spec, image_map)
        print("APPLIED page=%s id=%s" % (page_name, created["id"]))
        print(json.dumps(rep, indent=1))
        ok = (rep["sections"] >= 2 and rep["has_multi_column"]
              and rep["all_markers_present"]
              and rep["images_referenced"] == rep["images_expected"]
              and (rep["copy_tokens_total"] == 0 or rep["copy_coverage"] >= 0.9))
        print("COPY_COVERAGE: %.3f (%d source tokens)"
              % (rep["copy_coverage"], rep["copy_tokens_total"]))
        print("STRUCTURE_OK:", ok)
        if not ok:
            overall_ok = False

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
