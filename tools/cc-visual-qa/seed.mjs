// One-time M365 seed: open a real browser, you sign in, we save the authenticated
// session (storageState) for reuse by headless visual-QA runs. Run: node seed.mjs
import { chromium } from "playwright";
import { mkdirSync, chmodSync } from "node:fs";
import { dirname } from "node:path";

const SITE = "https://contoso.sharepoint.com/sites/CodeCraftAICommandCenter";
const STATE = process.env.HOME + "/.codecraft/sp-storage-state.json";
mkdirSync(dirname(STATE), { recursive: true });

const browser = await chromium.launch({ headless: false });
const ctx = await browser.newContext();
const page = await ctx.newPage();
await page.goto(SITE).catch(() => {});
console.log(">>> Sign in to Microsoft 365 (incl. MFA). Waiting up to 8 minutes...");

let ok = false;
for (let i = 0; i < 120; i++) {
  await page.waitForTimeout(4000);
  let url = "";
  try { url = page.url(); } catch {}
  const cookies = await ctx.cookies().catch(() => []);
  const spCookie = cookies.some((c) => (c.domain || "").includes("sharepoint.com"));
  const onSite = url.includes("contoso.sharepoint.com") && !/login\.|\/_forms\/|signin/i.test(url);
  if (i % 5 === 0) console.log(`  [poll ${i}] url=${url.slice(0, 70)} spCookie=${spCookie} onSite=${onSite}`);
  if (spCookie && onSite) { ok = true; break; }
}

if (ok) {
  await page.waitForTimeout(3000);
  await ctx.storageState({ path: STATE });
  chmodSync(STATE, 0o600);
  console.log("SEED_OK -> " + STATE);
} else {
  console.log("SEED_TIMEOUT — still no authenticated SharePoint session detected.");
}
await browser.close();
