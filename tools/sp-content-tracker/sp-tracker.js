#!/usr/bin/env node
/**
 * sp-tracker.js — Content Tracker generator for the OpenClaw SP conversion pipeline.
 *
 * Absorbed from FARA's excel-generator.js (de-branded, derived pain-points), but fed
 * by sp-audit.py's sp-expect.json instead of FARA's Playwright scanner.
 *
 * Emits a 3-sheet .xlsx:
 *   Sheet 1  Content Tracker    — one row per asset (heading/text/image/link/document) × 10 cols
 *   Sheet 2  Image Index        — per-image resolution + migrate vs replace-hi-res
 *   Sheet 3  Migration Summary  — status counts + DERIVED pain-points (only those the scan supports)
 *
 * Migration status is ADVISORY ONLY — the build always migrates content verbatim.
 *   Migrate (default) · Review (broken link / low-res / empty) · Archive (stale > cutoff)
 *   · Rewrite (undated or past-dated time-sensitive content)
 *
 * Usage:
 *   node sp-tracker.js <sp-expect.json> <out.xlsx> [--site NAME] [--url URL]
 *                      [--enrich enrich.json] [--today YYYY-MM-DD] [--stale-months N]
 *   --enrich  optional JSON: { brokenLinks:[{url,status}], imageDims:{ "<src>":{w,h} } }
 *             (produced by sp-audit.py: broken-link HEAD checks + measured image bytes)
 */

const ExcelJS = require('exceljs');
const fs = require('fs');

// ---- neutral palette (de-branded from FARA's hardcoded Crestfield navy) ----
const COLORS = {
  titleDark: 'FF1F2937', headerMid: 'FF374151', white: 'FFFFFFFF', lightGrey: 'FFF4F6F9',
  migrateGreen: 'FFE8F5EE', rewriteAmber: 'FFFFF3E0', reviewBlue: 'FFE6EEF8', archiveRed: 'FFFFEBEE',
  whiteText: 'FFFFFFFF',
};
const TIME_SENSITIVE = new Set(['news', 'events', 'announcement']);
const LOWRES_MIN_PX = 400; // natural width below this = flag for hero/modern use

function statusColor(s) {
  return { migrate: COLORS.migrateGreen, rewrite: COLORS.rewriteAmber,
           review: COLORS.reviewBlue, archive: COLORS.archiveRed }[(s || '').toLowerCase()] || COLORS.white;
}

// ---- date parsing for freshness ----
const MONTHS = { jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,oct:9,nov:10,dec:11 };
function parseDates(text) {
  if (!text) return [];
  const out = [];
  // "15 January 2026" / "29 Mar 2026" / "Jan 15, 2026"
  const re1 = /\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b/g;
  const re2 = /\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b/g;
  let m;
  while ((m = re1.exec(text))) { const mo = MONTHS[m[2].slice(0,3).toLowerCase()]; if (mo!=null) out.push(new Date(Date.UTC(+m[3],mo,+m[1]))); }
  while ((m = re2.exec(text))) { const mo = MONTHS[m[1].slice(0,3).toLowerCase()]; if (mo!=null) out.push(new Date(Date.UTC(+m[3],mo,+m[2]))); }
  return out;
}

// ---- explode sp-expect.json content blocks into flat assets ----
function extractLinks(html) {
  if (!html) return [];
  const out = []; const re = /<a[^>]*href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gis; let m;
  while ((m = re.exec(html))) {
    const href = m[1].trim();
    const label = m[2].replace(/<[^>]+>/g, '').trim();
    if (href && href !== '#') out.push({ href, label });
  }
  return out;
}
const isDoc = (href) => /\.(pdf|docx?|xlsx?|pptx?|csv|zip)(\?|$)/i.test(href);

