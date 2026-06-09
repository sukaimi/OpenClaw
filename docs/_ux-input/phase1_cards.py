#!/usr/bin/env python3
# Phase 1 — Web/EDM Build Engine. Creates JOB0003 cards in Intake. Does NOT start build.
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

SITE = "codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a"
LIST = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
PROJ = "JOB0003"

cards = [
    ("Engine · Job workspace + type taxonomy + intake schema",
     "P0 / foundation. Define the per-job record the whole engine writes into: a JOB#### folder/record holding (a) raw client materials in, (b) Discovery manifest, (c) build artifact out. Lock the type taxonomy: sp_project | multipage_site | single_page | edm | needs_backend(flag). Everything downstream keys off the job's `type`. No build logic yet — just the schema + storage layout."),

    ("Engine · Request router / classifier (Telegram+Teams intake)",
     "P0. Front-door triage: classify an incoming brief into the taxonomy. Confident -> confirm type in one line; ambiguous -> ask 1-2 clarifying Qs; ALWAYS lock `type` before any build. Detect needs_backend and flag to human (no silent half-build). Drives which downstream rail loads. Phase 1 intake = existing channels only (no web form yet)."),

    ("Engine · Discovery — vision pass on images",
     "P1. For each supplied image, run a vision model -> structured descriptors: subject, role (logo|hero|product|background|icon), orientation, aspect ratio, focal point, contains_text y/n, usable_as_background y/n. Output = per-asset JSON. This is the deep/expensive pass — in production it runs POST-payment (Phase 2 gate); Phase 1 runs it on hand-fed briefs to prove it."),

    ("Engine · Discovery — copy parse",
     "P1. Parse supplied copy into structure: tone, hierarchy, sections, headline/body/CTA per section. For EDM also capture sender name, subject line, preheader, CTA URL. Output = structured copy JSON. Structured copy (not one blob) is what makes the UIUX layout clean."),

    ("Engine · Discovery brief / asset manifest assembler",
     "P1. Merge the image + copy passes into ONE Discovery brief (manifest JSON) that the build bot consumes. Flag gaps: missing hero, weak/low-res asset, section with no image -> mark needs_gapfill so the asset bots can fill. This manifest is the contract between Discovery and Build."),

    ("Engine · Asset gap-fill — Pexels (stock)",
     "P2. When Discovery flags a needs_gapfill stock-type slot, pull candidate images from Pexels API (commercial use, no attribution required). Needs PEXELS_API_KEY — PROMPT the operator, do not set silently. Output = candidate images written into the manifest slot."),

    ("Engine · Asset gap-fill — Higgsfield (generated/branded)",
     "P2. For bespoke/branded assets Pexels can't cover, generate via Higgsfield. Use when the slot needs something specific (brand hero, custom illustration). Output = generated images into the manifest slot. Division of labour: Pexels=real stock, Higgsfield=generated."),

    ("Engine · Build rail — static web (multipage + single page)",
     "P1. From the Discovery brief, build a static site via the frontend toolchain (frontend-design / Stitch / shadcn). Multipage vs single-page is SCOPE, same rail. No backend. Output = static build artifact ready to deploy."),

    ("Engine · Build rail — EDM (email HTML)",
     "P1. Separate lane — email is NOT a small website. 600px table layout, inline CSS only, no JS, Outlook/Word-engine + dark-mode safe. From the Discovery brief. Output = single .html email file."),

    ("Engine · Deploy — Vercel (web)",
     "P1. Deploy the static build to OUR Vercel account; return a preview URL. Production promotion stays GATED behind approval/payment (Phase 2). Sites are taken down on project close per retention policy (Phase 3)."),

    ("Engine · Deliver — EDM output",
     "P1. Produce final EDM deliverable: .html file + rendered screenshot, optional test-send via msmtp. No hosting — EDM is an artifact, not a deployed site."),

    ("Engine · End-to-end dry run (Phase 1 acceptance gate)",
     "P0 / gate. Hand-feed ONE sample web brief + ONE sample EDM brief through router -> Discovery -> build -> deploy/deliver. Confirm the engine produces a real, good deliverable end to end. Passing this proves Phase 1 before we expose the paid web form (Phase 2)."),
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
    print(("OK  " if good else "FAIL"), r.status_code, "|", title[:60])
print("created", ok, "of", len(cards), "in", PROJ, "stage=Intake")
