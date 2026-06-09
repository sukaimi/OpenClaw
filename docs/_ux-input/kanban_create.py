#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items"

cards = [
    ("UX · Non-allowlisted user: graceful first reply (replace silent drop)",
     "P0. Today a non-allowlisted Teams user is silently dropped (dmPolicy=allowlist) — reads as a dead bot. Emit one graceful branded reply on first contact instead. Copy ready: docs/ux-copy-bot-rewrite.md §6e. Needs a logic change in the minified @openclaw/msteams handler (drop path) — do with operator present. See docs/ux-implementation-status.md."),
    ("UX · Empty/parse-error reply guard (model dead-air fallback)",
     "P0. deepseek-v4-flash occasionally returns an empty/incomplete turn; raw parse-error must never reach the user. Add a reply-pipeline guard substituting 'Sorry — something dropped on my end. Could you send that again?'. Copy: ux-copy-bot-rewrite.md §6d. Code change."),
    ("UX · Telegram command-menu decision (66 infra commands → curated/disable)",
     "P1, Telegram only. End users see ~66 openclaw CLI/admin commands. No per-command allowlist in config (channels.telegram.commands only toggles native on/off). Decide: disable native menu (also removes operator slash-commands) vs plugin patch for curated 5 (/start /help /brief /status /handoff). ux-copy-bot-rewrite.md §8. Teams unaffected."),
    ("UX · Make Teams welcome-card edit durable (plugin config or fork)",
     "The rebranded welcome card was applied by editing vendored dist (…/@openclaw/msteams/dist/src-D_rcW2Zm.js, buildWelcomeCard). It will be OVERWRITTEN on any plugins install/upgrade. Make durable via upstream plugin config (promptStarters/botName options exist) or a maintained fork. Backup: *.bak-uxcard."),
]

created = []
for title, notes in cards:
    body = {"fields": {"Title": title, "Stage": "Intake", "Notes": notes, "ProjectNo": "JOB0002"}}
    r = requests.post(url, headers=h, data=json.dumps(body))
    if r.status_code >= 300:
        # retry without ProjectNo in case the column is typed/numeric
        body2 = {"fields": {"Title": title, "Stage": "Intake", "Notes": notes}}
        r = requests.post(url, headers=h, data=json.dumps(body2))
    ok = r.status_code < 300
    cid = r.json().get("id") if ok else r.text[:120]
    created.append((ok, cid, title[:50]))
    print(("OK  " if ok else "FAIL"), cid, "|", title[:60])

print("created", sum(1 for c in created if c[0]), "of", len(cards))
