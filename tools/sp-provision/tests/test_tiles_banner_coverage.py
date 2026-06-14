#!/usr/bin/env python3
"""Unit tests for SP classic->modern HomeTiles / banner coverage (JOB0024-109, sub-task 3).

Covers three seams:
  Sub-task 3 - canvas_compose.tiles_from_blocks(): a classic HomeTiles block (image +
        label + link tiles) is mapped to a NATIVE Quick Links web part; every tile
        label + url round-trips verbatim (copy_coverage >= threshold).
  Sub-task 3 - canvas_compose.banner_from_blocks(): a classic banner block (image +
        title + tagline + link) is mapped to a NATIVE Hero web part; title + image +
        tagline survive verbatim.
  Triage     - cc_sp_triage.classify(): buildableTypes=['tiles']/['banner'] flips those
        flagged pages flag->buildable (handler now registered in HANDLED_TYPES), while a
        CAROUSEL page STAYS flagged 'carousel-spfx' even when whitelisted — SPFx-blocked
        (flag-don't-fake: its modern equivalent needs missing SPFx source + a broken
        toolchain, so it is NOT in HANDLED_TYPES and can never be downgraded here).

Repo-only, synthetic fixtures — no SharePoint, no network, no live capture, no SPFx
authoring. Run: python3 -m unittest discover -s tests -v   (from tools/sp-provision)
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPDIR = os.path.dirname(HERE)
sys.path.insert(0, SPDIR)

import cc_sp_triage as triage          # noqa: E402
import canvas_compose as compose       # noqa: E402

COV_THRESHOLD = 0.9  # same fidelity bar the completeness gate uses for article pages


# --------------------------------------------------------------------------- #
# Synthetic source blocks (what the audit WOULD emit for a HomeTiles grid and a
# classic banner). HomeTiles = image+label+link tiles; banner = one big image +
# title + tagline + link.
# --------------------------------------------------------------------------- #
FIX_TILES = {
    "kind": "tiles",
    "heading": "Department Hubs",
    "items": [
        {"title": "Human Resources", "url": "/sites/Acme/SitePages/HR.aspx"},
        {"title": "Information Technology", "url": "https://it.example.com/acme"},
        {"title": "Finance and Payroll", "url": "/sites/Acme/SitePages/Finance.aspx"},
        {"title": "Health and Safety", "url": "/sites/Acme/SitePages/Safety.aspx"},
    ],
    "text": "",
    "html": "",
    "images": [],
}

# A tiles block expressed as raw HomeTiles markup (image + label + link anchors).
FIX_TILES_HTML = {
    "kind": "tiles",
    "heading": "Quick Access",
    "items": [],
    "text": "",
    "html": ('<div class="HomeTiles">'
             '<a href="/sites/Acme/Travel.aspx"><img src="travel.png"/>Travel Booking</a>'
             '<a href="/sites/Acme/Expenses.aspx"><img src="exp.png"/>Expense Claims</a>'
             '</div>'),
    "images": [],
}

FIX_BANNER = {
    "kind": "banner",
    "heading": "Welcome to Acme One",
    "text": "Connecting every plant, depot and office across the group.",
    "url": "/sites/Acme/About.aspx",
    "html": "",
    "images": [{"src": "/sites/Acme/PublishingImages/banner-hero.jpg", "alt": "Acme campus"}],
}

# image-map: source-src -> migrated build URL (banner background).
IMAGE_MAP = {"/sites/Acme/PublishingImages/banner-hero.jpg":
             "https://codeandcanvas.sharepoint.com/sites/CCBuild/Migrated/banner-hero.jpg"}


def _fold_wp(wp):
    """Flatten a web part to its searchable copy. Text web parts -> innerHtml; native
    web parts (Hero/Quick Links/Image) carry their copy in serverProcessedContent, so
    fold the whole web part to JSON — exactly how cc-verify-sp's fidelity gate folds
    non-text web parts (see canvas_compose module header)."""
    if wp.get("innerHtml") is not None:
        return wp["innerHtml"]
    return json.dumps(wp, ensure_ascii=False)


def _compose_blob(content, image_map=None, title="Test Page"):
    """Compose content[] through the SAME verbatim composer the build uses, then fold
    every web part (text innerHtml + native serverProcessedContent) for coverage."""
    page_spec = {"title": title, "content": content}
    canvas = compose.build_canvas_from_content(
        page_spec, image_map=image_map or {}, site_id="sid")
    assert canvas is not None, "composer returned None for non-empty content"
    blob = [title]
    for sec in canvas["horizontalSections"]:
        for col in sec.get("columns", []):
            for wp in col.get("webparts", []):
                blob.append(_fold_wp(wp))
    return "\n".join(blob)


class TestTilesMapping(unittest.TestCase):
    def test_tiles_from_items_quicklinks(self):
        wp = compose.tiles_from_blocks(FIX_TILES)
        self.assertIsNotNone(wp)
        self.assertEqual(wp["webPartType"], compose.QUICKLINKS_WEBPART_GUID)
        blob = json.dumps(wp, ensure_ascii=False)
        # every tile label + url verbatim in the Quick Links serverProcessedContent
        for it in FIX_TILES["items"]:
            self.assertIn(it["title"], blob)
            self.assertIn(it["url"], blob)

    def test_tiles_from_html_anchors(self):
        wp = compose.tiles_from_blocks(FIX_TILES_HTML)
        self.assertIsNotNone(wp)
        blob = json.dumps(wp, ensure_ascii=False)
        self.assertIn("Travel Booking", blob)
        self.assertIn("/sites/Acme/Travel.aspx", blob)
        self.assertIn("Expense Claims", blob)

    def test_empty_tiles_none(self):
        self.assertIsNone(compose.tiles_from_blocks(
            {"kind": "tiles", "items": [], "html": "", "heading": ""}))

    def test_tiles_coverage_after_compose(self):
        source_text = " ".join("%s %s" % (it["title"], it["url"])
                               for it in FIX_TILES["items"])
        blob = _compose_blob([FIX_TILES])
        cov, missing, total = compose.copy_coverage(source_text, blob)
        self.assertGreaterEqual(
            cov, COV_THRESHOLD,
            "tiles coverage %.3f < %.2f; missing=%s" % (cov, COV_THRESHOLD, missing[:20]))
        # and every label/url is actually on the composed page
        for it in FIX_TILES["items"]:
            self.assertIn(it["title"], blob)
            self.assertIn(it["url"], blob)

    def test_tiles_overflow_not_dropped(self):
        # >8 tiles: Quick Links caps at 8, the rest must survive verbatim as a text wp.
        many = {"kind": "tiles", "heading": "Big Grid", "html": "", "images": [],
                "items": [{"title": "Hub %d" % i, "url": "/h/%d" % i}
                          for i in range(11)]}
        blob = _compose_blob([many])
        for i in range(11):
            self.assertIn("Hub %d" % i, blob)
            self.assertIn("/h/%d" % i, blob)


class TestBannerMapping(unittest.TestCase):
    def test_banner_from_blocks_hero(self):
        wp = compose.banner_from_blocks(FIX_BANNER, IMAGE_MAP, site_id="sid")
        self.assertEqual(wp["webPartType"], compose.HERO_WEBPART_GUID)
        blob = json.dumps(wp, ensure_ascii=False)
        # title + tagline verbatim; banner image becomes the hero background (migrated URL)
        self.assertIn("Welcome to Acme One", blob)
        self.assertIn("Connecting every plant", blob)
        self.assertIn(IMAGE_MAP["/sites/Acme/PublishingImages/banner-hero.jpg"], blob)

    def test_banner_title_and_image_after_compose(self):
        blob = _compose_blob([FIX_BANNER], image_map=IMAGE_MAP)
        self.assertIn("Welcome to Acme One", blob)
        self.assertIn(IMAGE_MAP["/sites/Acme/PublishingImages/banner-hero.jpg"], blob)

    def test_banner_coverage_after_compose(self):
        source_text = "%s %s" % (FIX_BANNER["heading"], FIX_BANNER["text"])
        blob = _compose_blob([FIX_BANNER], image_map=IMAGE_MAP)
        cov, missing, total = compose.copy_coverage(source_text, blob)
        self.assertGreaterEqual(
            cov, COV_THRESHOLD,
            "banner coverage %.3f < %.2f; missing=%s" % (cov, COV_THRESHOLD, missing[:20]))


class TestTriageTilesBannerCarousel(unittest.TestCase):
    """tiles/banner flip flag->buildable under buildableTypes; carousel STAYS flagged
    'carousel-spfx' even when whitelisted (SPFx-blocked, NOT in HANDLED_TYPES)."""

    def _page(self, **sig):
        base = {
            "file": "Home.aspx", "title": "Home", "lib": "Site Pages",
            "modified": "2026-05-01T00:00:00Z", "bytes": 5000, "webPartCount": 1,
            "isPublishing": False, "hasListWebpart": True,
            "hasTiles": False, "hasCarousel": False, "hasBanner": False,
        }
        base.update(sig)
        # Home.aspx is a SYSTEM page; use a distinct file so 'keep' is True.
        base["file"] = sig.get("file", "Landing.aspx")
        return [base]

    def _classify(self, page, **kw):
        return triage.classify(page, 18, 6,
                               triage.datetime.now(triage.timezone.utc), **kw)

    def test_tiles_flagged_then_flips(self):
        page = self._page(hasTiles=True)
        r0 = self._classify(page)[0]
        self.assertEqual(r0["flagReason"], "hometiles")
        self.assertFalse(r0["buildable"])
        r1 = self._classify(page, buildable_types=["tiles"])[0]
        self.assertIsNone(r1["flagReason"])
        self.assertTrue(r1["buildable"])

    def test_banner_flagged_then_flips(self):
        page = self._page(hasBanner=True, hasListWebpart=False)
        r0 = self._classify(page)[0]
        self.assertEqual(r0["flagReason"], "banner")
        self.assertFalse(r0["buildable"])
        r1 = self._classify(page, buildable_types=["banner"])[0]
        self.assertIsNone(r1["flagReason"])
        self.assertTrue(r1["buildable"])

    def test_carousel_stays_flagged_spfx(self):
        page = self._page(hasCarousel=True)
        r0 = self._classify(page)[0]
        self.assertEqual(r0["flagReason"], "carousel-spfx")
        self.assertFalse(r0["buildable"])
        # even if the operator (mistakenly) whitelists 'carousel', it CANNOT flip —
        # carousel is NOT in HANDLED_TYPES (SPFx-blocked).
        r1 = self._classify(page, buildable_types=["carousel"])[0]
        self.assertEqual(r1["flagReason"], "carousel-spfx")
        self.assertFalse(r1["buildable"])

    def test_carousel_takes_precedence_over_generic_list(self):
        # a carousel page also trips hasListWebpart, but must get the SPECIFIC reason,
        # not the generic 'list-driven'.
        page = self._page(hasCarousel=True, hasListWebpart=True)
        r = self._classify(page)[0]
        self.assertEqual(r["flagReason"], "carousel-spfx")

    def test_handlers_registered_carousel_absent(self):
        self.assertIn("tiles", triage.HANDLED_TYPES)
        self.assertIn("banner", triage.HANDLED_TYPES)
        self.assertNotIn("carousel", triage.HANDLED_TYPES)

    def test_generic_list_still_works(self):
        # ST2 regression: a plain list page (no tiles/carousel/banner) keeps the
        # 'list-driven' flag and flips under buildableTypes=['list'].
        page = self._page(hasListWebpart=True)
        r0 = self._classify(page)[0]
        self.assertEqual(r0["flagReason"], "list-driven")
        r1 = self._classify(page, buildable_types=["list"])[0]
        self.assertIsNone(r1["flagReason"])
        self.assertTrue(r1["buildable"])


if __name__ == "__main__":
    unittest.main()
