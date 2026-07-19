// cc-completeness-gate: DETERMINISTIC completeness/verify gate for the SP classic->modern pipeline.
// Given a SOURCE manifest (produced by cc-sp-manifest.mjs on the classic source page) and a BUILT
// page URL, it captures the BUILT page's rendered manifest by REUSING cc-sp-manifest.mjs (shelled,
// not reimplemented), then diffs built vs source: every source image / link / text-block must be
// present in the built page. It also asserts the page is PUBLISHED and has >= minSections sections.
//
// This is the gate signal. An O/C agent CANNOT pass it by self-report: pass requires the rendered
// built page to actually contain the source's elements. A capture error FAILS (never silent pass).
//
// Usage:
//   node cc-completeness-gate.mjs --source <sourceManifest.json> --built-url <url> [opts]
//   node cc-completeness-gate.mjs --source <src.json> --built-manifest <built.json> [opts]   (offline diff)
// Options:
//   --min-sections <N>   minimum content sections required (default 2)
//   --out <verdict.json> write structured JSON verdict (default: stdout only)
//   --state <path>       auth storageState path forwarded to cc-sp-manifest.mjs
//   --no-auth            capture without auth (default: auth on)
//   --area <a,b>         source areas to enforce (default: content). e.g. content,nav,footer
//   --image-map <path>   migration map (old src -> new build URL). The pipeline renames+resizes
//                        migrated images, so matching by SOURCE basename is wrong. With the map we
//                        match the BUILT basename of each source image. If omitted, falls back to
//                        source-basename matching with a warning. Unmapped in-scope images are
//                        FLAGGED (not silently passed).
//
// SCOPE = CONTENT-ONLY. Tenant chrome and global nav are OUT of scope (non-portable, handed to
// human devs). The gate must NOT count them as missing:
//   - Source IMAGES with zone === "lnkLogo" or zone starting "s4-" (master-page logo, bg/header
//     tiles, footer logo, wallpaper) are EXCLUDED. Content images (zone "" or starting "carousel")
//     are KEPT.
//   - Source LINKS with zone === "topNav-mobile" (global nav) are EXCLUDED. Content links
//     (zone "contentRow", "pageTitle", or anything not a known nav zone) are KEPT.
//
// Exit 0 = PASS (complete). Non-zero = FAIL (incomplete / capture error / not published).

