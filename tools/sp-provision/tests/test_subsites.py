#!/usr/bin/env python3
"""Unit tests for cc_sp_subsites — subsite enumeration + per-subsite job fan-out (JOB0024-109, sub-task 4).

Seams covered, all against SYNTHETIC webinfos JSON (no SharePoint, no network, no writes):
  - enumerate_subsites(): SharePoint REST `webinfos` payload (value[] of ServerRelativeUrl) AND a
    Graph `/sites/{id}/sites` payload (value[] of webUrl) both parse to {title, serverRelativeUrl};
    entries without an addressable URL are skipped; duplicates de-duped; order preserved.
  - fan_out(): one child descriptor per subsite with correct source/target URLs + parent linkage,
    config-driven target naming (no hardcoded site names), and NO writes anywhere.

Run: python3 -m unittest discover -s tests -v   (from tools/sp-provision)
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPDIR = os.path.dirname(HERE)
sys.path.insert(0, SPDIR)

import cc_sp_subsites as subsites  # noqa: E402


# --- Synthetic fixtures (2-3 nested webs) --------------------------------- #

# SharePoint REST /_api/web/webinfos shape.
WEBINFOS_REST = {
    "value": [
        {"Title": "HR Team", "ServerRelativeUrl": "/sites/Intranet/HR Team",
         "Id": "11111111-1111-1111-1111-111111111111", "WebTemplate": "STS"},
        {"Title": "Finance", "ServerRelativeUrl": "/sites/Intranet/Finance",
         "Id": "22222222-2222-2222-2222-222222222222", "WebTemplate": "STS"},
        {"Title": "Projects", "ServerRelativeUrl": "/sites/Intranet/Projects",
         "Id": "33333333-3333-3333-3333-333333333333", "WebTemplate": "PROJECTSITE"},
    ]
}

# Microsoft Graph /sites/{id}/sites shape (webUrl absolute, no ServerRelativeUrl).
WEBINFOS_GRAPH = {
    "value": [
        {"displayName": "HR Team", "name": "HR Team",
         "webUrl": "https://contoso.sharepoint.com/sites/Intranet/HR Team"},
        {"displayName": "Finance", "name": "Finance",
         "webUrl": "https://contoso.sharepoint.com/sites/Intranet/Finance"},
    ]
}


class TestEnumerate(unittest.TestCase):
    def test_rest_payload_parses_all_three(self):
        subs = subsites.enumerate_subsites(WEBINFOS_REST)
        self.assertEqual(len(subs), 3)
        self.assertEqual(subs[0], {"title": "HR Team",
                                   "serverRelativeUrl": "/sites/Intranet/HR Team"})
        self.assertEqual([s["title"] for s in subs], ["HR Team", "Finance", "Projects"])

    def test_graph_payload_derives_server_relative_url(self):
        subs = subsites.enumerate_subsites(WEBINFOS_GRAPH)
        self.assertEqual(len(subs), 2)
        # webUrl reduced to its server-relative path.
        self.assertEqual(subs[0]["serverRelativeUrl"], "/sites/Intranet/HR Team")
        self.assertEqual(subs[1]["serverRelativeUrl"], "/sites/Intranet/Finance")

    def test_skips_unaddressable_and_dedupes(self):
        payload = {"value": [
            {"Title": "No URL"},  # skipped: no addressable URL
            {"Title": "HR", "ServerRelativeUrl": "/sites/Intranet/HR Team"},
            {"Title": "HR dup", "ServerRelativeUrl": "/sites/Intranet/HR Team/"},  # dup (trailing /)
        ]}
        subs = subsites.enumerate_subsites(payload)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["title"], "HR")

    def test_bare_list_and_empty_inputs(self):
        self.assertEqual(subsites.enumerate_subsites([]), [])
        self.assertEqual(subsites.enumerate_subsites({}), [])
        self.assertEqual(subsites.enumerate_subsites(None), [])
        bare = subsites.enumerate_subsites(
            [{"Title": "X", "ServerRelativeUrl": "/sites/Intranet/X"}])
        self.assertEqual(len(bare), 1)


class TestFanOut(unittest.TestCase):
    def setUp(self):
        self.parent = {
            "job": "JOB0099",
            "sourceUrl": "https://contoso.sharepoint.com/sites/Intranet",
        }
        self.subs = subsites.enumerate_subsites(WEBINFOS_REST)

    def test_one_descriptor_per_subsite(self):
        children = subsites.fan_out(self.parent, self.subs, "{parent}-{slug}")
        self.assertEqual(len(children), 3)

    def test_descriptor_fields_source_target_parent(self):
        children = subsites.fan_out(self.parent, self.subs, "{parent}-{slug}")
        c0 = children[0]
        # child job id derived from parent + slug
        self.assertEqual(c0["job"], "JOB0099-HR-Team")
        # source URL grafts the subsite SRU onto the parent's scheme+host
        self.assertEqual(c0["sourceUrl"],
                         "https://contoso.sharepoint.com/sites/Intranet/HR Team")
        # target naming is config-driven via the template
        self.assertEqual(c0["targetSite"], "JOB0099-HR-Team")
        # parent linkage preserved on every child
        self.assertTrue(all(c["parent"] == "JOB0099" for c in children))

    def test_config_driven_target_template_no_hardcoded_names(self):
        children = subsites.fan_out(
            self.parent, self.subs,
            "https://build.example.com/sites/{parent}_{slug}")
        self.assertEqual(
            children[1]["targetSite"],
            "https://build.example.com/sites/JOB0099_Finance")
        # changing the template changes every target -> nothing hardcoded
        self.assertTrue(all(c["targetSite"].startswith("https://build.example.com/")
                            for c in children))

    def test_subsites_not_merged(self):
        # each subsite stays its own job — never collapsed into one.
        children = subsites.fan_out(self.parent, self.subs, "{parent}-{slug}")
        ids = [c["job"] for c in children]
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(ids, ["JOB0099-HR-Team", "JOB0099-Finance", "JOB0099-Projects"])

    def test_path_only_parent_source_falls_back_to_sru(self):
        parent = {"job": "JOB0099", "sourceUrl": "/sites/Intranet"}
        children = subsites.fan_out(parent, self.subs, "{parent}-{slug}")
        self.assertEqual(children[0]["sourceUrl"], "/sites/Intranet/HR Team")

    def test_missing_parent_job_raises(self):
        with self.assertRaises(ValueError):
            subsites.fan_out({"sourceUrl": "x"}, self.subs, "{parent}-{slug}")

    def test_missing_template_raises(self):
        with self.assertRaises(ValueError):
            subsites.fan_out(self.parent, self.subs, "")


class TestNoWrites(unittest.TestCase):
    """fan_out + enumerate must be pure: no files appear, mtimes unchanged."""

    def test_nothing_written_to_disk(self):
        before = {f: os.stat(os.path.join(SPDIR, f)).st_mtime
                  for f in os.listdir(SPDIR)
                  if os.path.isfile(os.path.join(SPDIR, f))}
        subs = subsites.enumerate_subsites(WEBINFOS_REST)
        subsites.fan_out({"job": "JOB0099", "sourceUrl": "https://h/sites/I"},
                         subs, "{parent}-{slug}")
        after_files = [f for f in os.listdir(SPDIR)
                       if os.path.isfile(os.path.join(SPDIR, f))]
        # no new files
        self.assertEqual(set(before), set(after_files))
        # no mtimes touched
        for f, mt in before.items():
            self.assertEqual(os.stat(os.path.join(SPDIR, f)).st_mtime, mt)


if __name__ == "__main__":
    unittest.main()
