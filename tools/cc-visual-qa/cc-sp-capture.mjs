// cc-sp-capture: interactive/delegated source capture for SharePoint classic->modern conversion.
// Pulls a CLIENT's classic site over an authenticated BROWSER session (the FARA model:
// a human logs in once via the popup), so NOTHING needs to be provisioned in the client
// tenant (no app-consent, no Sites.Selected). Produces a capture/ bundle that the server's
// `sp-audit.py --from-capture <dir>` parses into the same sp-expect.json + enrich.json.
//
// Usage:
//   node cc-sp-capture.mjs <SOURCE_SITE_URL> --job <JOB> [--out <dir>] [--login] [--state <path>]
//     --login        headed browser: human logs in via the popup; the session is
//                    persisted to <state> for reuse. Use this for a first-time client.
//     (default)      headless, reuse the seeded storageState at <state>.
//     --state <p>    storageState path (default ~/.codecraft/sp-storage-state.json).
//     --out <dir>    bundle dir (default ./capture-<JOB>).
//
// Emits one JSON line: {ok, pages, images, nav, out, error?}
import { chromium } from "playwright";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const val = (f, d) => { const i = argv.indexOf(f); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const positional = argv.filter((a, i) => !a.startsWith("--") && !(i > 0 && ["--job", "--out", "--state", "--only", "--pages", "--inventory-out"].includes(argv[i - 1])));

const sourceUrl = positional[0];
const job = val("--job");
const interactive = has("--login");
const PROBE = has("--probe");   // enumerate pages/lists/nav only; skip image downloads
const ONLY = (() => { const a = val("--only") || val("--pages"); return a ? new Set(a.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)) : null; })();  // capture only these page filenames (--pages is an alias for --only)
const STATE = val("--state", process.env.HOME + "/.codecraft/sp-storage-state.json");
const INVENTORY_OUT = val("--inventory-out", null);  // when given, write full page list to this path

function fail(error, code = 1) { console.log(JSON.stringify({ ok: false, error: String(error).slice(0, 300) })); process.exit(code); }
if (!sourceUrl || !job) fail("usage: node cc-sp-capture.mjs <SOURCE_SITE_URL> --job <JOB> [--out <dir>] [--login] [--state <path>]", 2);

const outDir = val("--out", `./capture-${job}`);

// Normalise any deeper URL to the site root (mirrors sp-audit._site_root).
function siteRoot(u) {
  u = u.replace(/\/+$/, "");
  let m = u.match(/^(https?:\/\/[^/]+\/sites\/[^/]+)(?:\/.*)?$/i);
  if (m) return m[1];
  m = u.match(/^(https?:\/\/[^/]+\/teams\/[^/]+)(?:\/.*)?$/i);
  if (m) return m[1];
  return u;
}
const ROOT = siteRoot(sourceUrl);
const ORIGIN = new URL(ROOT).origin;
const isLogin = (url) => /login\.microsoftonline|\/signin|\/_forms\/|\/login\.aspx/i.test(url || "");

// SharePoint REST: read the page library + nav + lists over the authed session.
const SP_REST_PAGE_LISTS = ["Site Pages", "Pages"];
const ACCEPT = { Accept: "application/json;odata=nometadata" };

async function getJson(req, url) {
  const r = await req.get(url, { headers: ACCEPT, timeout: 60000 });
  if (r.status() >= 300) return null;
  try { return await r.json(); } catch { return null; }
}

