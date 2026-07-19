#!/usr/bin/env python3
"""cc-sp-subsites — subsite hierarchy enumeration + per-subsite job fan-out (JOB0024-109, sub-task 4).

The classic->modern pipeline (cc-sp-mirror) converts ONE site. A classic site collection often
nests SUBSITES (webs) under the source web; each is its own page/list/nav surface and must NOT be
merged into the parent. This module:

  1. enumerate_subsites(webinfos)  -> parse a provided SharePoint REST `/_api/web/webinfos` payload
     (or a Graph `/sites/{id}/sites` payload) into a flat list of child webs
     ({title, serverRelativeUrl}). PURE parse of provided JSON — makes NO live calls.

  2. fan_out(parent_job, subsites, target_template)  -> one CHILD JOB DESCRIPTOR per subsite
     ({job, sourceUrl, targetSite, parent}). Target naming is config-driven via `target_template`
     (no hardcoded site names). Returns pure descriptors — writes NOTHING anywhere.

  CLI:  cc_sp_subsites.py <parent-job> --webinfos <json> [--dry-run]
        prints the child-job plan derived from a provided webinfos JSON file.

LIVE-REFERENCE CAVEAT (cannot be validated repo-only — needs a reference nested site):
  - nested-web AUTH (the delegated session must actually reach each child web's _api),
  - final target-site naming collisions / provisioning, and nav stitching parent<->child,
  resolve only against a real multi-web source. This module implements + unit-tests the
  enumeration/fan-out LOGIC; those live seams are flagged, not exercised.

Repo-only. No network. No SharePoint. No writes. Match cc_sp_config / cc-sp-mirror style.
"""
import argparse
import json
import re
import sys
from urllib.parse import urlsplit


# Default child-target naming template. {parent} = parent job id, {slug} = subsite slug.
# Config-driven: callers pass their own template; this is only the fallback default.
DEFAULT_TARGET_TEMPLATE = "{parent}-{slug}"


def _server_relative_url(entry):
    """Pull a server-relative URL out of either a SharePoint REST webinfos entry
    (ServerRelativeUrl) or a Graph /sites child entry (webUrl -> path)."""
    if not isinstance(entry, dict):
        return None
    sru = entry.get("ServerRelativeUrl") or entry.get("serverRelativeUrl")
    if sru:
        return sru
    # Graph: webUrl is absolute (https://host/sites/x/sub); reduce to its path.
    web_url = entry.get("webUrl") or entry.get("url")
    if web_url:
        return urlsplit(web_url).path or web_url
    return None


def _title(entry):
    return (
        entry.get("Title")
        or entry.get("title")
        or entry.get("displayName")
        or entry.get("name")
        or ""
    )


def enumerate_subsites(webinfos):
    """Given a parsed SharePoint `/_api/web/webinfos` payload OR a Graph `/sites/{id}/sites`
    payload (dict with a value[] list, or a bare list), return child webs as ordered
    [{"title": str, "serverRelativeUrl": str}, ...].

    PURE parse of provided JSON — makes NO live calls. Entries without a resolvable
    server-relative URL are skipped (cannot fan a job we can't address); order preserved;
    duplicate serverRelativeUrls de-duplicated (first wins)."""
    if isinstance(webinfos, dict):
        rows = (
            webinfos.get("value")
            or webinfos.get("webinfos")
            or webinfos.get("webs")
            or []
        )
    elif isinstance(webinfos, list):
        rows = webinfos
    else:
        rows = []

    out = []
    seen = set()
    for entry in rows:
        sru = _server_relative_url(entry)
        if not sru:
            continue
        key = sru.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": _title(entry), "serverRelativeUrl": sru})
    return out


def _slug(server_relative_url):
    """Last path segment of a server-relative URL, sanitised for use in a target name/job id.
    '/sites/Intranet/HR Team' -> 'HR-Team'. Empty/odd input -> 'subsite'."""
    leaf = server_relative_url.rstrip("/").rsplit("/", 1)[-1]
    leaf = re.sub(r"[^A-Za-z0-9]+", "-", leaf).strip("-")
    return leaf or "subsite"