function normalizeAssets(spExpect, opts) {
  const assets = [], images = [];
  const sourceUrl = opts.siteUrl || spExpect.sourceUrl || '';
  let imgN = 0;
  for (const page of (spExpect.pages || [])) {
    const pageName = page.title || page.name || 'Home';
    const pageUrl = page.name ? `${sourceUrl.replace(/\/$/, '')}/SitePages/${page.name}` : sourceUrl;
    for (const block of (page.content || [])) {
      const section = block.heading || block.kind || 'Content';
      const blockDates = parseDates([block.text, block.html, ...(block.items || []).map(i => i.text)].join(' '));
      const freshest = blockDates.length ? new Date(Math.max(...blockDates.map(d => +d))) : null;

      const base = { pageName, pageUrl, section, sourceKind: block.kind, freshest, timeSensitive: TIME_SENSITIVE.has(block.kind) };
      if (block.heading) assets.push({ ...base, assetType: 'Heading', assetDescription: block.heading, assetContent: block.heading });
      const text = (block.text || '').trim();
      if (text) assets.push({ ...base, assetType: 'Text Block', assetDescription: block.kind || 'text', assetContent: text });
      for (const it of (block.items || [])) {
        const t = (it.text || '').trim();
        if (t) assets.push({ ...base, assetType: 'List Item', assetDescription: block.kind || 'item', assetContent: t });
      }
      for (const lnk of extractLinks(block.html)) {
        assets.push({ ...base, assetType: isDoc(lnk.href) ? 'Document' : 'Link',
          assetDescription: lnk.label || lnk.href, assetContent: lnk.label, hyperlink: lnk.href });
      }
      for (const img of (block.images || [])) {
        imgN++; const ref = `IMG_${String(imgN).padStart(3, '0')}`;
        const rec = { ref, src: img.src, filename: img.filename || (img.src || '').split('/').pop(),
          alt: img.alt || '', section, pageName };
        images.push(rec);
        assets.push({ ...base, assetType: 'Image', assetDescription: img.alt || rec.filename,
          assetContent: img.alt || '', imageRef: ref, _imgSrc: img.src });
      }
    }
  }
  return { assets, images };
}

// ---- migration-status ruleset (ADVISORY) ----
function applyRuleset(assets, images, enrich, ctx) {
  const broken = new Map((enrich.brokenLinks || []).map(b => [b.url, b.status]));
  const dims = enrich.imageDims || {};
  const cutoff = new Date(ctx.today); cutoff.setMonth(cutoff.getMonth() - ctx.staleMonths);
  const lowResSrcs = new Set();

  for (const a of assets) {
    let status = 'Migrate', notes = [];
    // empty / garbled
    if (a.assetType !== 'Image' && !(a.assetContent || '').trim()) { status = 'Review'; notes.push('empty/garbled block'); }
    // broken link
    if (a.hyperlink && broken.has(a.hyperlink)) { status = 'Review'; notes.push(`BROKEN LINK (${broken.get(a.hyperlink)})`); }
    // low-res image
    if (a.assetType === 'Image' && a._imgSrc && dims[a._imgSrc]) {
      const w = dims[a._imgSrc].w || 0;
      if (w > 0 && w < LOWRES_MIN_PX) { status = 'Review'; notes.push(`low-res ${w}px (<${LOWRES_MIN_PX})`); lowResSrcs.add(a._imgSrc); }
    }
    // freshness — only escalates if not already Review
    if (status === 'Migrate' && a.timeSensitive) {
      if (!a.freshest) { status = 'Rewrite'; notes.push('undated time-sensitive content'); }
      else if (a.freshest < cutoff) { status = 'Archive'; notes.push(`stale (${a.freshest.toISOString().slice(0,10)})`); }
      else if (a.sourceKind === 'events' && a.freshest < new Date(ctx.today)) { status = 'Rewrite'; notes.push(`past-dated event (${a.freshest.toISOString().slice(0,10)})`); }
    }
    a.migrationStatus = status; a.reviewNotes = notes.join(' | ');
  }
  return { lowResSrcs };
}

function derivePainPoints(counters, navCount) {
  // Only emit a pain-point when the scan actually supports it (derived, not boilerplate).
  const pp = [];
  if (navCount > 8) pp.push(['PP Navigation', `${navCount} navigation/quick links on one page — overload; consolidate to ≤8.`]);
  if (counters.undated > 0) pp.push(['PP Comms', `${counters.undated} time-sensitive item(s) carry no publish date.`]);
  if (counters.broken > 0) pp.push(['PP Links', `${counters.broken} broken link(s) detected (HEAD ≠ 200).`]);
  if (counters.stale > 0) pp.push(['PP Governance', `${counters.stale} stale item(s) past the ${counters.staleMonths}-month freshness cutoff; no owner attribution.`]);
  if (counters.lowres > 0) pp.push(['PP Imagery', `${counters.lowres} low-resolution image(s) flagged for hi-res replacement.`]);
  if (counters.pastEvents > 0) pp.push(['PP Events', `${counters.pastEvents} "upcoming" event(s) are already in the past.`]);
  return pp;
}

