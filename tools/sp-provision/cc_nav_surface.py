#!/usr/bin/env python3
"""Surface the unsurfaced Command Center pages in the left-nav (QuickLaunch),
grouped. Idempotent (dedup by normalised Url). Adds:
  Runbooks (existing parent) -> + SP Conversion Runbook, + Rollback Runbook
  Learnings (new parent)     -> + 3 Learnings pages
  Themes & Layouts Gallery   -> new top-level node
QuickLaunch is SP-REST-only (not Graph-writable)."""
import json
import sys

import requests

sys.path.insert(0, "/root/.openclaw/sp-provision")
from cc_provision_intake import (  # noqa: E402
    _sp_rest_token, _form_digest, _quicklaunch_nodes, _norm_nav_url,
    _ensure_quicklaunch, SITE_WEB,
)

BASE = "/sites/CodeCraftAICommandCenter/SitePages/"


def _hdrs(tok, digest):
    return {"Authorization": "Bearer " + tok, "Accept": "application/json;odata=verbose",
            "Content-Type": "application/json;odata=verbose", "X-RequestDigest": digest}


def _children(tok, node_id):
    h = {"Authorization": "Bearer " + tok, "Accept": "application/json;odata=nometadata"}
    r = requests.get(SITE_WEB + "/_api/web/navigation/GetNodeById(%d)/Children" % node_id, headers=h)
    r.raise_for_status()
    return r.json().get("value", [])


def add_child(tok, digest, parent_id, title, url):
    for c in _children(tok, parent_id):
        if _norm_nav_url(c.get("Url")) == _norm_nav_url(url):
            print("  child exists:", title); return
    body = {"__metadata": {"type": "SP.NavigationNode"}, "Title": title, "Url": url, "IsVisible": True}
    r = requests.post(SITE_WEB + "/_api/web/navigation/GetNodeById(%d)/Children" % parent_id,
                      headers=_hdrs(tok, digest), data=json.dumps(body))
    print("  child add %-34s -> %d %s" % (title, r.status_code,
          "ok" if r.status_code in (200, 201) else r.text[:200]))


def find_node(tok, title=None, url=None):
    for n in _quicklaunch_nodes(tok):
        if title and n.get("Title") == title:
            return n
        if url and _norm_nav_url(n.get("Url")) == _norm_nav_url(url):
            return n
    return None


def main():
    tok = _sp_rest_token()
    digest = _form_digest(tok)

    # 1) Runbooks group: add the two unsurfaced runbooks as children
    rb = find_node(tok, title="Runbooks")
    print("Runbooks node id:", rb.get("Id") if rb else None)
    if rb:
        add_child(tok, digest, rb["Id"], "SP Conversion Runbook", BASE + "SP-Conversion-Runbook.aspx")
        add_child(tok, digest, rb["Id"], "Rollback Runbook", BASE + "Rollback-Runbook.aspx")

    # 2) Learnings group: new top-level parent (lands on codification page) + 3 children
    print("Learnings parent:")
    _ensure_quicklaunch(tok, "Learnings", BASE + "Learnings-SP-Pipeline-Codification.aspx")
    ln = find_node(tok, title="Learnings")
    print("  Learnings node id:", ln.get("Id") if ln else None)
    if ln:
        add_child(tok, digest, ln["Id"], "SP Pipeline Codification", BASE + "Learnings-SP-Pipeline-Codification.aspx")
        add_child(tok, digest, ln["Id"], "Level-2 Access Model", BASE + "Learnings-Level-2-Access-Model.aspx")
        add_child(tok, digest, ln["Id"], "JOB0017 Themes/Layouts", BASE + "Learnings-JOB0017-Themes-Layouts.aspx")

    # 3) Themes & Layouts Gallery: top-level
    print("Themes & Layouts Gallery:")
    st, _ = _ensure_quicklaunch(tok, "Themes & Layouts Gallery", BASE + "Themes-Layouts-Gallery.aspx")
    print("  ->", st)


if __name__ == "__main__":
    main()