async function main() {
  if (!interactive && !existsSync(STATE)) fail(`no storageState at ${STATE} — run with --login once (or seed.mjs)`, 3);
  mkdirSync(join(outDir, "pages"), { recursive: true });
  mkdirSync(join(outDir, "images"), { recursive: true });

  const browser = await chromium.launch({ headless: !interactive });
  const ctxOpts = { viewport: { width: 1440, height: 1000 } };
  if (existsSync(STATE)) ctxOpts.storageState = STATE;
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();

  // Establish the session. Detect REAL authentication by polling the SharePoint _api
  // itself (200 = authed) rather than guessing from the URL — robust to enterprise IdP
  // redirects (login.microsoftonline / ADFS / _forms) and Conditional Access.
  const apiAuthed = async () => {
    try { const r = await ctx.request.get(ROOT + "/_api/web?$select=Title", { headers: ACCEPT, timeout: 15000 }); return r.status() === 200; }
    catch { return false; }
  };
  await page.goto(ROOT, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  if (interactive) {
    const deadline = Date.now() + 300000;
    while (!(await apiAuthed()) && Date.now() < deadline) await page.waitForTimeout(3000);
    if (await apiAuthed()) await ctx.storageState({ path: STATE }); // persist the live session for reuse
  }
  if (!(await apiAuthed())) {
    await browser.close();
    fail("not authenticated to SharePoint _api (not 200) — the login session is not granting API access. Most likely Conditional Access / device-compliance is blocking this (unmanaged) browser, or the account lacks access to this site.", 4);
  }

  const req = ctx.request;

  // 1) Pages: read the wiki/modern page library AND the classic publishing 'Pages'
  // library. Publishing pages keep their body in PublishingPageContent (NOT WikiField/
  // CanvasContent1), so query each library with the fields that exist on it, accumulate
  // across both, and de-dup by filename.
  const PAGE_LIBS = [
    { title: "Site Pages", select: "FileLeafRef,Title,WikiField,CanvasContent1,Modified,Created" },
    { title: "Pages", select: "FileLeafRef,Title,PublishingPageContent,Modified,Created" },
  ];
  const pages = [];
  const inventoryAll = [];  // FULL list (before ONLY filter) for --inventory-out
  const seenPage = new Set();
  const seenInv = new Set();
  for (const lib of PAGE_LIBS) {
    const u = `${ROOT}/_api/web/lists/getbytitle('${encodeURIComponent(lib.title)}')/items?$select=${lib.select}&$top=500`;
    const data = await getJson(req, u);
    if (!data || !data.value) continue;
    for (const it of data.value) {
      const nm = it.FileLeafRef || "";
      const key = nm.toLowerCase();
      if (!key.endsWith(".aspx")) continue;
      // Collect into full inventory (de-dup by filename)
      if (!seenInv.has(key)) {
        seenInv.add(key);
        // complexity signals for triage (heuristic — used to FLAG pages, not perfectly classify)
        const invBody = it.WikiField || it.CanvasContent1 || it.PublishingPageContent || "";
        const wpHits = invBody.match(/webPartData|data-sp-webpart|ms-rte-wpbox|WebPartZone|<webPart\b/gi);
        const isPublishing = lib.title === "Pages" || !!it.PublishingPageContent;
        const hasListWebpart = /XsltListViewWebPart|ListViewWebPart|ContentByQuery|CarouselWebPart|"isListLayout"|listId/i.test(invBody);
        inventoryAll.push({
          title:    it.Title || nm.slice(0, -5),
          file:     nm,
          lib:      lib.title,
          modified: it.Modified || "",
          created:  it.Created  || "",
          bytes:    invBody.length,
          webPartCount: wpHits ? wpHits.length : 0,
          isPublishing,
          hasListWebpart,
        });
      }
      // Apply ONLY filter and de-dup for body capture
      if (seenPage.has(key)) continue;
      if (ONLY && !ONLY.has(key)) continue;
      const body = it.WikiField || it.CanvasContent1 || it.PublishingPageContent || "";
      seenPage.add(key);
      writeFileSync(join(outDir, "pages", nm + ".html"), body, "utf8");
      pages.push({ name: nm, title: it.Title || nm.slice(0, -5), body: `pages/${nm}.html`, lib: lib.title, bytes: body.length });
    }
  }
  if (!inventoryAll.length) { await browser.close(); fail("no .aspx pages found in 'Site Pages'/'Pages' over the authed session", 5); }
  // When probe-only with ONLY filter there may be no body-captured pages — that's OK.
  if (!PROBE && !pages.length) { await browser.close(); fail("no .aspx pages matched the --only/--pages filter", 5); }
  // Write full inventory if requested (BEFORE any ONLY filter — all pages on the site)
  if (INVENTORY_OUT) {
    const { mkdirSync: mkd, writeFileSync: wfs } = await import("node:fs");
    const { dirname } = await import("node:path");
    mkd(dirname(INVENTORY_OUT), { recursive: true });
    wfs(INVENTORY_OUT, JSON.stringify(inventoryAll, null, 1));
  }

  // 2) Images: download every <img src> referenced by the page bodies (server matches by src).
  const imagesMap = {};
  let idx = 0;
  if (!PROBE) for (const p of pages) {
    const body = (await import("node:fs")).readFileSync(join(outDir, p.body), "utf8");
    const tags = body.match(/<img\b[^>]*>/gi) || [];
    for (const tag of tags) {
      const m = tag.match(/src\s*=\s*["']([^"']+)["']/i);
      if (!m) continue;
      let src = m[1].replace(/&amp;/g, "&").trim();
      if (!src || /^data:/i.test(src) || imagesMap[src]) continue;
      let abs;
      try { abs = new URL(src, ORIGIN + "/").href; } catch { continue; }
      const r = await req.get(abs, { timeout: 60000 }).catch(() => null);
      if (!r || r.status() >= 300) continue;
      const buf = await r.body();
      const base = (src.split("?")[0].split("#")[0].split("/").pop() || `img-${idx}`).replace(/[^A-Za-z0-9._-]/g, "-");
      const local = `images/${String(idx).padStart(3, "0")}-${base}`;
      writeFileSync(join(outDir, local), buf);
      imagesMap[src] = local;
      idx++;
    }
  }

  // 3) Nav (top nav + quick launch) and 4) list inventory — best-effort, for nav_migrate + the tracker.
  const nav = {
    topnavigationbar: await getJson(req, `${ROOT}/_api/web/navigation/topnavigationbar`),
    quicklaunch: await getJson(req, `${ROOT}/_api/web/navigation/quicklaunch`),
  };
  const listsData = await getJson(req, `${ROOT}/_api/web/lists?$select=Title,Hidden&$filter=Hidden eq false&$top=200`);
  const lists = (listsData?.value || []).map((l) => ({ name: l.Title })).filter((l) => l.name);

  writeFileSync(join(outDir, "nav.json"), JSON.stringify(nav, null, 1));
  writeFileSync(join(outDir, "images-map.json"), JSON.stringify(imagesMap, null, 1));
  const manifest = {
    _comment: "Captured over an authenticated browser session (delegated auth). Feed to sp-audit.py --from-capture.",
    job, sourceUrl: ROOT, siteRoot: ROOT, sourceSiteId: null,
    sourceKind: "classic-capture", capturedBy: "cc-sp-capture",
    pages, lists, nav: "nav.json", images: "images-map.json",
  };
  writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));

  await browser.close();
  console.log(JSON.stringify({ ok: true, pages: pages.length, inventory: inventoryAll.length, images: Object.keys(imagesMap).length, nav: !!(nav.topnavigationbar || nav.quicklaunch), out: outDir, inventoryOut: INVENTORY_OUT || null }));
}

main().catch((e) => fail(e));
