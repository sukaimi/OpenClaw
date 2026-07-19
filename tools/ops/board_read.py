#!/usr/bin/env python3
import sys
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
r = requests.get(
    "https://graph.microsoft.com/v1.0/sites/%s/lists/%s/items?expand=fields&top=200" % (SITE, LIST),
    headers={"Authorization": "Bearer " + tok})
items = r.json().get("value", [])
projs = {}
openc = []
for it in items:
    f = it.get("fields", {})
    p = f.get("ProjectNo") or "-"
    projs[p] = projs.get(p, 0) + 1
    if f.get("Stage") != "Closed":
        openc.append((f.get("Stage"), p, (f.get("Title") or "")[:55]))
print("TOTAL", len(items))
print("PROJECTS:", dict(sorted(projs.items())))
print("OPEN", len(openc))
for s, p, t in sorted(openc):
    print("  [%s] %s  %s" % (s, p, t))
