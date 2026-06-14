#!/usr/bin/env node
/**
 * selftest.js — proves the ruleset + 3-sheet workbook end-to-end with synthetic input.
 * No network, no real SP. Exit non-zero on any failed assertion.
 */
const assert = require('assert');
const fs = require('fs');
const ExcelJS = require('exceljs');
const { buildWorkbook, normalizeAssets, applyRuleset, parseDates } = require('./sp-tracker.js');

const TODAY = '2026-06-12'; // fixed reference so freshness is deterministic

// Synthetic sp-expect.json mirroring the real schema (kinds/headings/text/html/images/items)
const spExpect = {
  sourceUrl: 'https://example.sharepoint.com/sites/DemoClassic',
  pages: [{
    name: 'Home.aspx', title: 'Home',
    content: [
      { kind: 'intro', heading: 'Acme Corp', text: 'Acme Corp — Good Stuff — Last updated: 15 January 2026',
        html: '<h1>Acme Corp</h1>', images: [{ src: '/sites/DemoClassic/SiteAssets/logo.png', filename: 'logo.png', alt: 'Logo' }] },
      { kind: 'welcome', heading: 'Welcome', text: 'Welcome to Acme.', html: '<p>Welcome to Acme.</p>', images: [] },
      { kind: 'news', heading: 'Company News', text: 'Fresh item dated 20 May 2026.',
        html: '<a href="https://example.com/live">Live</a> <a href="https://example.com/dead">Dead</a>', images: [] },
      { kind: 'news', heading: 'Old News', text: 'An item from 03 February 2024.', html: '', images: [] },
      { kind: 'news', heading: 'Mystery News', text: 'No date on this announcement at all.', html: '', images: [] },
      { kind: 'events', heading: 'Upcoming Events', text: 'Town Hall on 03 April 2026.', html: '', images: [] },
      { kind: 'documents', heading: 'Key Documents', text: 'Handbook',
        html: '<a href="https://example.com/handbook.pdf">Handbook v4.2</a>', images: [] },
      { kind: 'brands', heading: '', text: '', html: '', images: [] }, // empty/garbled
    ],
  }],
};

// Synthetic enrichment: one broken link, one tiny (low-res) image
const enrich = {
  brokenLinks: [{ url: 'https://example.com/dead', status: '404' }],
  imageDims: { '/sites/DemoClassic/SiteAssets/logo.png': { w: 120, h: 60 } }, // < 400px → low-res
};

function find(assets, pred) { return assets.find(pred); }

(async () => {
  // --- date parsing ---
  assert.equal(parseDates('Last updated: 15 January 2026').length, 1, 'parse "15 January 2026"');
  assert.equal(parseDates('dated 20 May 2026 and 03 February 2024').length, 2, 'parse two dates');
  assert.equal(parseDates('no date here').length, 0, 'no false date');

  // --- normalize ---
  const { assets, images } = normalizeAssets(spExpect, { siteUrl: spExpect.sourceUrl });
  assert.ok(assets.length > 8, `assets exploded (${assets.length})`);
  assert.equal(images.length, 1, 'one image extracted');
  assert.ok(find(assets, a => a.assetType === 'Heading'), 'has Heading asset');
  assert.ok(find(assets, a => a.assetType === 'Document'), 'pdf href → Document');
  assert.ok(find(assets, a => a.assetType === 'Link'), 'plain href → Link');
  assert.ok(find(assets, a => a.assetType === 'Image'), 'has Image asset');

  // --- ruleset ---
  applyRuleset(assets, images, enrich, { today: TODAY, staleMonths: 12 });
  const freshNews = find(assets, a => a.section === 'Company News' && a.assetType === 'Text Block');
  const oldNews = find(assets, a => a.section === 'Old News' && a.assetType === 'Text Block');
  const mystery = find(assets, a => a.section === 'Mystery News' && a.assetType === 'Text Block');
  const event = find(assets, a => a.section === 'Upcoming Events' && a.assetType === 'Text Block');
  const deadLink = find(assets, a => a.hyperlink === 'https://example.com/dead');
  const liveLink = find(assets, a => a.hyperlink === 'https://example.com/live');
  const image = find(assets, a => a.assetType === 'Image');
  const welcome = find(assets, a => a.section === 'Welcome' && a.assetType === 'Text Block');
  const empty = find(assets, a => a.sourceKind === 'brands' && a.assetType === 'Heading');

  assert.equal(freshNews.migrationStatus, 'Migrate', `fresh news → Migrate (got ${freshNews.migrationStatus})`);
  assert.equal(oldNews.migrationStatus, 'Archive', `2024 news → Archive (got ${oldNews.migrationStatus})`);
  assert.equal(mystery.migrationStatus, 'Rewrite', `undated news → Rewrite (got ${mystery.migrationStatus})`);
  assert.equal(event.migrationStatus, 'Rewrite', `past-dated event (Apr<Jun) → Rewrite (got ${event.migrationStatus})`);
  assert.equal(deadLink.migrationStatus, 'Review', `broken link → Review (got ${deadLink.migrationStatus})`);
  assert.ok(/BROKEN LINK/.test(deadLink.reviewNotes), 'broken link note present');
  assert.equal(liveLink.migrationStatus, 'Migrate', `live link → Migrate (got ${liveLink.migrationStatus})`);
  assert.equal(image.migrationStatus, 'Review', `low-res image → Review (got ${image.migrationStatus})`);
  assert.ok(/low-res/.test(image.reviewNotes), 'low-res note present');
  assert.equal(welcome.migrationStatus, 'Migrate', 'non-time-sensitive intact → Migrate');
  assert.ok(empty === undefined || empty.migrationStatus === 'Review', 'empty heading not present or Review');

  // --- workbook: exactly the 3 required sheets, populated ---
  const { workbook, counters, pains } = await buildWorkbook(spExpect, { siteName: 'Acme', siteUrl: spExpect.sourceUrl, enrich, today: TODAY });
  const out = require('path').join(__dirname, '_selftest.xlsx');
  await workbook.xlsx.writeFile(out);
  const rb = new ExcelJS.Workbook(); await rb.xlsx.readFile(out);
  const names = rb.worksheets.map(w => w.name);
  assert.deepEqual(names, ['Content Tracker', 'Image Index', 'Migration Summary'], `3 sheets in order (got ${names})`);
  assert.ok(rb.getWorksheet('Content Tracker').rowCount > 10, 'tracker populated');
  assert.equal(rb.getWorksheet('Image Index').rowCount >= 5, true, 'image index populated');
  assert.ok(counters.review >= 2 && counters.archive >= 1 && counters.rewrite >= 2, `counters sane: ${JSON.stringify(counters)}`);
  assert.ok(pains.length >= 3, `derived pain points present (${pains.length})`);
  fs.unlinkSync(out);

  console.log('✅ ALL PASS');
  console.log('   counters:', JSON.stringify(counters));
  console.log('   pains:', pains.map(p => p[0]).join(', '));
})().catch(e => { console.error('❌ FAIL:', e.message); process.exit(1); });
