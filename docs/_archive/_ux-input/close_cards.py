#!/usr/bin/env python3
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests
SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
tok = graph_token()
h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}

closes = {
 "16": "CLOSED, operator decision 2026-06-02: leave silent-drop. Non-members getting no reply is a sound security default for a gated bot; not worth a core access-control hand-patch (security-sensitive, plus wiped on each openclaw upgrade). The drop lives in core route-resolution / channel-DVHtbclf.js. Reopen via an upstream deniedMessage config option if real external users ever need it. Graceful copy is on file in docs/ux-copy-bot-rewrite.md section 6e.",
 "17": "CLOSED, mitigated: the persona rewrite eliminated empty turns in QA (zero empties across cold sessions). A rare model-level incomplete turn does not warrant a core send-path hand-patch (no config knob; high blast radius; wiped on upgrade). MONITOR; if dead-air recurs, fix hub-model reliability (deepseek-v4-flash is the source of incomplete turn detected log lines), not core. Fallback copy on file: section 6d.",
 "18": "CLOSED, operator decision 2026-06-02: keep the ~66 Telegram commands for now. No per-command allowlist exists and disabling native would also remove the operator slash-menu. Revisit when real end users (not just operator) use Telegram: then either channels.telegram.commands.native=false or a curated plugin patch (start, help, brief, status, handoff). Teams unaffected (uses the welcome card).",
}
for cid, notes in closes.items():
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE}/lists/{LIST}/items/{cid}/fields"
    r = requests.patch(url, headers=h, data=json.dumps({"Stage": "Closed", "Notes": notes}))
    print(cid, "-> Closed", r.status_code, "" if r.status_code < 300 else r.text[:120])
