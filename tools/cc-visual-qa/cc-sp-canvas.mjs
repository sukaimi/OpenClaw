// cc-sp-canvas: capture a BUILT modern SharePoint page's manifest from its WEB-PART JSON
// (CanvasContent1) via SP REST — NOT from the rendered DOM. The DOM renders content images as
// opaque `blob:` URLs (migrated filename unrecoverable); CanvasContent1 carries the REAL migrated
// image references (serverProcessedContent.imageSources.imageSource), link targets
// (properties.imageLinkUrl + <a href> in text web parts) and authored text. This enables true
// element-level matching in cc-completeness-gate.mjs instead of weak COUNT-PARITY.
//
// Output shape matches cc-sp-manifest.mjs (source:, title, images[], links[], text[], sections)
// so the gate's diff logic is unchanged. Built image `src` values are now real serverRelativeUrls.
//
// Usage: node cc-sp-canvas.mjs <pageUrl> <out.json> [--state <storageState.json>]
//   pageUrl: full URL to the built page, e.g.
//     https://contoso.sharepoint.com/sites/CCBuild-0023/SitePages/Home.aspx
//
// Fail-closed: any auth/REST/parse error -> non-zero exit, no manifest written, NEVER a silent pass.

import { chromium } from "playwright";
import { existsSync, writeFileSync } from "node:fs";

const pageUrl = process.argv[2];
const outPath = process.argv[3];
const stateArg = (() => { const i = process.argv.indexOf("--state"); return i > 0 ? process.argv[i + 1] : null; })();

if (!pageUrl || !outPath) {
  console.error("usage: node cc-sp-canvas.mjs <pageUrl> <out.json> [--state <storageState.json>]");
  process.exit(2);
}

// Derive {siteUrl, serverRelativePagePath} from the full page URL.
let siteUrl, pageServerRelative;
try {
  const u = new URL(pageUrl);
  // site = origin + everything up to and including /sites/<name> (or root web). SitePages lives under the web.
  const path = u.pathname; // /sites/CCBuild-0023/SitePages/Home.aspx
  const m = path.match(/^(.*?)\/(SitePages\/[^/]+\.aspx)$/i);
  if (!m) throw new Error("page URL must end with /SitePages/<Name>.aspx — got " + path);
  siteUrl = u.origin + (m[1] || "");
  pageServerRelative = m[2]; // SitePages/Home.aspx (relative to the web)
} catch (e) {
  console.error("FAIL: cannot parse page URL: " + e.message);
  process.exit(2);
}

const STATE = stateArg || (process.env.HOME + "/.codecraft/sp-storage-state.json");
if (!existsSync(STATE)) {
  console.error("FAIL: storageState not found: " + STATE + " (need an authed Playwright session for the build tenant)");
  process.exit(2);
}

