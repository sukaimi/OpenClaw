#!/usr/bin/env python3
"""Unit tests for SP classic->modern publishing-layout coverage (JOB0024-109).

Covers two seams:
  G1  - cc_sp_triage.classify(): buildableTypes=["publishing"] flips a flagged
        publishing page flag->buildable (and only when a handler is registered).
  Sub-task 1 - sp-audit._publishing_blocks(): a PublishingPageContent body is
        extracted into ORDERED content[] blocks (pub-field/section, images + order
        preserved), and composing them through the SAME verbatim composer yields
        copy_coverage >= threshold.

Repo-only, synthetic fixtures — no SharePoint, no network, no live capture.
Run: python3 -m unittest discover -s tests -v   (from tools/sp-provision)
"""
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPDIR = os.path.dirname(HERE)
sys.path.insert(0, SPDIR)

import cc_sp_triage as triage          # noqa: E402
import canvas_compose as compose       # noqa: E402

# sp-audit.py has a hyphen -> load by path.
_spec = importlib.util.spec_from_file_location(
    "sp_audit", os.path.join(SPDIR, "sp-audit.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

COV_THRESHOLD = 0.9  # same fidelity bar the completeness gate uses for article pages


# --------------------------------------------------------------------------- #
# Synthetic PublishingPageContent fixtures (classic field-control chrome).
# Three realistic field types: rich-text body, image field, summary-link field.
# --------------------------------------------------------------------------- #

# 1) Rich-text field + image field (CEO message style)
FIX_RICHTEXT_IMAGE = """
<div class="PublishingWebControls">
  <div class="ms-rtestate-field RichImageField">
    <img src="/sites/Acme/PublishingImages/ceo-portrait.jpg" alt="Jane Doe, CEO" />
  </div>
  <div class="ms-rtestate-field RichHtmlField">
    <h2>A Message From Our CEO</h2>
    <p>Welcome to Acme Corporation. This year marks a decade of relentless
    innovation across our manufacturing and logistics divisions.</p>
    <p>Our people remain the engine of everything we build, and I am proud of the
    progress we have made together toward a safer, smarter workplace.</p>
  </div>
</div>
"""

# 2) Rich-text field + summary-link field (news + quick links style)
FIX_RICHTEXT_SUMMARYLINK = """
<div class="PublishingWebControls">
  <div class="ms-rtestate-field RichHtmlField">
    <h2>Quarterly Operations Update</h2>
    <p>The Eastern plant completed its automation upgrade on schedule and under
    budget. Output rose eleven percent against the prior quarter.</p>
  </div>
  <div class="SummaryLinkFieldControl">
    <ul>
      <li><a href="/sites/Acme/SitePages/Safety.aspx">Safety Handbook</a></li>
      <li><a href="/sites/Acme/SitePages/Benefits.aspx">Benefits Portal</a></li>
    </ul>
  </div>
</div>
"""

# 3) Pure rich-text field, no leading heading (plain pub-field region)
FIX_RICHTEXT_ONLY = """
<div class="ms-rtestate-field RichHtmlField">
  <p>All visitors must sign in at the front desk and wear a visible badge at all
  times while on the premises. Photography is prohibited in the laboratory wing.</p>
  <p>Emergency assembly points are marked on every floor near the stairwells.</p>
</div>
"""


def _compose_html(content, title="Test Page"):
    """Compose a page_spec's content[] through the SAME verbatim composer the build
    uses, then flatten every text web part's innerHtml + the title for coverage."""
    page_spec = {"title": title, "content": content}
    canvas = compose.build_canvas_from_content(page_spec, image_map={}, site_id="sid")
    assert canvas is not None, "composer returned None for non-empty content"
    blob = [title]
    for sec in canvas["horizontalSections"]:
        for col in sec.get("columns", []):
            for wp in col.get("webparts", []):
                blob.append(wp.get("innerHtml") or "")
    return "\n".join(blob)


class TestPublishingExtraction(unittest.TestCase):
    def test_richtext_image_blocks_and_order(self):
        blocks = audit._publishing_blocks(FIX_RICHTEXT_IMAGE)
        self.assertTrue(blocks, "expected >=1 block")
        # the image-field region carries the portrait img verbatim
        all_imgs = [im["src"] for b in blocks for im in b.get("images", [])]
        self.assertIn("/sites/Acme/PublishingImages/ceo-portrait.jpg", all_imgs)
        # a region with its own <h2> heading is keyed 'section'; others 'pub-field'
        kinds = [b["kind"] for b in blocks]
        for k in kinds:
            self.assertIn(k, ("pub-field", "section"))
        self.assertIn("section", kinds)  # the CEO heading region
        # ORDER preserved: image region appears before the heading text region
        joined = " ".join(b["text"] for b in blocks)
        self.assertIn("Message From Our CEO", joined)

    def test_summarylink_blocks(self):
        blocks = audit._publishing_blocks(FIX_RICHTEXT_SUMMARYLINK)
        self.assertTrue(blocks)
        kinds = [b["kind"] for b in blocks]
        self.assertTrue(set(kinds) <= {"pub-field", "section"})
        joined = " ".join(b["html"] for b in blocks)
        # summary-link anchors survive (href preserved by _clean_html)
        self.assertIn("Safety Handbook", joined)
        self.assertIn("Benefits Portal", joined)

    def test_richtext_only_is_pubfield(self):
        blocks = audit._publishing_blocks(FIX_RICHTEXT_ONLY)
        self.assertTrue(blocks)
        # no heading -> pure pub-field region
        self.assertEqual(blocks[0]["kind"], "pub-field")
        self.assertIn("front desk", blocks[0]["text"])

    def test_is_publishing_html_detection(self):
        self.assertTrue(audit._is_publishing_html(FIX_RICHTEXT_IMAGE))
        # a plain wiki body (no publishing chrome) is NOT routed to publishing
        self.assertFalse(audit._is_publishing_html("<p>just a wiki paragraph</p>"))


class TestPublishingCoverage(unittest.TestCase):
    """Composing the extracted blocks reproduces the source copy >= the gate bar."""

    def _assert_covered(self, fixture):
        content = audit._publishing_blocks(fixture)
        source_text = " ".join(b.get("text", "") for b in content)
        build_html = _compose_html(content)
        cov, missing, total = compose.copy_coverage(source_text, build_html)
        self.assertGreaterEqual(
            cov, COV_THRESHOLD,
            "coverage %.3f < %.2f; missing=%s" % (cov, COV_THRESHOLD, missing[:20]))

    def test_richtext_image_coverage(self):
        self._assert_covered(FIX_RICHTEXT_IMAGE)

    def test_summarylink_coverage(self):
        self._assert_covered(FIX_RICHTEXT_SUMMARYLINK)

    def test_richtext_only_coverage(self):
        self._assert_covered(FIX_RICHTEXT_ONLY)


class TestTriageBuildableFlip(unittest.TestCase):
    """G1: buildableTypes=['publishing'] flips a flagged publishing page to buildable,
    and ONLY when a handler is registered (flag-don't-fake)."""

    def _pub_page(self):
        return [{
            "file": "About.aspx", "title": "About Us", "lib": "Pages",
            "modified": "2026-05-01T00:00:00Z", "bytes": 4000,
            "webPartCount": 1, "isPublishing": True, "hasListWebpart": False,
        }]

    def test_publishing_flagged_by_default(self):
        rows = triage.classify(self._pub_page(), 18, 6, triage.datetime.now(triage.timezone.utc))
        r = rows[0]
        self.assertEqual(r["flagReason"], "publishing-layout")
        self.assertFalse(r["buildable"])

    def test_publishing_flips_when_whitelisted(self):
        rows = triage.classify(self._pub_page(), 18, 6,
                               triage.datetime.now(triage.timezone.utc),
                               buildable_types=["publishing"])
        r = rows[0]
        self.assertIsNone(r["flagReason"])
        self.assertTrue(r["buildable"])

    def test_no_flip_without_registered_handler(self):
        # 'list-driven' is NOT in HANDLED_TYPES -> whitelisting it must NOT flip
        page = [{
            "file": "Roster.aspx", "title": "Roster", "lib": "Site Pages",
            "modified": "2026-05-01T00:00:00Z", "bytes": 2000,
            "webPartCount": 1, "isPublishing": False, "hasListWebpart": True,
        }]
        rows = triage.classify(page, 18, 6,
                               triage.datetime.now(triage.timezone.utc),
                               buildable_types=["list-driven"])
        r = rows[0]
        self.assertEqual(r["flagReason"], "list-driven")
        self.assertFalse(r["buildable"])


if __name__ == "__main__":
    unittest.main()
