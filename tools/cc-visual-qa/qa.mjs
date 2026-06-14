// Domain-agnostic visual QA: screenshot ANY url headless.
// Usage: node qa.mjs <url> <outPng> [--auth]
// --auth  load the seeded M365 storageState (for SharePoint behind login).
//         Omit it for public web/EDM URLs (no session needed).
// Emits one line of JSON: {authed,title,finalUrl,out,ok}
import { chromium } from "playwright";
import { existsSync } from "node:fs";

const args = process.argv.slice(2);
const useAuth = args.includes("--auth");
const positional = args.filter((a) => a !== "--auth");
const url = positional[0];
const out = positional[1];

if (!url || !out) {
  console.log(JSON.stringify({ ok: false, error: "usage: node qa.mjs <url> <outPng> [--auth]" }));
  process.exit(2);
}

const STATE = process.env.HOME + "/.codecraft/sp-storage-state.json";
const ctxOpts = { viewport: { width: 1440, height: 1000 } };

if (useAuth) {
  if (!existsSync(STATE)) {
    console.log(JSON.stringify({ ok: false, error: "no storageState at " + STATE + " (run seed.mjs)", out }));
    process.exit(3);
  }
  ctxOpts.storageState = STATE;
}

let ok = false, title = "", finalUrl = "", authed = false;
const browser = await chromium.launch({ headless: true });
try {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3500);
  finalUrl = page.url();
  authed = useAuth && !/login\.microsoftonline|\/signin|\/_forms\//i.test(finalUrl);
  title = await page.title().catch(() => "");
  // SharePoint modern pages scroll inside an inner region, not the body, so
  // fullPage only ever sees the first viewport. The inner-scroll container only
  // engages when the viewport is short — measure the real content height and
  // grow the viewport to match so the whole page (incl. footer) renders inline.
  const contentH = await page.evaluate(() => {
    const sel = '[data-automation-id="contentScrollRegion"], .SPPageChrome-content, [class*="scrollRegion"], .CanvasZone';
    const heights = [document.scrollingElement?.scrollHeight || 0];
    for (const r of document.querySelectorAll(sel)) heights.push(r.scrollHeight || 0);
    return Math.max(...heights);
  }).catch(() => 0);
  if (contentH > 1000) {
    await page.setViewportSize({ width: 1440, height: Math.min(contentH + 200, 20000) });
    await page.waitForTimeout(1500);
  }
  await page.screenshot({ path: out, fullPage: true });
  ok = true;
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: String(e).slice(0, 200), out }));
  await browser.close();
  process.exit(1);
}
await browser.close();
console.log(JSON.stringify({ authed, title, finalUrl: finalUrl.slice(0, 120), out, ok }));
