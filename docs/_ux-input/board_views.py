#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok}

# views
r = requests.get("https://graph.microsoft.com/v1.0/sites/%s/lists/%s/views" % (SITE, LIST), headers=h)
print("=== VIEWS ===", r.status_code)
print(json.dumps(r.json(), indent=1)[:1500])

# closed cards with Created/Modified to confirm current order
r2 = requests.get("https://graph.microsoft.com/v1.0/sites/%s/lists/%s/items?expand=fields&top=200" % (SITE, LIST), headers=h)
print("=== CLOSED cards (id, Created, Modified, title) ===")
rows = []
for it in r2.json().get("value", []):
    f = it.get("fields", {})
    if f.get("Stage") == "Closed":
        rows.append((int(it["id"]), it.get("createdDateTime", "")[:19], it.get("lastModifiedDateTime", "")[:19], (f.get("Title") or "")[:35]))
for x in sorted(rows):
    print(" ", x)