import { existsSync, readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const MANIFEST_TOOL = join(HERE, "cc-sp-manifest.mjs"); // DOM capture tool (fallback mode)
const CANVAS_TOOL   = join(HERE, "cc-sp-canvas.mjs");   // web-part-JSON capture (T3b, primary)

// ---- arg parsing -----------------------------------------------------------
const argv = process.argv.slice(2);
const flag = n => argv.includes(n);
const val  = (n, d=null) => { const i = argv.indexOf(n); return i >= 0 ? argv[i+1] : d; };

const sourcePath   = val("--source");
const builtUrl     = val("--built-url");          // DOM-render capture (fallback; blob images)
const builtCanvas  = val("--built-canvas-url");   // T3b: read web-part JSON (CanvasContent1) — REAL image refs
const builtManPath = val("--built-manifest");
const minSections  = parseInt(val("--min-sections", "2"), 10);
const outPath      = val("--out");
const statePath    = val("--state");
const noAuth       = flag("--no-auth");
const areas        = (val("--area", "content")).split(",").map(s => s.trim()).filter(Boolean);
const imageMapPath = val("--image-map");

function die(msg) { console.error("ARG ERROR: " + msg); process.exit(2); }
if (!sourcePath) die("--source <manifest.json> is required");
if (!builtUrl && !builtCanvas && !builtManPath) die("one of --built-canvas-url (preferred), --built-url, or --built-manifest is required");
if (!existsSync(sourcePath)) die("source manifest not found: " + sourcePath);

// ---- normalization rules ---------------------------------------------------
// Images match by basename (CDN/host rewrites the path; the asset filename survives).
const imgKey = src => {
  if (!src) return "";
  try { src = decodeURIComponent(src); } catch {}
  let base = src.split(/[?#]/)[0].split("/").pop() || src;
  return base.toLowerCase().trim();
};
// Links match by normalized target: drop protocol, trailing slash, query/hash, lowercase host+path.
const linkKey = href => {
  if (!href) return "";
  try {
    const u = new URL(href);
    let p = (u.host + u.pathname).toLowerCase();
    try { p = decodeURIComponent(p); } catch {}
    return p.replace(/\/+$/, "");
  } catch {
    return href.toLowerCase().split(/[?#]/)[0].replace(/\/+$/, "");
  }
};
// Text normalization (FIX 1): SOURCE manifests captured from classic SP frequently carry MOJIBAKE
// (Windows-1252 bytes mis-decoded as UTF-8) and U+FFFD replacement chars — e.g. "It's" -> "Itï¿½s",
// "we've" -> "weï¿½ve". The BUILT side carries clean curly punctuation. Both sides are mapped to a
// common ASCII form so a single corrupt byte can no longer fail a whole paragraph. We:
//   1. strip zero-width chars,
//   2. fold multi-byte mojibake sequences (â€™ â€œ â€ â€“ â€” â€¦ Ã©…) to ASCII,
//   3. fold the bare U+FFFD / "ï¿½" artifact to an apostrophe (its overwhelmingly common context
//      here is a contraction: It's / we've / can't / they'd),
//   4. fold curly quotes/apostrophes/dashes/ellipsis to ASCII,
//   5. collapse whitespace + lowercase + trim.
const MOJIBAKE = [
  ["â€™", "'"], ["â€˜", "'"], ["â€š", ","], ["â€›", "'"],
  ["â€œ", '"'], ["â€", '"'], ["â€", '"'],
  ["â€“", "-"], ["â€”", "-"], ["â€¦", "..."],
  ["Ã©", "e"], ["Ã¨", "e"], ["Ã ", "a"], ["Ã§", "c"],
  ["Ã¼", "u"], ["Ã¶", "o"], ["Ã¤", "a"], ["Ã±", "n"],
  ["ï¿½", "'"],
];
const normText = t => {
  let s = (t || "").replace(/[​‌‍﻿]/g, "");
  for (const [a, b] of MOJIBAKE) s = s.split(a).join(b);
  return s
    .replace(/�/g, "'")               // bare replacement char -> apostrophe (contraction context)
    .replace(/[‘’‚‛]/g, "'")
    .replace(/[“”„‟]/g, '"')
    .replace(/[–—―]/g, "-")
    .replace(/…/g, "...")
    .replace(/\s+/g, " ")
    .toLowerCase()
    .trim();
};
// For SHINGLE matching we further strip ALL punctuation to spaces. This removes punctuation-PLACEMENT
// artifacts between the two captures — e.g. source "clicking here.  Thank" vs built "clicking here .
// Thank" — which would otherwise break shingles straddling the punctuation. Identity of the WORDS is
// what we assert, not their exact punctuation glue.
const shingleTokens = norm => norm.replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
// Split a normalized+tokenized block into overlapping K-word shingles. Blocks shorter than K words
// degrade to a single whole-string shingle (strict — stays fail-closed for tiny blocks).
const SHINGLE_K = 6;
const SHINGLE_THRESHOLD = 0.8; // a source block PASSES iff >= this fraction of its shingles are found
const shinglesOf = norm => {
  const w = shingleTokens(norm).split(" ").filter(Boolean);
  if (w.length <= SHINGLE_K) return w.length ? [w.join(" ")] : [];
  const out = [];
  for (let i = 0; i + SHINGLE_K <= w.length; i++) out.push(w.slice(i, i + SHINGLE_K).join(" "));
  return out;
};

// ---- CONTENT-ONLY scoping (tenant chrome + global nav are OUT of scope) ----
// Source IMAGE in scope iff its zone is NOT chrome. Chrome = master-page logo (lnkLogo) or any
// SharePoint classic structural zone (s4-titlerow, s4-bodyContainer, s4-workspace, ...). Content
// images carry zone "" or a "carousel*" zone.
const isChromeImageZone = z => {
  const zone = (z || "").trim();
  return zone === "lnkLogo" || zone.startsWith("s4-");
};
const imageInScope = im => inAreas(im) && !isChromeImageZone(im.zone);

// Source LINK in scope iff its zone is NOT global navigation AND not capture noise.
// Global nav = "topNav-mobile". CAPTURE NOISE (T3b residual #1): zone "pageTitle" is the SP classic
// breadcrumb link back to the site home (a chrome breadcrumb, NOT authored page content) — it must
// not be in the required-set. Authored content links carry zone "contentRow" (Quick Links rail) etc.
const isNavLinkZone   = z => (z || "").trim() === "topNav-mobile";
const isBreadcrumbZone = z => (z || "").trim() === "pageTitle";
const linkInScope = ln => inAreas(ln) && !isNavLinkZone(ln.zone) && !isBreadcrumbZone(ln.zone);

// CAPTURE NOISE (T3b residual #2): a modern web part's ARIA label (e.g. "Full Width Image Carousel
// WebPart") is an accessibility label the renderer injects — NOT authored content. Drop such text
// blocks from the source required-set. (These never appear when the BUILT side is read from
// CanvasContent1, which carries only authored web-part text; we also filter the SOURCE side here.)
const TEXT_NOISE = [/\bweb\s*part\b/i, /\bwebpart\b/i, /image carousel/i];
const isNoiseText = t => TEXT_NOISE.some(re => re.test(t || ""));

// ---- load source -----------------------------------------------------------
let source;
try { source = JSON.parse(readFileSync(sourcePath, "utf8")); }
catch (e) { console.error("FAIL: cannot parse source manifest: " + e.message); process.exit(3); }

const inAreas = el => areas.includes(el.area || "content");
const srcImages = (source.images || []).filter(imageInScope);
const srcLinks  = (source.links  || []).filter(linkInScope);
const srcText   = (source.text   || []).filter(t => !isNoiseText(t)); // drop web-part ARIA labels (T3b residual #2)

// residual filtering counts (transparency in the verdict)
const excludedBreadcrumbLinks = (source.links || []).filter(ln => inAreas(ln) && isBreadcrumbZone(ln.zone)).length;
const excludedNoiseText       = (source.text  || []).filter(isNoiseText).length;

// counts of what scoping excluded (for the verdict — transparency, not silent dropping)
const excludedImages = (source.images || []).filter(im => inAreas(im) && isChromeImageZone(im.zone)).length;
const excludedLinks  = (source.links  || []).filter(ln => inAreas(ln) && isNavLinkZone(ln.zone)).length;

// ---- image-map (renamed/resized migrated images) --------------------------
// The pipeline renames+resizes migrated images, so a source image must be matched by the BUILT
// basename it was migrated to — NOT the source basename. The map file looks like:
//   { "_comment":..., "job":..., "sourceUrl":..., "buildSite":..., "_map": { "<old src>": "<new build url>" }, "_details":[...] }
// We index by the PATH of the old src (lowercased, decoded), because manifest srcs are full URLs
// (https://host/path...) while map keys are path-only (/sites/RDQ/...). afdcache-wrapped srcs embed
// the real publishing path after /afdcache.ashx/authitem — we index that too.
//
// Returns: { byPath: Map<normPath, builtBasename>, raw: <the _map dict>, loaded: bool }
function srcPathVariants(src) {
  // yields candidate normalized paths for a source URL or a map key
  const out = [];
  let s = src || "";
  try { s = decodeURIComponent(s); } catch {}
  let path = s;
  try { path = new URL(s).pathname; } catch { /* already a path */ }
  try { path = decodeURIComponent(path); } catch {}
  path = path.toLowerCase();
  out.push(path);
  // afdcache wrapper: /_vti_bin/afdcache.ashx/authitem/sites/rdq/publishingimages/foo.png
  const m = path.match(/\/afdcache\.ashx\/authitem(\/.*)$/);
  if (m) out.push(m[1]);
  return out;
}
let imageMap = { byPath: new Map(), loaded: false, entries: 0 };
const imageMapWarnings = [];
if (imageMapPath) {
  if (!existsSync(imageMapPath)) { console.error("FAIL: --image-map not found: " + imageMapPath); process.exit(3); }
  let mapDoc;
  try { mapDoc = JSON.parse(readFileSync(imageMapPath, "utf8")); }
  catch (e) { console.error("FAIL: cannot parse image-map: " + e.message); process.exit(3); }
  // The actual old->new dict lives under `_map`; tolerate a flat dict (entries that are url-strings)
  // for forward-compat. Ignore meta keys (_comment, job, sourceUrl, buildSite, _details, _map-meta).
  const META = new Set(["_comment", "job", "sourceurl", "buildsite", "_details", "_map"]);
  const rawMap = (mapDoc && typeof mapDoc._map === "object" && mapDoc._map) ? mapDoc._map
               : Object.fromEntries(Object.entries(mapDoc || {}).filter(
                   ([k, v]) => !META.has(k.toLowerCase()) && typeof v === "string"));
  let n = 0;
  for (const [oldSrc, newUrl] of Object.entries(rawMap)) {
    if (typeof newUrl !== "string") continue;
    const builtBase = imgKey(newUrl);
    if (!builtBase) continue;
    for (const p of srcPathVariants(oldSrc)) imageMap.byPath.set(p, builtBase);
    n++;
  }
  imageMap.loaded = true;
  imageMap.entries = n;
  if (n === 0) imageMapWarnings.push("image-map loaded but contained 0 usable old->new entries");
} else {
  imageMapWarnings.push("no --image-map supplied — matching migrated images by SOURCE basename (renamed/resized images may false-FAIL)");
}

// Resolve the BUILT basename to require for a source image.
//   -> { key, mapped:bool }   mapped=false means we fell back to source basename (and we FLAG it).
function builtKeyForSourceImage(src) {
  if (imageMap.loaded) {
    for (const p of srcPathVariants(src)) {
      const hit = imageMap.byPath.get(p);
      if (hit) return { key: hit, mapped: true };
    }
  }
  return { key: imgKey(src), mapped: false };
}

// ---- capture or load BUILT manifest ---------------------------------------
// builtMode: "canvas" = read web-part JSON (CanvasContent1) -> REAL image refs, element-level match.
//            "dom"    = legacy DOM render -> content images are opaque blob: URLs (count-parity).
let built, capturedTo = null, builtMode = builtCanvas ? "canvas" : "dom";
if (builtCanvas) {
  // T3b PRIMARY: capture the built page from its web-part JSON via SP REST (cc-sp-canvas.mjs).
  // CanvasContent1 carries the REAL migrated image references — not the DOM's opaque blob: URLs —
  // so a swapped/missing/duplicated image ref is now catchable at element level. Any capture
  // failure -> hard FAIL (fail-closed; never a silent pass).
  const tmp = mkdtempSync(join(tmpdir(), "ccgate-canvas-"));
  capturedTo = join(tmp, "built-canvas.json");
  const args = [CANVAS_TOOL, builtCanvas, capturedTo];
  if (statePath) args.push("--state", statePath);
  try {
    execFileSync("node", args, { stdio: ["ignore", "inherit", "inherit"], timeout: 120000 });
  } catch (e) {
    console.error("FAIL: canvas capture errored (cc-sp-canvas.mjs): " + e.message);
    console.error("  A capture/REST/auth error is treated as INCOMPLETE — the gate does NOT silently pass.");
    process.exit(4);
  }
  if (!existsSync(capturedTo)) { console.error("FAIL: canvas capture produced no manifest file"); process.exit(4); }
  try { built = JSON.parse(readFileSync(capturedTo, "utf8")); }
  catch (e) { console.error("FAIL: captured canvas manifest unparseable: " + e.message); process.exit(4); }
  if (/sign in to your account/i.test(built.title || "")) {
    console.error('FAIL: canvas page resolved to sign-in ("' + built.title + '") — not authenticated.');
    process.exit(4);
  }
} else if (builtManPath) {
  if (!existsSync(builtManPath)) { console.error("FAIL: --built-manifest not found: " + builtManPath); process.exit(3); }
  try { built = JSON.parse(readFileSync(builtManPath, "utf8")); }
  catch (e) { console.error("FAIL: cannot parse built manifest: " + e.message); process.exit(3); }
  // a built manifest with non-opaque named images is treated as canvas-grade for matching
  if ((built.images || []).some(i => /\/sites\/|\/sitepages\/|serverrelative/i.test((i.src||"").toLowerCase()) && !/^blob:|^data:/.test((i.src||"").toLowerCase()))) builtMode = "canvas";
} else {
  // REUSE cc-sp-manifest.mjs to capture the live built page. Any capture failure -> hard FAIL.
  const tmp = mkdtempSync(join(tmpdir(), "ccgate-"));
  capturedTo = join(tmp, "built-manifest.json");
  const args = [MANIFEST_TOOL, builtUrl, capturedTo];
  if (!noAuth) args.push("--auth");
  if (statePath) args.push("--state", statePath);
  try {
    execFileSync("node", args, { stdio: ["ignore", "inherit", "inherit"], timeout: 120000 });
  } catch (e) {
    console.error("FAIL: capture of built page errored (cc-sp-manifest.mjs): " + e.message);
    console.error("  A capture error is treated as INCOMPLETE — the gate does NOT silently pass.");
    process.exit(4);
  }
  if (!existsSync(capturedTo)) { console.error("FAIL: capture produced no manifest file"); process.exit(4); }
  try { built = JSON.parse(readFileSync(capturedTo, "utf8")); }
  catch (e) { console.error("FAIL: captured manifest unparseable: " + e.message); process.exit(4); }
  // Sign-in interception guard: a redirect to the login page is NOT a built page.
  if (/sign in to your account/i.test(built.title || "")) {
    console.error('FAIL: built URL redirected to sign-in ("' + built.title + '") — not authenticated for this tenant/site.');
    console.error("  Provide a valid storageState via --state or ~/.codecraft/verify-<host>.json. Gate does NOT pass.");
    process.exit(4);
  }
}

// ---- build lookup sets from BUILT -----------------------------------------
// MODERN SP REALITY: a modern canvas Image web part renders its image as a `blob:` URL (loaded
// client-side) — the migrated filename is NOT recoverable from the rendered <img src>. Other built
// images come from resource handlers (`_api/siteiconmanager/...`, `vpc_CanvasImg.<guid>`) that also
// carry no real filename. Such srcs are OPAQUE: filename matching is impossible, so the migrated
// basename (even with a perfect image-map) can never be found in the built DOM. We split built
// images into NAMED (real basename, matchable) and OPAQUE (blob/data/resource, countable but
// unnameable), and fall back to a COUNT/PARITY check for content images when the built side exposes
// no named images (a pure modern-canvas page).
// OPAQUE = blob/data (client-side canvas render) or a resource handler with no real filename.
const isOpaqueBuiltSrc = src => {
  const s = (src || "").toLowerCase();
  if (!s) return true;
  if (s.startsWith("blob:") || s.startsWith("data:")) return true;
  if (/\/_api\/|\/_vti_bin\/|getsitelogo|vpc_canvasimg|siteiconmanager/.test(s)) return true;
  return false;
};
// CHROME on the BUILT side = site logo / app-injected wallpaper. Background-New.jpg is the SPFx
// wallpaper (tenant chrome), not body content — exclude from the content-image count.
const isBuiltChromeSrc = src => {
  const s = (src || "").toLowerCase();
  return /getsitelogo|siteiconmanager|background-new\.|\/siteassets\/brand-images\//.test(s);
};
const builtNamedImgKeys = new Set();          // ALL named built images (for filename matching)
const builtNamedContentImgKeys = new Set();   // named content images only (drives the fallback decision)
const builtNamedContentRefs = [];             // ordered DISTINCT named content refs {key, src} (positional distinctness fallback)
let builtOpaqueContentImgCount = 0;           // opaque images in the content area (the real canvas images)
// A built ref is a PLACEHOLDER/empty if it has no real filename token: empty, generic blank/spacer/
// placeholder names, or a 1x1/transparent stub. Such a ref cannot satisfy a source content image.
const isPlaceholderBuiltRef = (k, src) => {
  const s = (src || "").toLowerCase();
  if (!k) return true;
  if (/^(blank|spacer|placeholder|empty|transparent|1x1|pixel|noimage|default)\b/.test(k)) return true;
  if (/\/(blank|spacer|placeholder|empty)\b/.test(s)) return true;
  return false;
};
const builtNamedContentSeen = new Set();      // de-dup distinct refs by key
const builtDuplicateContentRefs = [];         // built content refs that repeated (a duplicate import smell)
for (const i of (built.images || [])) {
  const isContent = (i.area || "content") === "content";
  if (isOpaqueBuiltSrc(i.src)) {
    if (isContent && !isBuiltChromeSrc(i.src)) builtOpaqueContentImgCount++;
    continue;
  }
  if (isBuiltChromeSrc(i.src)) continue; // named chrome (wallpaper/logo) — out of scope
  const k = imgKey(i.src);
  if (!k) continue;
  builtNamedImgKeys.add(k);
  if (isContent) {
    builtNamedContentImgKeys.add(k);
    if (isPlaceholderBuiltRef(k, i.src)) {
      // a placeholder/empty content ref is NOT a resolvable image — do not let it satisfy a source image
      continue;
    }
    if (builtNamedContentSeen.has(k)) { builtDuplicateContentRefs.push(k); continue; }
    builtNamedContentSeen.add(k);
    builtNamedContentRefs.push({ key: k, src: i.src });
  }
}
const builtImgKeys  = builtNamedImgKeys; // named-only set for basename matching
// Count of genuine built content images (named content + opaque content canvas renders).
const builtContentImgCount = builtNamedContentImgKeys.size + builtOpaqueContentImgCount;
const builtLinkKeys = new Set((built.links  || []).map(l => linkKey(l.link)).filter(Boolean));
const builtTextNorm = (built.text || []).map(normText).filter(Boolean);
// Searchable blob for SHINGLE matching: tokenized (punctuation stripped) so source shingles match
// regardless of punctuation-placement differences between the two captures.
const builtBlob     = shingleTokens(builtTextNorm.join("  "));

// ---- DIFF: IMAGES ----------------------------------------------------------
// Match precedence per source content image:
//   1. image-map hit  -> built basename known -> present iff that basename is in the built set (true IDENTITY).
//   2. basename hit    -> source basename survives migration unchanged -> present (flag UNMAPPED: not via map).
//   3. distinctness    -> built CONTENT refs are NAMED but renamed (e.g. "00-foo.png") and we have no map:
//                         consume one DISTINCT, resolvable (non-placeholder, non-duplicate) built ref
//                         positionally and FLAG it UNMAPPED. Runs out of refs -> MISSING (shortfall). This
//                         is the T3b element-level guard: a swapped/dropped/duplicated/placeholder ref FAILS.
//   4. opaque canvas   -> built renders content images as blob/resource (no filename) -> defer to count-parity.
//   5. otherwise        -> MISSING.
const missingImages = [];     // genuinely absent (built exposes refs but none available for this source image)
const unnameableImages = [];  // source images whose built counterpart is opaque (blob/resource) — count-checked
const unmappedImages = [];    // in-scope source images matched WITHOUT a migration-map entry (flagged, not silent)
const distinctMatched = [];   // source images satisfied by positional distinctness {name, builtRef}
const builtRefPool = builtNamedContentRefs.slice(); // consumable pool of distinct resolvable built content refs
const hasNamedBuiltContent = builtNamedContentRefs.length > 0;
for (const im of srcImages) {
  if (!im.src) continue;
  const { key, mapped } = builtKeyForSourceImage(im.src);
  if (!key) continue;
  if (mapped) {
    // IDENTITY via map: the built basename is asserted. Present iff actually in the built set.
    if (builtImgKeys.has(key)) continue;
    // map says this source image migrated to <key>, but the built page has no such ref -> genuinely MISSING.
    missingImages.push({ name: key, alt: im.alt || "", src: im.src, zone: im.zone || "", mapped: true });
    continue;
  }
  // No map entry. Try a literal basename match first (some assets keep their name).
  if (builtImgKeys.has(key)) {
    unmappedImages.push({ name: key, src: im.src, zone: im.zone || "", how: "basename" });
    continue;
  }
  // Renamed-and-no-map case: if the built side exposes NAMED content refs, consume one DISTINCT
  // resolvable ref positionally. This proves a real, distinct, non-placeholder built image backs this
  // source image — catching a dropped/duplicated/placeholder ref as a SHORTFALL — while FLAGGING that
  // identity could not be confirmed (no map).
  if (hasNamedBuiltContent) {
    if (builtRefPool.length > 0) {
      const ref = builtRefPool.shift();
      distinctMatched.push({ name: key, builtRef: ref.key, src: im.src });
      unmappedImages.push({ name: key, src: im.src, zone: im.zone || "", how: "distinct:" + ref.key });
      continue;
    }
    // pool exhausted -> more in-scope source images than distinct resolvable built refs -> MISSING.
    missingImages.push({ name: key, alt: im.alt || "", src: im.src, zone: im.zone || "", mapped: false });
    continue;
  }
  // Built page exposes NO named content images but DOES render opaque canvas images -> count-parity.
  if (builtNamedContentImgKeys.size === 0 && builtOpaqueContentImgCount > 0) {
    unmappedImages.push({ name: key, src: im.src, zone: im.zone || "", how: "src-basename" });
    unnameableImages.push({ name: key, alt: im.alt || "", src: im.src, zone: im.zone || "", mapped });
  } else {
    missingImages.push({ name: key, alt: im.alt || "", src: im.src, zone: im.zone || "", mapped });
  }
}
// COUNT/PARITY check for opaque-canvas content images: the built page must render at LEAST as many
// content images as the in-scope source has. A shortfall is a real FAIL naming the count gap.
const imageCountShortfall = unnameableImages.length > 0
  ? Math.max(0, srcImages.length - builtContentImgCount)
  : 0;

const missingLinks = [];
for (const ln of srcLinks) {
  const k = linkKey(ln.link);
  if (!k) continue;
  if (!builtLinkKeys.has(k)) missingLinks.push({ target: k, text: ln.text || "", link: ln.link });
}

// SHINGLE matching (FIX 1): instead of requiring a whole source block to appear verbatim as one
// substring (which a single mojibake/▯ byte or a re-wrap breaks), split each source block into
// overlapping K-word shingles and PASS the block iff >= SHINGLE_THRESHOLD of its shingles are found
// in the tokenized built blob. Genuinely-absent paragraphs still FAIL (a fully-absent block has 0%
// of its shingles present) — fail-closed is preserved; verified with a negative test.
const missingText = [];
const textShingleStats = [];
for (const t of srcText) {
  const n = normText(t);
  if (n.length < 8) continue; // ignore trivially short blocks
  const sh = shinglesOf(n);
  if (sh.length === 0) continue;
  let hit = 0;
  for (const s of sh) if (builtBlob.includes(s)) hit++;
  const frac = hit / sh.length;
  textShingleStats.push({ frac: +frac.toFixed(2), hit, total: sh.length, preview: t.slice(0, 60) });
  if (frac < SHINGLE_THRESHOLD) {
    const label = t.length > 90 ? t.slice(0, 90) + "…" : t;
    missingText.push(label + "  [shingles " + hit + "/" + sh.length + "=" + frac.toFixed(2) + " < " + SHINGLE_THRESHOLD + "]");
  }
}

// ---- PUBLISHED + SECTIONS assertions --------------------------------------
// Published: a real authenticated SP page renders a <title> that is not a sign-in/error page
// and not empty. (Sign-in already hard-failed above.) We also reject obvious "page not found".
const builtTitle = (built.title || "").trim();
const publishProblems = [];
if (!builtTitle) publishProblems.push("built page has empty <title> (likely not rendered/published)");
if (/page not found|404|error|access denied/i.test(builtTitle)) publishProblems.push('built <title> looks like an error page: "' + builtTitle + '"');

// SECURITY / FAIL-CLOSED: a non-error <title> is NOT proof of publication — a draft or
// checked-out page can render a perfectly valid title. Require authoritative SharePoint
// publication metadata (Graph sitePage publishingState.level, or the list item moderation
// / publication field) to affirmatively say "published". If that metadata is absent or
// could not be fetched, treat the page as NOT published (fail closed) — never assume it.
const pubLevel  = String(built.publishingState?.level ?? built.publishingLevel ?? "").toLowerCase();
const modStatus = built.listItem?.fields?._ModerationStatus ?? built.moderationStatus;
const isPublished =
  pubLevel === "published" || pubLevel === "checkedin" ||
  built.published === true ||
  modStatus === 0 || modStatus === "0" || String(modStatus).toLowerCase() === "approved";
if (!isPublished) {
  publishProblems.push("cannot confirm SharePoint publication state (no authoritative publishingState/moderation metadata) — treating as NOT published (fail-closed)");
}

// Sections: count distinct content zones as a proxy for SP canvas sections, OR honour an explicit
// built.sections count if the capture provides one. Content images+links grouped by zone.
let sectionCount;
if (typeof built.sections === "number") {
  sectionCount = built.sections;
} else {
  const zones = new Set();
  for (const i of (built.images || [])) if ((i.area || "content") === "content" && i.zone) zones.add("z:" + i.zone);
  for (const l of (built.links  || [])) if ((l.area || "content") === "content" && l.zone) zones.add("z:" + l.zone);
  // floor of 1 if there is any content at all (some zones come back empty-string)
  const anyContent = (built.images || []).some(i => (i.area||"content")==="content") || (built.links||[]).some(l => (l.area||"content")==="content") || (built.text||[]).length > 0;
  sectionCount = zones.size || (anyContent ? 1 : 0);
}
const sectionsOk = sectionCount >= minSections;

// ---- VERDICT ---------------------------------------------------------------
const pass = missingImages.length === 0 && imageCountShortfall === 0 && missingLinks.length === 0 &&
             missingText.length === 0 && publishProblems.length === 0 && sectionsOk;

const verdict = {
  gate: "completeness",
  pass,
  source: sourcePath,
  sourceUrl: source.source || null,
  builtUrl: builtUrl || null,
  builtManifest: builtManPath || capturedTo,
  builtTitle,
  scope: "content-only (tenant chrome + global nav excluded)",
  checked: { images: srcImages.length, links: srcLinks.length, text: srcText.length, areas },
  excludedOutOfScope: { chromeImages: excludedImages, navLinks: excludedLinks },
  imageMap: {
    path: imageMapPath || null,
    loaded: imageMap.loaded,
    entries: imageMap.entries,
    unmappedInScopeImages: unmappedImages.map(u => u.name),
    warnings: imageMapWarnings
  },
  imagesCheck: {
    builtNamedImages: builtNamedImgKeys.size,
    builtNamedContentImages: builtNamedContentImgKeys.size,
    builtDistinctResolvableContentRefs: builtNamedContentRefs.length,
    builtOpaqueContentImages: builtOpaqueContentImgCount,
    builtContentImages: builtContentImgCount,
    nameMatched: srcImages.length - missingImages.length - unnameableImages.length - distinctMatched.length,
    distinctMatched: distinctMatched.map(d => ({ source: d.name, builtRef: d.builtRef })),
    duplicateBuiltContentRefs: builtDuplicateContentRefs,
    unnameable: unnameableImages.map(u => u.name),
    countShortfall: imageCountShortfall,
    note: distinctMatched.length
      ? "built page exposes NAMED-but-renamed content refs and no image-map covers them — matched by DISTINCT positional resolution (no duplicate/placeholder refs). Identity is NOT confirmed; refs flagged UNMAPPED. Populate the image-map in the BUILD step for true identity matching."
      : unnameableImages.length
      ? "built page renders content images as opaque (blob/resource) URLs — verified by COUNT/PARITY, not filename. Image-map/basename matching cannot apply on a modern-canvas page."
      : "verified by filename"
  },
  textCheck: {
    method: "shingle (K=" + SHINGLE_K + "-word, threshold " + SHINGLE_THRESHOLD + ") over mojibake/punctuation-normalized text",
    blocksChecked: textShingleStats.length,
    blocksMissing: missingText.length,
    perBlock: textShingleStats
  },
  sections: { count: sectionCount, min: minSections, ok: sectionsOk },
  published: { ok: publishProblems.length === 0, problems: publishProblems },
  missing: {
    images: missingImages.map(m => m.name),
    links:  missingLinks.map(m => m.target),
    text:   missingText
  },
  missingDetail: { images: missingImages, links: missingLinks, text: missingText }
};

// human-readable
const L = [];
L.push("== COMPLETENESS GATE ==");
L.push("source:   " + (verdict.sourceUrl || sourcePath));
L.push("built:    " + (builtUrl || builtManPath));
L.push("title:    " + (builtTitle || "(empty)"));
L.push("scope:    content-only (excluded " + excludedImages + " chrome image(s) + " + excludedLinks + " nav link(s) as out-of-scope)");
L.push("checked:  " + srcImages.length + " images, " + srcLinks.length + " links, " + srcText.length + " text blocks (areas: " + areas.join("+") + ")");
L.push("image-map:" + (imageMap.loaded ? " " + imageMap.entries + " entr" + (imageMap.entries === 1 ? "y" : "ies") + " loaded" : " (none)"));
for (const w of imageMapWarnings) L.push("WARN: " + w);
for (const u of unmappedImages) {
  const via = u.how && u.how.startsWith("distinct:")
    ? "matched to a DISTINCT built ref '" + u.how.slice("distinct:".length) + "' (renamed; identity NOT map-confirmed)"
    : "matched by source basename, not migration map";
  L.push("WARN unmapped image (" + via + "): " + u.name);
}
for (const d of builtDuplicateContentRefs) L.push("WARN built page has a DUPLICATE content image ref: " + d + " (repeated import — cannot back two distinct source images)");
if (distinctMatched.length) {
  L.push("images:   " + distinctMatched.length + " source content image(s) matched by DISTINCT positional resolution (built refs renamed, no image-map).");
  L.push("          distinct resolvable built content refs: " + builtNamedContentRefs.length + " vs source in-scope: " + srcImages.length +
         (missingImages.length ? "  -> SHORTFALL " + missingImages.length : "  -> OK (no swap/drop/dup detectable at identity level without a map)"));
} else if (unnameableImages.length) {
  L.push("images:   " + unnameableImages.length + " source content image(s) verified by COUNT/PARITY (built renders them as opaque blob/resource URLs — no filename to match).");
  L.push("          built content images: " + builtContentImgCount + " vs source in-scope: " + srcImages.length +
         (imageCountShortfall ? "  -> SHORTFALL " + imageCountShortfall : "  -> OK"));
} else {
  L.push("images:   " + (srcImages.length - missingImages.length) + "/" + srcImages.length + " matched by filename.");
}
L.push("sections: " + sectionCount + " (min " + minSections + ") " + (sectionsOk ? "OK" : "FAIL"));
L.push("published:" + (publishProblems.length ? " FAIL — " + publishProblems.join("; ") : " OK"));
for (const m of missingImages) L.push("MISSING image: " + m.name + (m.mapped ? " [image-map says it migrated here, but no such built ref]" : " [no distinct built ref available — built short on content images]") + (m.alt ? '  (alt="' + m.alt + '")' : ""));
if (imageCountShortfall) L.push("MISSING images (by count): built has " + builtContentImgCount + " content image(s), source needs " + srcImages.length + " — " + imageCountShortfall + " short.");
for (const m of missingLinks)  L.push("MISSING link: "  + m.target + (m.text ? '  ("' + m.text + '")' : ""));
for (const m of missingText)   L.push("MISSING text: "  + m);
L.push(pass ? "VERDICT: PASS — built page is complete." :
              "VERDICT: FAIL — " + (missingImages.length + imageCountShortfall + missingLinks.length + missingText.length) +
              " missing element(s)" + (sectionsOk ? "" : " + sections") + (publishProblems.length ? " + publish" : "") + ".");
console.log(L.join("\n"));

if (outPath) writeFileSync(outPath, JSON.stringify(verdict, null, 2));

process.exit(pass ? 0 : 1);
