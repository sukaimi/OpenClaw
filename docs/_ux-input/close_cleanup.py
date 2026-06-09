#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests
SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}

rules = [
    ("register Azure Bot",
     "CLOSED: done. Azure bot OpenClaw-Teams-Bot-CnC registered (appId 9f815fcb-95b3-4cd4-b9de-f6017a8e5d1a, tenant 135ea4fa-...); Teams channel LIVE with round-trip verified 2026-06-02. Card was stale in Intake."),
    ("OpenCode",
     "CLOSED: wired. opencode binary installed (/usr/bin/opencode v1.15.13), authed via openrouter, and the engineer prompt (workspace-full-stack-engineer/AGENTS.md L49,56-57) delegates code generation to OpenCode on the profile coder (Profile A = Qwen3 Coder). Design is prompt-level invocation via the exec tool, not a config cliBackend/acp (intended). Full sample-brief->site run is the separate e2e card (already Closed)."),
    ("UX refresh of Command Center",
     "CLOSED: delivered. Command Center homepage redesigned (Stone & Line brand, reference-inspired) and brand theme applied last session. Pending operator visual sign-off only; reopen for any tweaks."),
]

r = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items?expand=fields&top=100", headers=h)
items = r.json().get("value", [])
done = 0
for it in items:
    f = it.get("fields", {})
    if f.get("Stage") == "Closed":
        continue
    title = f.get("Title") or ""
    cid = f.get("id")
    for needle, note in rules:
        if needle.lower() in title.lower():
            url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items/{cid}/fields"
            rr = requests.patch(url, headers=h, data=json.dumps({"Stage": "Closed", "Notes": note}))
            print(f"{cid} '{title[:45]}' -> Closed {rr.status_code}")
            done += 1
            break
print("closed", done, "card(s)")
