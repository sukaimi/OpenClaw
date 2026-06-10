#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
r = requests.get("https://graph.microsoft.com/v1.0/sites/%s/lists/%s/items?expand=fields&top=300" % (SITE, LIST),
                 headers={"Authorization": "Bearer " + tok})
proj = {}
for it in r.json().get("value", []):
    f = it.get("fields", {})
    p = f.get("ProjectNo") or "(none)"
    d = proj.setdefault(p, {"total": 0, "closed": 0, "open": 0, "created": [], "modified": [], "titles": []})
    d["total"] += 1
    if f.get("Stage") == "Closed":
        d["closed"] += 1
    else:
        d["open"] += 1
    d["created"].append(it.get("createdDateTime", "")[:10])
    d["modified"].append(it.get("lastModifiedDateTime", "")[:10])
    d["titles"].append((f.get("Title") or "")[:48])

for p in sorted(proj):
    d = proj[p]
    status = "CLOSED" if d["open"] == 0 else "OPEN (%d open)" % d["open"]
    print("%-9s | %2d cards | %-14s | %s -> %s" % (
        p, d["total"], status, min(d["created"]), max(d["modified"])))
    for t in d["titles"][:3]:
        print("            - " + t)
    print("            ...")
