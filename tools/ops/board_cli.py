#!/usr/bin/env python3
"""cc-board — Code&Craft Kanban CLI for the dispatch chain.
Usage:
  board_cli.py read [PROJ]                  # summarize cards (default JOB0003)
  board_cli.py move <itemId> <Stage> [note] # move a card, optional Notes
  board_cli.py next-tick [PROJ] [--dry]     # schedule next dispatch tick iff Intake remains
"""
import sys, os, json, time, subprocess
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
BASE = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s" % (SITE, LIST)
TICK_MSG = ("Phase 1 dispatch tick. Follow "
            "/root/.openclaw/workspace-delivery-lead/DISPATCH.md exactly. "
            "Do ONE card, then run `cc-board next-tick` to self-continue.")


def _items(proj):
    tok = graph_token()
    r = requests.get(BASE + "/items?expand=fields&top=200",
                     headers={"Authorization": "Bearer " + tok})
    out = []
    for it in r.json().get("value", []):
        f = it.get("fields", {})
        if f.get("ProjectNo") == proj:
            out.append((int(it["id"]), f.get("Stage"), f.get("Title") or "", f.get("Notes") or ""))
    return sorted(out, key=lambda x: x[0])


def cmd_read(proj):
    items = _items(proj)
    counts = {}
    for _id, st, _t, _n in items:
        counts[st] = counts.get(st, 0) + 1
    intake = [i for i in items if i[1] == "Intake"]
    print("PROJECT", proj, "| total", len(items), "| counts", dict(sorted(counts.items())))
    nxt = intake[0][0] if intake else None
    print("NEXT_INTAKE", nxt if nxt is not None else "NONE")
    for _id, st, t, n in items:
        flag = " [BLOCKED]" if (n or "").strip().upper().startswith("BLOCKED") else ""
        print("  %s  [%s]%s  %s" % (_id, st, flag, t[:55]))


CANON_STAGES = ["Intake", "Content Audit", "Content Architecture", "Wireframes", "Design",
                "Build", "Internal QA", "Staging", "Production", "Closed"]


def _norm_stage(s):
    # tolerate case/spacing variance from agents; map to the exact Kanban column name
    for c in CANON_STAGES:
        if str(s).strip().lower() == c.lower():
            return c
    return s


def _resolve(item):
    # Accept either a numeric itemId OR a JOB#### ProjectNo (agents reference jobs by ProjectNo).
    if str(item).isdigit():
        return item
    r = requests.get(BASE + "/items?expand=fields&top=400",
                     headers={"Authorization": "Bearer " + graph_token()})
    for it in r.json().get("value", []):
        if (it.get("fields", {}).get("ProjectNo") or "") == item:
            return it["id"]
    return None


def cmd_move(item, stage, note):
    rid = _resolve(item)
    if rid is None:
        print("no card found for", item); sys.exit(1)
    item = rid
    stage = _norm_stage(stage)
    tok = graph_token()
    # BL-001 hard gate: a CLIENT job (has /srv/projects/<JOB>/brief.json) cannot be moved to Closed
    # unless cc-verify-client wrote the .verified marker. Agents physically cannot self-close.
    if str(stage).strip().lower() == "closed":
        g = requests.get(BASE + "/items/%s?expand=fields" % item,
                         headers={"Authorization": "Bearer " + tok})
        proj = (g.json().get("fields") or {}).get("ProjectNo") or ""
        pd = "/srv/projects/%s" % proj
        if proj and os.path.exists(pd + "/brief.json") and not os.path.exists(pd + "/.verified"):
            print("REFUSED: %s (%s) is a client job with no verify marker. Run `cc-verify-client %s` "
                  "— only a PASS may close it." % (item, proj, proj))
            sys.exit(2)
    fields = {"Stage": stage}
    if note:
        fields["Notes"] = note
    r = requests.patch(BASE + "/items/%s/fields" % item,
                       headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                       data=json.dumps(fields))
    print(item, "->", stage, "status", r.status_code, "" if r.status_code < 300 else r.text[:160])
    sys.exit(0 if r.status_code < 300 else 1)


def cmd_next_tick(proj, dry):
    items = _items(proj)
    intake = [i for i in items if i[1] == "Intake"]
    blocked = [i for i in items if (i[3] or "").strip().upper().startswith("BLOCKED")]
    if not intake:
        print("DRAINED — no Intake cards remain for", proj)
        if blocked:
            print("BLOCKED cards still open:")
            for _id, st, t, _n in blocked:
                print("  %s [%s] %s" % (_id, st, t[:55]))
        print("ACTION: stop. Do NOT schedule another tick.")
        return
    print("WORK_REMAINS —", len(intake), "Intake card(s); next =", intake[0][0])
    if dry:
        print("DRY: would schedule one-shot tick +1m")
        return
    name = "cc-phase1-tick-%d" % int(time.time())
    cmd = ["openclaw", "cron", "add", name, "--at", "+1m", "--agent", "main",
           "--delete-after-run", "--message", TICK_MSG]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print("SCHEDULED", name, "rc", p.returncode)
    if p.returncode != 0:
        print("CRON_STDERR", (p.stderr or p.stdout)[:200])
        sys.exit(1)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    cmd = a[0]
    if cmd == "read":
        cmd_read(a[1] if len(a) > 1 else "JOB0003")
    elif cmd == "move":
        cmd_move(a[1], a[2], a[3] if len(a) > 3 else None)
    elif cmd == "next-tick":
        rest = [x for x in a[1:] if x != "--dry"]
        proj = rest[0] if rest else "JOB0003"
        cmd_next_tick(proj, "--dry" in a)
    else:
        print("unknown:", cmd); sys.exit(1)


if __name__ == "__main__":
    main()
