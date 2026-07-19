// Unit test for the triage flag-detection heuristics (JOB0024-108 Phase F).
// Validates pageSignals() against REPRESENTATIVE REAL SharePoint page bodies, so
// the publishing/list/heavy flag paths are deterministically proven even though
// those page types can't be seeded live in modern SPO.
import { pageSignals } from "./sp-complexity.mjs";
import assert from "node:assert";

let pass = 0;
const t = (name, got, expect) => {
  assert.deepStrictEqual(got, expect, `${name}: got ${JSON.stringify(got)}`);
  console.log("  ok:", name);
  pass++;
};

// 1) Modern Site Page CanvasContent1 — two web parts, no list
const modern = `[{"position":{"zoneIndex":1,"sectionIndex":1},"webPartId":"d1d91016-032f-456d-98a4-721247c305e8","webPartData":{"dataVersion":"1.0","properties":{"imageSourceType":2}}},{"webPartId":"6f96a85e","webPartData":{"properties":{"title":"Text"}}}]`;
t("modern: 2 web parts", pageSignals(modern, "Site Pages", null),
  { bytes: modern.length, webPartCount: 2, isPublishing: false, hasListWebpart: false,
    hasCarousel: false, hasTiles: false });

// 2) Classic WikiField with a web part zone
const wiki = `<div class="ms-rte-layoutszone-inner"><div class="ms-rte-wpbox"><div class="ms-rtestate-notify ms-rtestate-read 9b...">WebPartZone content</div></div></div>`;
const w2 = pageSignals(wiki, "Site Pages", null);
assert.ok(w2.webPartCount >= 1 && !w2.isPublishing && !w2.hasListWebpart, "wiki webpart");
console.log("  ok: classic WikiField web part (count " + w2.webPartCount + ")"); pass++;

// 3) Publishing page — PublishingPageContent body in the 'Pages' library
const pub = `<div class="article"><p>Innovation is the key to success across our brands.</p></div>`;
t("publishing (lib=Pages)", pageSignals(pub, "Pages", pub),
  { bytes: pub.length, webPartCount: 0, isPublishing: true, hasListWebpart: false,
    hasCarousel: false, hasTiles: false });

// 4) Classic list view web part (XsltListViewWebPart inside a zone)
const listClassic = `<WebPartPages:XsltListViewWebPart runat="server" ListUrl="/Lists/Announcements"><WebPartZone/></WebPartPages:XsltListViewWebPart>`;
const l4 = pageSignals(listClassic, "Site Pages", null);
assert.ok(l4.hasListWebpart === true, "XsltListViewWebPart -> hasListWebpart");
console.log("  ok: classic XsltListViewWebPart flagged list-driven"); pass++;

// 5) Modern list web part (CanvasContent1 referencing a listId)
const listModern = `[{"webPartId":"f92bf067-bc19-489e-a556-7fe95f508720","webPartData":{"properties":{"isDocumentLibrary":false,"selectedListId":"a1b2c3d4-1111-2222-3333-444455556666"}}}]`;
const l5 = pageSignals(listModern, "Site Pages", null);
assert.ok(l5.hasListWebpart === true && l5.webPartCount === 1, "modern list webpart");
console.log("  ok: modern list web part (listId) flagged list-driven"); pass++;

// 6) Plain wiki text page — nothing special
const plain = `<div><p>Just some ordinary paragraph text with no web parts.</p></div>`;
t("plain text page", pageSignals(plain, "Site Pages", null),
  { bytes: plain.length, webPartCount: 0, isPublishing: false, hasListWebpart: false,
    hasCarousel: false, hasTiles: false });

// 7) Empty body
t("empty body", pageSignals("", "Site Pages", null),
  { bytes: 0, webPartCount: 0, isPublishing: false, hasListWebpart: false,
    hasCarousel: false, hasTiles: false });

// 8) HomeTiles web part (image+label+link tiles) — DISTINCT hasTiles signal, AND
//    still flips the generic hasListWebpart so the ST2 list path keeps flagging it
//    until the operator whitelists "tiles". Carousel must stay false here.
const tiles = `<div class="HomeTiles"><a href="/HR"><img src="hr.png"/>HR</a><a href="/IT"><img src="it.png"/>IT</a></div>`;
const t8 = pageSignals(tiles, "Site Pages", null);
assert.ok(t8.hasTiles === true && t8.hasCarousel === false && t8.hasListWebpart === true,
  "HomeTiles -> hasTiles + hasListWebpart, NOT carousel");
console.log("  ok: HomeTiles -> distinct hasTiles (still hasListWebpart)"); pass++;

// 9) CarouselWebPart (SPFx-blocked) — DISTINCT hasCarousel signal, NOT hasTiles.
const carousel = `<WebPartPages:CarouselWebPart runat="server"><Slides/></WebPartPages:CarouselWebPart>`;
const t9 = pageSignals(carousel, "Site Pages", null);
assert.ok(t9.hasCarousel === true && t9.hasTiles === false && t9.hasListWebpart === true,
  "Carousel -> hasCarousel + hasListWebpart, NOT tiles");
console.log("  ok: CarouselWebPart -> distinct hasCarousel (SPFx-blocked)"); pass++;

// 10) Generic XsltListView is list-driven but NEITHER tiles NOR carousel.
const t10 = pageSignals(listClassic, "Site Pages", null);
assert.ok(t10.hasListWebpart === true && t10.hasTiles === false && t10.hasCarousel === false,
  "generic list -> hasListWebpart only, no tiles/carousel");
console.log("  ok: generic list web part -> not tiles, not carousel"); pass++;

console.log(`\nflag-detection: ${pass}/10 PASS`);
process.exit(0);
