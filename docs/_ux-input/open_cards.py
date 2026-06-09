#!/usr/bin/env python3
import sys
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests
SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
r = requests.get(
    f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items?expand=fields&top=100",
    headers={"Authorization": "Bearer " + tok})
items = r.json().get("value", [])
openc, closed = [], 0
for it in items:
    f = it.get("fields", {})
    stage = f.get("Stage")
    title = f.get("Title") or ""
    proj = f.get("ProjectNo") or ""
    if stage == "Closed":
        closed += 1
    else:
        openc.append((stage, proj, title))
print(f"TOTAL {len(items)} | Closed {closed} | OPEN {len(openc)}")
for stage, proj, title in sorted(openc):
    print(f"  [{stage}] {proj}  {title}")