async function buildWorkbook(spExpect, opts) {
  const ctx = { today: opts.today || new Date().toISOString().slice(0,10), staleMonths: opts.staleMonths || 12 };
  const siteName = opts.siteName || (spExpect.sourceUrl || 'SITE').split('/').pop();
  const siteUrl = opts.siteUrl || spExpect.sourceUrl || '';
  const enrich = opts.enrich || {};

  const { assets, images } = normalizeAssets(spExpect, opts);
  const { lowResSrcs } = applyRuleset(assets, images, enrich, ctx);

  const counters = {
    pages: (spExpect.pages || []).length, assets: assets.length,
    migrate: 0, rewrite: 0, review: 0, archive: 0,
    broken: (enrich.brokenLinks || []).length, lowres: lowResSrcs.size,
    undated: assets.filter(a => a.timeSensitive && a.migrationStatus === 'Rewrite' && /undated/.test(a.reviewNotes)).length,
    stale: assets.filter(a => a.migrationStatus === 'Archive').length,
    pastEvents: assets.filter(a => /past-dated event/.test(a.reviewNotes)).length,
    staleMonths: ctx.staleMonths,
  };
  for (const a of assets) counters[a.migrationStatus.toLowerCase()]++;
  const navCount = assets.filter(a => a.sourceKind === 'quicklinks' || a.assetType === 'Link').length;

  const wb = new ExcelJS.Workbook();
  wb.creator = 'OpenClaw SP Pipeline'; wb.created = new Date(ctx.today);

  // ---------- Sheet 1: Content Tracker ----------
  const ws1 = wb.addWorksheet('Content Tracker');
  ws1.columns = [18,32,20,16,28,48,16,30,28,18].map(width => ({ width }));
  const title1 = ws1.addRow([`${siteName} — Classic → Modern Content Tracker`]); ws1.mergeCells('A1:J1');
  paint(title1.getCell(1), COLORS.titleDark, true, 12);
  const sub1 = ws1.addRow([`Source: ${siteUrl}  |  Audited: ${ctx.today}  |  Pages: ${counters.pages}  |  Assets: ${counters.assets}  |  Status is advisory — build migrates verbatim`]);
  ws1.mergeCells('A2:J2'); paint(sub1.getCell(1), COLORS.headerMid, false, 10);
  ws1.addRow([]);
  const hdr1 = ws1.addRow(['Page','Page URL','Section','Asset Type','Description','Content','Image Ref','Hyperlink','Review Notes','Migration Status']);
  hdr1.eachCell(c => paint(c, COLORS.headerMid, true, 10));

  const byPage = {};
  for (const a of assets) (byPage[a.pageName] ||= []).push(a);
  let ri = 0;
  for (const [pg, list] of Object.entries(byPage)) {
    const div = ws1.addRow([`  ${pg}`]); ws1.mergeCells(`A${div.number}:J${div.number}`);
    div.eachCell(c => paint(c, COLORS.headerMid, true, 10));
    for (const a of list) {
      const row = ws1.addRow([a.pageName, a.pageUrl, a.section, a.assetType, a.assetDescription || '',
        a.assetContent || '', a.imageRef || '', a.hyperlink || '', a.reviewNotes || '', a.migrationStatus]);
      const bg = ri % 2 === 0 ? COLORS.white : COLORS.lightGrey;
      row.eachCell(c => { c.fill = fill(bg); c.font = { name:'Calibri', size:10 }; c.alignment = { vertical:'top', wrapText:true }; });
      const sc = row.getCell(10); sc.fill = fill(statusColor(a.migrationStatus)); sc.font = { bold:true, name:'Calibri', size:10 };
      ri++;
    }
  }

  // ---------- Sheet 2: Image Index ----------
  const ws2 = wb.addWorksheet('Image Index');
  ws2.columns = [18,30,22,20,28,16,20].map(width => ({ width }));
  const title2 = ws2.addRow([`${siteName} — Image Asset Index`]); ws2.mergeCells('A1:G1');
  paint(title2.getCell(1), COLORS.titleDark, true, 12);
  const sub2 = ws2.addRow(['Images from the source site. Low-resolution assets are flagged for hi-res replacement before migration.']);
  ws2.mergeCells('A2:G2'); paint(sub2.getCell(1), COLORS.headerMid, false, 10);
  ws2.addRow([]);
  const hdr2 = ws2.addRow(['Reference ID','File Name','Page Found On','Section','Usage','Resolution','Migration Action']);
  hdr2.eachCell(c => paint(c, COLORS.headerMid, true, 10));
  images.forEach((img, i) => {
    const d = (enrich.imageDims || {})[img.src];
    const w = d ? (d.w || 0) : 0;
    const resNote = w > 0 ? (w < LOWRES_MIN_PX ? `${w}px — LOW` : `${w}px — OK`) : 'unknown';
    const action = w > 0 && w < LOWRES_MIN_PX ? 'Replace with hi-res' : 'Migrate';
    const row = ws2.addRow([img.ref, img.filename, img.pageName, img.section, img.alt || 'Image', resNote, action]);
    const bg = i % 2 === 0 ? COLORS.lightGrey : COLORS.white;
    row.eachCell(c => { c.fill = fill(bg); c.font = { name:'Calibri', size:10 }; });
    const ac = row.getCell(7); ac.fill = fill(action === 'Migrate' ? COLORS.migrateGreen : COLORS.archiveRed); ac.font = { bold:true, name:'Calibri', size:10 };
  });

  // ---------- Sheet 3: Migration Summary ----------
  const ws3 = wb.addWorksheet('Migration Summary');
  ws3.columns = [28,10,4,18,52].map(width => ({ width }));
  const title3 = ws3.addRow([`${siteName} — Migration Readiness`]); ws3.mergeCells('A1:E1');
  paint(title3.getCell(1), COLORS.titleDark, true, 12);
  const sub3 = ws3.addRow(['Auto-derived from the Content Tracker · Classic → Modern SharePoint conversion']);
  ws3.mergeCells('A2:E2'); paint(sub3.getCell(1), COLORS.headerMid, false, 10);
  ws3.addRow([]);
  const hdr3 = ws3.addRow(['AUDIT SUMMARY', null, null, 'DERIVED PAIN POINTS', null]);
  hdr3.getCell(1).font = { bold:true, size:10 }; hdr3.getCell(4).font = { bold:true, size:10 };
  const pains = derivePainPoints(counters, navCount);
  const summary = [
    ['Total pages', counters.pages], ['Total assets', counters.assets],
    ['Ready to migrate', counters.migrate], ['Needs rewrite', counters.rewrite],
    ['Stale / archive', counters.archive], ['Under review', counters.review],
    ['Broken links', counters.broken], ['Low-res images', counters.lowres],
  ];
  const valBg = [COLORS.lightGrey, COLORS.lightGrey, COLORS.migrateGreen, COLORS.rewriteAmber, COLORS.archiveRed, COLORS.reviewBlue, COLORS.archiveRed, COLORS.rewriteAmber];
  const rows3 = Math.max(summary.length, pains.length);
  for (let i = 0; i < rows3; i++) {
    const s = summary[i], p = pains[i];
    const row = ws3.addRow([ s ? s[0] : null, s ? s[1] : null, null, p ? p[0] : null, p ? p[1] : null ]);
    if (s) { row.getCell(1).fill = fill(COLORS.lightGrey); row.getCell(2).fill = fill(valBg[i]); row.getCell(2).font = { bold:true, size:10 }; }
    if (p) { row.getCell(4).fill = fill(COLORS.reviewBlue); row.getCell(4).font = { bold:true, size:10 }; row.getCell(5).alignment = { wrapText:true }; }
  }

  return { workbook: wb, counters, assets, images, pains };
}

