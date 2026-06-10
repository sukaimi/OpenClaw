#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok}
# Pull a few items' fields to learn schema + distinct Stage values
url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items?expand=fields&top=50"
r = requests.get(url, headers=h)
items = r.json().get("value", [])
print("item count:", len(items))
stages = set()
sample_keys = None
titles = []
for it in items:
    f = it.get("fields", {})
    if sample_keys is None:
        sample_keys = [k for k in f.keys() if not k.startswith("@") and not k.startswith("_")]
    stages.add(f.get("Stage"))
    titles.append((f.get("Title"), f.get("Stage")))
print("field keys:", sample_keys)
print("distinct Stage values:", sorted(str(s) for s in stages))
print("sample titles+stage:")
for t in titles[:6]:
    print("  ", t)
