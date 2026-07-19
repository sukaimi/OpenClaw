#!/usr/bin/env python3
"""Unit tests for SP classic->modern list-view coverage (JOB0024-109, sub-task 2).

Covers two seams:
  Sub-task 2 - sp-audit._listview_blocks(): a parsed list-items array (a LINK list
        and a DATA list) is turned into ONE ordered content[] block of kind
        'listview' carrying ALL item titles + hrefs verbatim; composing it through
        the SAME verbatim composer yields copy_coverage >= threshold.
  Triage   - cc_sp_triage.classify(): buildableTypes=["list"] flips a flagged
        list-driven page flag->buildable (and only because a handler is now
        registered in HANDLED_TYPES).

Repo-only, synthetic fixtures — no SharePoint, no network, no live capture, no
live Graph list fetch (that path is a flagged stub: _fetch_list_items).
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
# Synthetic list-items fixtures (what _fetch_list_items WOULD return; here parsed
# from capture/synthetic, NOT a live read). One LINK list, one DATA list.
# --------------------------------------------------------------------------- #

# A link list (e.g. a "Useful Links" XsltListViewWebPart) — each row has an href.
FIX_LINK_LIST = [
    {"title": "Employee Handbook", "href": "/sites/Acme/SitePages/Handbook.aspx"},
    {"title": "IT Service Desk", "href": "https://acme.example.com/helpdesk"},
    {"title": "Travel Booking Portal", "href": "https://travel.example.com/acme"},
]

# A data list (e.g. an "Office Locations" ContentByQuery) — titles + extra text,
# no links.
FIX_DATA_LIST = [
    {"title": "Eastern Plant", "text": "Hanover, New Jersey — manufacturing"},
    {"title": "Western Depot", "text": "Reno, Nevada — logistics and distribution"},
    {"title": "Corporate Office", "text": "Chicago, Illinois — headquarters"},
]


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


class TestListviewExtraction(unittest.TestCase):
    def test_link_list_one_ordered_block(self):
        blocks = audit._listview_blocks(FIX_LINK_LIST)
        self.assertEqual(len(blocks), 1, "expected exactly ONE listview block")
        b = blocks[0]
        self.assertEqual(b["kind"], "listview")
        # ALL titles present, IN ORDER, and each href present (verbatim) in the html.
        html = b["html"]
        last = -1
        for it in FIX_LINK_LIST:
            self.assertIn(it["title"], html)
            pos = html.find(it["title"])
            self.assertGreater(pos, last, "list-view items lost their source order")
            last = pos
            self.assertIn(it["href"], html)        # href as anchor target + text
        # link list -> rendered as anchors
        self.assertIn("<a href=", html)

    def test_data_list_one_ordered_block(self):
        blocks = audit._listview_blocks(FIX_DATA_LIST)
        self.assertEqual(len(blocks), 1)
        b = blocks[0]
        self.assertEqual(b["kind"], "listview")
        html = b["html"]
        for it in FIX_DATA_LIST:
            self.assertIn(it["title"], html)
            self.assertIn(it["text"].split(" — ")[0], html)  # extra text survives
        # data list -> no anchors
        self.assertNotIn("<a href=", html)

    def test_empty_list_no_block(self):
        self.assertEqual(audit._listview_blocks([]), [])
        self.assertEqual(audit._listview_blocks([{"title": ""}]), [])

    def test_live_fetch_is_a_flagged_stub(self):
        # the live Graph list fetch is intentionally NOT wired on this rail.
        with self.assertRaises(NotImplementedError):
            audit._fetch_list_items("sid", "Useful Links")


class TestListviewCoverage(unittest.TestCase):
    """Composing the snapshot block reproduces ALL item copy >= the gate bar."""

    def _assert_covered(self, items):
        content = audit._listview_blocks(items)
        source_text = " ".join(b.get("text", "") for b in content)
        build_html = _compose_html(content)
        cov, missing, total = compose.copy_coverage(source_text, build_html)
        self.assertGreaterEqual(
            cov, COV_THRESHOLD,
            "coverage %.3f < %.2f; missing=%s" % (cov, COV_THRESHOLD, missing[:20]))
        return cov

    def test_link_list_coverage(self):
        self._assert_covered(FIX_LINK_LIST)

    def test_data_list_coverage(self):
        self._assert_covered(FIX_DATA_LIST)

    def test_all_titles_and_hrefs_present_after_compose(self):
        content = audit._listview_blocks(FIX_LINK_LIST)
        build_html = _compose_html(content)
        for it in FIX_LINK_LIST:
            self.assertIn(it["title"], build_html)
            self.assertIn(it["href"], build_html)


class TestTriageListBuildableFlip(unittest.TestCase):
    """buildableTypes=['list'] flips a flagged list-driven page to buildable, and
    ONLY because a handler is now registered in HANDLED_TYPES (flag-don't-fake)."""

    def _list_page(self):
        return [{
            "file": "Locations.aspx", "title": "Office Locations", "lib": "Site Pages",
            "modified": "2026-05-01T00:00:00Z", "bytes": 3000,
            "webPartCount": 1, "isPublishing": False, "hasListWebpart": True,
        }]

    def test_list_flagged_by_default(self):
        rows = triage.classify(self._list_page(), 18, 6,
                               triage.datetime.now(triage.timezone.utc))
        r = rows[0]
        self.assertEqual(r["flagReason"], "list-driven")
        self.assertFalse(r["buildable"])

    def test_list_flips_when_whitelisted(self):
        rows = triage.classify(self._list_page(), 18, 6,
                               triage.datetime.now(triage.timezone.utc),
                               buildable_types=["list"])
        r = rows[0]
        self.assertIsNone(r["flagReason"])
        self.assertTrue(r["buildable"])

    def test_list_handler_registered(self):
        self.assertIn("list", triage.HANDLED_TYPES)


if __name__ == "__main__":
    unittest.main()