function fill(argb) { return { type:'pattern', pattern:'solid', fgColor:{ argb } }; }
function paint(cell, bg, bold, size) { cell.fill = fill(bg); cell.font = { bold:!!bold, color:{ argb:COLORS.whiteText }, name:'Calibri', size:size||10 }; }

async function writeTracker(spExpect, outPath, opts) {
  const { workbook, counters } = await buildWorkbook(spExpect, opts);
  await workbook.xlsx.writeFile(outPath);
  return counters;
}

module.exports = { buildWorkbook, writeTracker, normalizeAssets, applyRuleset, parseDates, derivePainPoints };

// ---- CLI ----
if (require.main === module) {
  const a = process.argv.slice(2);
  const pos = a.filter(x => !x.startsWith('--'));
  const flag = (n, d) => { const i = a.indexOf(`--${n}`); return i >= 0 ? a[i + 1] : d; };
  const [inPath, outPath] = pos;
  if (!inPath || !outPath) { console.error('usage: node sp-tracker.js <sp-expect.json> <out.xlsx> [--site NAME] [--url URL] [--enrich enrich.json] [--today YYYY-MM-DD] [--stale-months N]'); process.exit(2); }
  const spExpect = JSON.parse(fs.readFileSync(inPath, 'utf8'));
  const enrichPath = flag('enrich'); const enrich = enrichPath && fs.existsSync(enrichPath) ? JSON.parse(fs.readFileSync(enrichPath, 'utf8')) : {};
  writeTracker(spExpect, outPath, {
    siteName: flag('site'), siteUrl: flag('url'), enrich,
    today: flag('today'), staleMonths: flag('stale-months') ? +flag('stale-months') : 12,
  }).then(c => console.log(JSON.stringify({ ok:true, out:outPath, counters:c }))).catch(e => { console.error(e); process.exit(1); });
}
