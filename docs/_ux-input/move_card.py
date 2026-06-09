#!/usr/bin/env python3
# usage: move_card.py <itemId> <Stage> ["Notes to append/replace"]
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests
SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
item, stage = sys.argv[1], sys.argv[2]
notes = sys.argv[3] if len(sys.argv) > 3 else None
fields = {"Stage": stage}
if notes:
    fields["Notes"] = notes
tok = graph_token()
url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items/{item}/fields"
r = requests.patch(url, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, data=json.dumps(fields))
print(item, "->", stage, "status", r.status_code, "" if r.status_code < 300 else r.text[:150])
