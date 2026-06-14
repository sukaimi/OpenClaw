// Page complexity signals for large-site triage (JOB0024-108).
// Shared by cc-sp-capture's inventory pass AND its unit test so the detection
// heuristics cannot drift. Heuristic by design — used to FLAG pages for operator
// review (flag-don't-fake), not to perfectly classify.
export function pageSignals(body, lib, hasPublishingField) {
  const b = body || "";
  const wpHits = b.match(/webPartData|data-sp-webpart|ms-rte-wpbox|WebPartZone|<webPart\b/gi);
  return {
    bytes: b.length,
    webPartCount: wpHits ? wpHits.length : 0,
    isPublishing: lib === "Pages" || !!hasPublishingField,
    hasListWebpart: /XsltListViewWebPart|ListViewWebPart|ContentByQuery|CarouselWebPart|"isListLayout"|listId/i.test(b),
  };
}