const browser = await chromium.launch({ headless: true });
let exitCode = 0;
try {
  const ctx = await browser.newContext({ storageState: STATE });
  const page = await ctx.newPage();
  // Land on the site root so relative _api calls carry the right cookies/origin.
  await page.goto(siteUrl, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});

  const rest = await page.evaluate(async ({ siteUrl, pageRel }) => {
    const sel = "$select=Title,CanvasContent1,Url,PromotedState";
    const url = siteUrl + "/_api/sitepages/pages/GetByUrl('" + pageRel + "')?" + sel;
    try {
      const r = await fetch(url, { headers: { "Accept": "application/json;odata=nometadata" } });
      if (!r.ok) return { ok: false, status: r.status, body: (await r.text()).slice(0, 400) };
      const j = await r.json();
      return { ok: true, status: r.status, data: j };
    } catch (e) {
      return { ok: false, status: 0, body: "fetch threw: " + e.message };
    }
  }, { siteUrl, pageRel: pageServerRelative });

  if (!rest.ok) {
    console.error("FAIL: SP REST GetByUrl returned HTTP " + rest.status + " — " + (rest.body || "").slice(0, 300));
    console.error("  A REST/auth error is treated as INCOMPLETE — the gate does NOT silently pass.");
    process.exit(4);
  }
  const d = rest.data || {};
  const title = d.Title || "";
  // Sign-in interception guard.
  if (/sign in to your account/i.test(title)) {
    console.error('FAIL: page resolved to a sign-in title ("' + title + '") — not authenticated for this tenant.');
    process.exit(4);
  }
  const canvas = d.CanvasContent1;
  if (typeof canvas !== "string" || !canvas.trim()) {
    console.error("FAIL: CanvasContent1 is empty/missing — page has no web-part content (not built/published?).");
    process.exit(4);
  }
  let parts;
  try { parts = JSON.parse(canvas); }
  catch (e) { console.error("FAIL: CanvasContent1 is not valid JSON: " + e.message); process.exit(4); }
  if (!Array.isArray(parts)) { console.error("FAIL: CanvasContent1 did not parse to an array of controls."); process.exit(4); }

  const abs = u => { try { return new URL(u, siteUrl).href; } catch { return u; } };
  const images = [];   // {src, alt, link, zone, area, kind}
  const links = [];    // {text, link, area, zone}
  const text = [];     // authored text strings
  let sectionSet = new Set();

  for (const c of parts) {
    // section index (canvas sections) for the published/sections assertion
    const pos = c.position || {};
    if (typeof pos.sectionIndex === "number") sectionSet.add(pos.sectionIndex);

    const data = c.webPartData || {};
    const props = data.properties || {};
    const spc = data.serverProcessedContent || {};

    // ---- IMAGE web parts (controlType 3) — REAL migrated image refs ----
    // image source lives in serverProcessedContent.imageSources.imageSource (preferred) or props.
    const imgSrc =
      (spc.imageSources && (spc.imageSources.imageSource || spc.imageSources["imageSource"])) ||
      props.imageSource || props.src || props.serverRelativeUrl || "";
    if (imgSrc) {
      images.push({
        src: abs(imgSrc),
        alt: (props.altText || data.title || "").slice(0, 60),
        link: props.imageLinkUrl ? abs(props.imageLinkUrl) : "",
        zone: data.title || "Image",   // authored web-part title, not a DOM ARIA label
        area: "content",
        kind: "canvas-image"
      });
      // an image web part's link target is authored content -> count it as a link too
      if (props.imageLinkUrl) links.push({ text: (props.altText || "").slice(0, 60), link: abs(props.imageLinkUrl), area: "content", zone: "imageLink" });
    }

    // ---- TEXT web parts (controlType 4) — authored html: text + <a href> links ----
    const html = data.innerHTML || c.innerHTML || props.innerHTML || "";
    if (html) {
      // strip tags for the text blob
      const plain = html
        .replace(/<a\b[^>]*>(.*?)<\/a>/gi, " $1 ")
        .replace(/<[^>]+>/g, " ")
        .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&copy;/g, "©")
        .replace(/\s+/g, " ").trim();
      if (plain.length > 4) text.push(plain);
      // authored anchors -> content links
      const re = /<a\b[^>]*\bhref=["']([^"']+)["'][^>]*>(.*?)<\/a>/gi;
      let mm;
      while ((mm = re.exec(html)) !== null) {
        const href = mm[1].replace(/&amp;/g, "&");
        const t = (mm[2] || "").replace(/<[^>]+>/g, "").trim();
        links.push({ text: t.slice(0, 60), link: abs(href), area: "content", zone: "textLink" });
      }
    }
  }

  const manifest = {
    source: pageUrl,
    title,
    sections: sectionSet.size || (images.length || links.length || text.length ? 1 : 0),
    images,
    links,
    text
  };
  writeFileSync(outPath, JSON.stringify(manifest, null, 1));
  console.log("CANVAS capture OK:", pageUrl);
  console.log("  title:", title, "| PromotedState:", d.PromotedState);
  console.log("  web-part controls:", parts.length, "| sections:", manifest.sections);
  console.log("  images:", images.length, "| links:", links.length, "| text blocks:", text.length);
  console.log("  image refs:", images.map(i => i.src.split("/").pop()).join(", "));
} catch (e) {
  console.error("FAIL: canvas capture errored: " + e.message);
  exitCode = 4;
} finally {
  await browser.close();
}
process.exit(exitCode);
