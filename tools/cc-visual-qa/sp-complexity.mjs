// Page complexity signals for large-site triage (JOB0024-108).
// Shared by cc-sp-capture's inventory pass AND its unit test so the detection
// heuristics cannot drift. Heuristic by design — used to FLAG pages for operator
// review (flag-don't-fake), not to perfectly classify.
export function pageSignals(body, lib, hasPublishingField) {
  const b = body || "";
  const wpHits = b.match(/webPartData|data-sp-webpart|ms-rte-wpbox|WebPartZone|<webPart\b/gi);
  // Split out the carousel + tiles families from the generic list signal so triage
  // can route them DISTINCTLY (JOB0024-109 sub-task 3): HomeTiles/banner have native
  // modern handlers (flag->buildable), Carousel is SPFx-blocked (stays flagged with
  // its own reason). hasListWebpart stays TRUE for any of them so the prior list path
  // (ST2) still flags the page if the operator hasn't whitelisted the specific family.
  const hasCarousel = /CarouselWebPart/i.test(b);
  const hasTiles = /HomeTiles|TilesWebPart|PromotedLinks|"tilesLayout"/i.test(b);
  return {
    bytes: b.length,
    webPartCount: wpHits ? wpHits.length : 0,
    isPublishing: lib === "Pages" || !!hasPublishingField,
    hasListWebpart: /XsltListViewWebPart|ListViewWebPart|ContentByQuery|CarouselWebPart|HomeTiles|TilesWebPart|PromotedLinks|"isListLayout"|listId/i.test(b),
    hasCarousel,
    hasTiles,
  };
}
