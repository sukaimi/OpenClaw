#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests
SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}

updates = {
 "16": ("Intake",
   "INVESTIGATED, defer to supervised session. The non-allowlisted DM drop (dropping dm not allowlisted) lives in GATEWAY CORE: /usr/lib/node_modules/openclaw/dist/channel-runtime-Eq3ifkF3.js, NOT the msteams plugin. It is shared channel access-control; a wrong edit risks allowlist/security across ALL channels and is wiped on any openclaw upgrade. Not safe to edit unattended. Graceful reply copy is ready in docs/ux-copy-bot-rewrite.md section 6e. Best durable fix: request an upstream deniedMessage config option for channels."),
 "17": ("Intake",
   "INVESTIGATED, defer to supervised session. No config knob exists (schema only has embeddings/acp fallbacks). The empty/incomplete-turn path is GATEWAY CORE: send-Djd3po9o.js and cli-runner. A user-facing fallback (Sorry, something dropped on my end, please resend, copy 6d) needs a core code change (high blast radius, wiped on upgrade). LARGELY MITIGATED ALREADY by the persona fix (fresh sessions return non-empty in testing). If dead-air recurs, also consider a more reliable hub model than deepseek-v4-flash, which is the source of the incomplete turn detected log lines."),
 "18": ("Intake",
   "RECOMMENDATION, decision needed. Telegram surfaces ~66 openclaw CLI/admin commands to end users. No per-command allowlist exists (channels.telegram.commands only toggles native on/off, per-channel-global). The Delivery Lead is conversational, end users brief in natural language not slash commands. REC: when real end users arrive on Telegram, set channels.telegram.commands.native=false (removes the 66-command menu, operator can still type commands as text) OR plugin-patch a curated set (start, help, brief, status, handoff). NOT done now because it would also strip the operator slash-menu on Telegram. Teams is unaffected (uses the welcome card). Operator decision."),
}
for cid, (stage, notes) in updates.items():
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items/{cid}/fields"
    r = requests.patch(url, headers=h, data=json.dumps({"Stage": stage, "Notes": notes}))
    print(cid, "->", stage, r.status_code, "" if r.status_code < 300 else r.text[:120])
