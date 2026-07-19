#!/usr/bin/env python3
import sys
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok}
# list columns -> find Stage choices
r = requests.get(
    "https://graph.microsoft.com/v1.0/sites/%s/lists/%s/columns" % (SITE, LIST),
    headers=h)
for c in r.json().get("value", []):
    if c.get("name") in ("Stage", "Title", "Notes", "ProjectNo") or c.get("choice"):
        ch = c.get("choice", {}).get("choices") if c.get("choice") else None
        print(c.get("name"), "| choice:", ch)
# also dump JOB0003 item ids so we can move them
r2 = requests.get(
    "https://graph.microsoft.com/v1.0/sites/%s/lists/%s/items?expand=fields&top=200" % (SITE, LIST),
    headers=h)
print("--- JOB0003 items ---")
for it in r2.json().get("value", []):
    f = it.get("fields", {})
    if f.get("ProjectNo") == "JOB0003":
        print(it.get("id"), "|", f.get("Stage"), "|", (f.get("Title") or "")[:55])