def _source_url(parent_source, server_relative_url):
    """Compose the child's absolute source URL: graft the subsite's server-relative path onto
    the parent source's scheme+host. If parent_source is itself only a path, return the SRU."""
    parts = urlsplit(parent_source)
    if parts.scheme and parts.netloc:
        return "%s://%s%s" % (parts.scheme, parts.netloc, server_relative_url)
    return server_relative_url


def fan_out(parent_job, subsites, target_template, parent_source=None):
    """Produce one CHILD JOB DESCRIPTOR per subsite — pure dicts, NO writes anywhere.

    parent_job      : {"job", "sourceUrl", ...}  (the parent job.config.json, or a minimal dict).
    subsites        : output of enumerate_subsites() (or any [{"title","serverRelativeUrl"}]).
    target_template : config-driven format string, e.g. "{parent}-{slug}" — fields available:
                      {parent} (parent job id), {slug} (subsite slug), {title} (subsite title).
                      Substituted to form each child targetSite name. NO hardcoded site names.
    parent_source   : optional override for the parent source URL (else parent_job['sourceUrl']).

    Returns: [{"job", "sourceUrl", "targetSite", "parent"}, ...] — one per subsite, in order.
    """
    if isinstance(parent_job, dict):
        parent_id = parent_job.get("job") or ""
        src_base = parent_source or parent_job.get("sourceUrl") or ""
    else:
        parent_id = str(parent_job)
        src_base = parent_source or ""
    if not parent_id:
        raise ValueError("fan_out: parent_job must carry a job id")
    if not target_template:
        raise ValueError("fan_out: target_template is required (config-driven naming)")

    descriptors = []
    for sub in subsites:
        sru = sub.get("serverRelativeUrl")
        if not sru:
            continue
        slug = _slug(sru)
        target = target_template.format(
            parent=parent_id, slug=slug, title=sub.get("title") or slug
        )
        descriptors.append({
            "job": "%s-%s" % (parent_id, slug),
            "sourceUrl": _source_url(src_base, sru),
            "targetSite": target,
            "parent": parent_id,
        })
    return descriptors


def main():
    ap = argparse.ArgumentParser(prog="cc-sp-subsites")
    ap.add_argument("parent_job", help="parent JOB#### id")
    ap.add_argument("--webinfos", required=True,
                    help="path to a provided webinfos / Graph /sites JSON (parsed, NOT fetched)")
    ap.add_argument("--source-url", default="",
                    help="parent source site URL (scheme+host grafted onto each child SRU)")
    ap.add_argument("--target-template", default=DEFAULT_TARGET_TEMPLATE,
                    help="config-driven child target naming template, e.g. '{parent}-{slug}'")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the child-job plan; this tool NEVER writes regardless")
    a = ap.parse_args()

    with open(a.webinfos) as f:
        webinfos = json.load(f)

    subsites = enumerate_subsites(webinfos)
    parent = {"job": a.parent_job, "sourceUrl": a.source_url}
    children = fan_out(parent, subsites, a.target_template)

    print("=" * 78)
    print("cc-sp-subsites — child-job fan-out plan (DESCRIPTORS only; nothing written)")
    print("  parent      = %s" % a.parent_job)
    print("  sourceUrl   = %s" % (a.source_url or "(none — child sourceUrl = server-relative)"))
    print("  template    = %s" % a.target_template)
    print("  subsites    = %d" % len(subsites))
    print("=" * 78)
    for i, c in enumerate(children, 1):
        print("\n%2d. %s" % (i, c["job"]))
        print("    sourceUrl  = %s" % c["sourceUrl"])
        print("    targetSite = %s" % c["targetSite"])
        print("    parent     = %s" % c["parent"])
    if not children:
        print("\n(no subsites found in payload)")
    print("\n" + "=" * 78)
    # Documented limitation: nested-web auth reach, target-name collision/provisioning, and
    # parent<->child nav stitching are not exercised in this snapshot.


if __name__ == "__main__":
    main()
