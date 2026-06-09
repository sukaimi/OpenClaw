#!/usr/bin/env python3
# Phase 2 — Front Door + Money. Creates JOB0004 cards in Intake. Does NOT build (awaits Sukaimi approval).
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
PROJ = "JOB0004"

cards = [
    ("Phase2 · Intake bridge (cc-intake): paid submission -> JOB####",
     "P0 / foundation. The glue that turns a PAID Tally submission into a job on the engine board — but only AFTER operator 'go'. Maps form fields -> job (type, declared pages, structured copy, image uploads pulled from Tally). Creates a new JOB#### in Intake for the Phase-1 engine to build. Builder: Claude."),

    ("Phase2 · CRO landing 1-pager (request.codeandcraft.ai)",
     "P1. Single-page, conversion-optimised: hero + value prop, how-it-works (3 steps), pricing (SGD10/page), LIVE slot-counter + urgency, the embedded order form, footer with T&C/Privacy links. Built by O/C on the static-web rail (dogfood) under the verify gate; deploy to Sukaimi's Vercel. Claude orchestrates O/C + verifies."),

    ("Phase2 · Tally order form (web/EDM only, no SP)",
     "P1. Tally form: type (multipage_site | single_page | edm — NO SharePoint), DECLARED page count, structured copy (headline/body/CTA per section), image uploads. Free tier; embeds in the landing page. Builder: Claude wires config; Sukaimi owns the Tally account."),

    ("Phase2 · Stripe Payment Link (pages x SGD10)",
     "P1. Stripe Payment Link, quantity = declared pages @ SGD10 each. On payment -> fires the operator ping. Needs Stripe account + keys — PROMPT Sukaimi, never set silently. Builder: Claude wires; Sukaimi provides account/keys."),

    ("Phase2 · Monthly slot counter + waitlist mode",
     "P1. 10-total-requests/month counter, resets on the 1st. Landing page reads slots-left from a small status file (client-side fetch — still no maintained backend). When 0 left, the page swaps the order form for a WAITLIST capture; operator notified of waitlist signups. Builder: Claude."),

    ("Phase2 · Operator ping (Telegram + Teams) + 'go' checkpoint",
     "P1. On a paid request, notify Sukaimi on BOTH Telegram AND Teams (so a missed Telegram is caught): 'New paid request — N-page <type>, SGD<X> paid. Reply go.' Operator 'go' (reply/command) releases the job to the engine. NOTHING builds or spends tokens before 'go'. Builder: Claude."),

    ("Phase2 · Client notifiers (build-started / delivered / feedback)",
     "P1. Automated emails to the client via msmtp: (a) build-STARTED ('we've started your <type>'), (b) DELIVERED ('ready: <URL>' or EDM .html + preview), (c) FEEDBACK request at close. All automatic — no per-send approval. Builder: Claude."),

    ("Phase2 · Token-economics guard (cheap pre-pay, deep Discovery post-go)",
     "P1. Enforce the split: pre-payment = near-zero cost (quote = declared pages x SGD10, NO vision/LLM calls). Deep multimodal Discovery + build only fire AFTER payment AND operator 'go'. Protects against burning tokens on unpaid/tire-kicker requests. Builder: Claude (wired into cc-intake + dispatch)."),

    ("Phase2 · Legal — T&C + Privacy (Code&Canvas), short essentials",
     "P2. Short, plain, essentials-only, under Code&Canvas (the legal entity). T&C: service scope (web/EDM, SGD10/page), payment (refundable before build 'go', non-refundable after), client provides + warrants rights to content/images, IP (client owns deliverable on full payment; Code&Canvas may showcase as portfolio), takedown-on-close + 3-month archive, liability cap, Singapore law. Privacy: data collected (form+uploads+contact), Stripe handles payment, processors (Stripe/Tally/Vercel/Pexels), 3-mo retention then purge, contact. DRAFT for Sukaimi review — NOT auto-published as binding. Linked in the landing footer. Builder: Claude drafts."),

    ("Phase2 · End-to-end dry run (Phase 2 acceptance gate)",
     "P0 / gate. One test request flows the WHOLE journey: arrive -> cap check -> Tally submit -> Stripe TEST pay -> operator pinged (TG + Teams) -> 'go' -> engine builds + deploys -> client delivered -> close. Gate-verified end to end. Passing = Phase 2 proven."),
]

tok = graph_token()
h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
url = "https://graph.microsoft.com/v1.0/sites/%s/lists/%s/items" % (SITE, LIST)
ok = 0
for title, notes in cards:
    body = {"fields": {"Title": title, "Stage": "Intake", "Notes": notes, "ProjectNo": PROJ}}
    r = requests.post(url, headers=h, data=json.dumps(body))
    good = r.status_code < 300
    ok += 1 if good else 0
    print(("OK  " if good else "FAIL"), r.status_code, "|", title[:58])
print("created", ok, "of", len(cards), "in", PROJ, "stage=Intake")
