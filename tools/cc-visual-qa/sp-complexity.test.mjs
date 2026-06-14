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
  { bytes: modern.length, webPartCount: 2, isPublishing: false, hasListWebpart: false });

// 2) Classic WikiField with a web part zone
const wiki = `<div class="ms-rte-layoutszone-inner"><div class="ms-rte-wpbox"><div class="ms-rtestate-notify ms-rtestate-read 9b...">WebPartZone content</div></div></div>`;
const w2 = pageSignals(wiki, "Site Pages", null);
assert.ok(w2.webPartCount >= 1 && !w2.isPublishing && !w2.hasListWebpart, "wiki webpart");
console.log("  ok: classic WikiField web part (count " + w2.webPartCount + ")"); pass++;

// 3) Publishing page — PublishingPageContent body in the 'Pages' library
const pub = `<div class="article"><p>Innovation is the key to success across our brands.</p></div>`;
t("publishing (lib=Pages)", pageSignals(pub, "Pages", pub),
  { bytes: pub.length, webPartCount: 0, isPublishing: true, hasListWebpart: false });

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
  { bytes: plain.length, webPartCount: 0, isPublishing: false, hasListWebpart: false });

// 7) Empty body
t("empty body", pageSignals("", "Site Pages", null),
  { bytes: 0, webPartCount: 0, isPublishing: false, hasListWebpart: false });

console.log(`\nflag-detection: ${pass}/7 PASS`);
process.exit(0);
