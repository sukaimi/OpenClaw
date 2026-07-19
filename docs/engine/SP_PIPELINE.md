# Runbook — SharePoint CLASSIC → MODERN Conversion Rail (Graph / spclient.py)

_The engine of **SPARK v1** (SharePoint Autonomous Rebuild Kit) — the live headline rail. All 10
agents run **DeepSeek V4** (Profile A `deepseek-v4-flash` / `deepseek-v4-pro`)._

**Audience:** the OpenClaw engineer agent, loaded per-job by the delivery-lead when a job is a
SharePoint **conversion** (`brief.json.type: sp_convert` / `sharepoint`).
**Replaces** `runbook-sp-pages.md` for conversion jobs. (The greenfield pages runbook built
fixed Northwind pages from a brief; this runbook DERIVES the deliverable from an existing
classic source site.)

**Golden rule:** the deliverable is a **MODERN SharePoint site that rebuilds an existing
CLASSIC source site**. You AUDIT the source, then REBUILD an equivalent modern site in the
**assigned isolated build site** via Microsoft Graph using `spclient.py` — run **on the VPS**.
There is **no build host, no CI, no `.sppkg`, no app catalog, and NO Vercel** on this rail.
Deploy target = the **isolated build site**, never Vercel, never the Command Center, never
another tenant.

**Level 1 (this rail):** source classic site + isolated build site both live in **our
codeandcanvas tenant**. The operator supplies the classic **source URL** as a parameter.
**Level 2** (deploy the built modern site into the client's own tenant) — a **manual dev handover**,
not an automated step; see section 9 below and `docs/engine/SP_CLIENT_TENANT.md`.
Requires the client admin to grant `Sites.Selected` write (or SCA) on their target site (one-time).

Toolkit: `/root/.openclaw/sp-provision/spclient.py` → `from spclient import SP`. App-cert auth
(Sites.Selected), scoped to BOTH the source site (read) and the build site (write).

---

## ORCHESTRATOR — use `cc-sp-mirror` (do NOT chain the scripts by hand)

The whole pipeline is now driven by one config-driven orchestrator. Per job:

1. `cc-sp-config <JOB>` -> writes `/srv/projects/<JOB>/job.config.json` from brief+site+sp-expect (sourceUrl, targetSite, pages, buildCap, heavyWebpartCap, styler).
2. **Operator full-run (Mac):** `cc-sp-mirror --config /srv/projects/<JOB>/job.config.json [--dry-run] [--from <stage>]`

Full 17-stage pipeline (in order):

| Stage | Where | Script | Output |
|---|---|---|---|
| verify-access (×2) | mac + server | cc-sp-capture.mjs --probe / cc_preflight_sp.py | source readable + target writable |
| capture (×3) | mac | cc-sp-capture.mjs / cc-sp-manifest.mjs | capture bundle + site-inventory.json + per-page manifests |
| audit | server | sp-audit.py | sp-expect.json (pages + lastModified + content markers) |
| **scorer** | server | cc_sp_scorer.py | **sp-scored.json** (Tier 1/2/3 + priority\_score per page) |
| **notify** | server | cc_sp_notify_plan.py | **Teams ping** with tier breakdown — informational, no gate |
| image-migrate | server | image_migrate.py | image-map.json |
| **compose** | server | cc_sp_batch_runner.py | pages built in tier order, batches of 10; exceptions logged |
| compose (home) | server | sp_home_compose.py | Home.aspx built |
| style | server | cc-sp-styler-attach.py | wallpaper + brand applied |
| verify (×N) | mac | cc-completeness-gate.mjs | qa-verdict-\<label\>.json per page |
| tracker | server | cc-sp-tracker.py | content-tracker.xlsx (Sheet 1 sorted by Tier/Priority) |
| **handover** | server | cc_sp_handover.py | **sp-handover-summary.json + Teams handover ping** |
| closeout | server | cc_closeout.py | archive + client email + card Closed |

Resume from a stage: `--from <stage-name>` (e.g. `--from scorer` to re-score without re-capturing).
Dry-run to print the full plan: `--dry-run`.

What the orchestrator guarantees (built into `canvas_compose.py` / `cc_sp_batch_runner.py`):
- **Tier-ordered execution** — pages are built Tier 1 first (homepage + recently-modified high-traffic pages), Tier 2 next, Tier 3 last. Client always receives the most important pages first.
- **Non-fatal exceptions** — a failed page is logged to `sp-exceptions.json` and skipped; the runner never aborts the whole job. Exceptions surface at handover.
- **Source-of-truth reconciliation** — build images AND text are merged from the live-capture manifest so the gate matches even when sp-audit under-captured.
- **Three safety nets** (marker / content / image) — every source marker, every `content[]` body block, and every content image lands on the page.
- **Per-page completeness gate** (`cc-completeness-gate.mjs`) diffs the BUILT page's web-part JSON vs the source manifest; fail-closed. You can NEVER self-close.

The sections below document the underlying scripts (reference / debugging). You normally only run the two commands above.

---

## 0. Mental model (the whole conversion pipeline)

```
operator supplies SOURCE classic URL + assigned BUILD site (site.json.siteId)
   ->  AUDIT:   sp-audit.py          reads source via Graph/SP REST
   ->                                EMITS sp-expect.json (pages + lastModified + content + lists)
   ->  SCORE:   cc_sp_scorer.py      tiers pages by importance -> sp-scored.json (T1/T2/T3)
   ->  NOTIFY:  cc_sp_notify_plan.py Teams ping with tier breakdown; O/C proceeds immediately
   ->  BUILD:   cc_sp_batch_runner.py  Tier-ordered batches of 10 via canvas_compose.py
   ->                                  exceptions logged to sp-exceptions.json (non-fatal)
   ->           sp_home_compose.py   homepage built separately
   ->  GATE:    cc-completeness-gate.mjs  per-page diff vs source manifest -> qa-verdict-*.json
   ->  TRACKER: cc-sp-tracker.py     content-tracker.xlsx (Sheet 1 sorted by Tier/Priority Score)
   ->  HANDOVER:cc_sp_handover.py    sp-handover-summary.json + Teams handover ping
   ->  CLOSEOUT:cc_closeout.py       archive + client email + card Closed
```

Source = READ-only. Build target = the assigned isolated build site (via Graph). Two human
touchpoints only: intake form submission + handover sign-off. Zero mid-job gates.

---

## 0a. INTAKE TRIGGER LAYER (before the engineer is ever loaded)

Everything above starts only once a JOB exists. That handoff was built (2026-06-11) but never
actually wired end-to-end — closed 2026-07-12, all fixes verified live (not assumed). Full write-up:
[[project_sp_intake_automation_fix]] memory. Scripts: `/root/.openclaw/sp-provision/` on the server
(no git remote there — edited live via SSH; `.bak-*` files left next to each changed script).

```
client/operator fills "Intake Briefs" SP list -> cc_intake_autorun.py (cron, */5 * * * *)
   -> CLARIFY hop: cc-intake-clarify + cc-intake-notify ("Awaiting Sign-off" ping)
   -> client SignedOff + operator Status=Approved -> cc-intake-notify ("Approved" ping)
   -> AccessVerified=="Verified" gate (see below) -> cc-intake-watch (JOB + Ready card)
   -> auto-dispatch delivery-lead (`openclaw agent ... --deliver --channel last`)
```

What was broken and fixed: (1) no cron ever existed for `cc_intake_autorun.py` specifically — the
one prior success (JOB0022, 06-11) was a manual run, before the `AccessVerified` gate (added 06-14)
even existed; (2) `cc-intake-notify` existed but nothing called it — wired in, idempotent via
`_intake_notify_state.json`; (3) `AccessVerified` for item 6 was set from a real, manually-run check
(never faked) — the server app-cert has no grant on client tenants, so source-site read access is
checked **Mac-side** via
`node tools/cc-visual-qa/cc-sp-capture.mjs <source> --job <id> --probe --state ~/.codecraft/verify-<host>.json`
(per-host delegated session; `verify-codeandcanvas.sharepoint.com.json` covers own-tenant sources);
(4) `item_web_url()`'s Graph `webUrl` is broken for this list (downloads instead of rendering) — now
constructs `DispForm.aspx?ID=<id>` directly; (5) the dispatch call was missing `--deliver`, so any
question the delivery-lead asked (e.g. model profile) never reached any channel — fixed, confirmed
via a live `deliverySucceeded: true` response.

**⚠️ STILL OPEN — the "Verify" button path is silently broken, cause unconfirmed.** There is a
SEPARATE, older automated verify system (`cc_verify_bridge.py`, cron `/etc/cron.d/cc-verify-bridge`
every 3 min, built + "live-proven" 2026-06-14 per [[project_sp_level2_access_model]]) that's
supposed to do step (3) above automatically: operator clicks "Verify" on the form
(`VerifyRequested=true`) → bridge enqueues → Mac launchd worker (`cc-verify-watch.mjs`, manually
loaded per session) captures → bridge reconciles → `AccessVerified=Verified`. Item 6 had
`VerifyRequested=True` set from creation and matched every enqueue condition in
`cc_verify_bridge.py` (checked the source — filter is `VerifyRequested truthy AND AccessVerified !=
Verified AND has SourceSiteURL AND not already queued`), yet was **never enqueued** — no
`/srv/verify-queue/6.json` ever appeared, `AccessVerified` sat empty (not even "Pending", which the
enqueue step should have set). The cron IS active (`systemctl is-active cron` = active) and DOES
process other items (log shows real enqueue/reconcile activity for items 1 and 5) — so this isn't a
dead cron, something is item-6-specific or timing-specific that wasn't root-caused before this
session ended. **Before the next real client intake, verify this path actually works** — don't
assume the manual Mac-probe workaround used for item 6 is the normal path; it was a workaround for
a bridge that appears to have quietly stopped working for at least this one item.

**Sukaimi's explicit call (2026-07-12): keep auto-dispatch as-is** — JOB creation immediately
dispatches the delivery-lead; it is NOT operator-gated pending a manual step, despite older
"operator-gated" wording in the original design doc. That stale wording was corrected everywhere
(notify message, Kanban card Notes, docstrings).

**Not yet live-fired**: the "Awaiting Sign-off" notify checkpoint (today's test item was already
Approved when work started) — only code-reviewed + idempotency-tested, not exercised for real.

**One more gap found + fixed same day:** getting a JOB *created* isn't the same as getting it
*built*. `cc-dispatch-loop-sp` — the supervisor that re-invokes the delivery-lead for each
subsequent stage (Content Audit → Content Architecture → Wireframes → …) — was disabled a month
ago (`/etc/cron.d/cc-dispatch-sp` didn't exist; the script itself, `/usr/local/bin/cc-dispatch-loop-sp`,
was untouched). JOB0026 correctly finished its first card ("do ONE card then STOP" is by design)
and then sat idle forever with nothing to re-invoke it. Re-enabled per Sukaimi's explicit call
(`*/5 * * * *`) — the script itself is unchanged and already safe: one card per tick, and it does
NOT auto-advance past real client gates (content/wireframes/design/staging pause with
`GATE-PAUSED:`, wait for operator).
Sukaimi's requested UAT = submit one brand-new form untouched and watch the whole chain fire.

---

## 1. AUDIT the source classic site (DO THIS FIRST — it derives the deliverable)

Run `sp-audit.py <SOURCE_SITE_URL> --job <JOB>`. It resolves the source site id, reads its
pages + lists via Graph, and writes `/srv/projects/<JOB>/sp-expect.json`. **You build to that
file** — it is the contract the gate enforces. The audit also emits `enrich.json` beside it
(broken-link HEAD checks + image natural dimensions, best-effort — never blocks the audit).

After the audit, the **delivery-lead** runs `cc-sp-tracker <JOB>` (Content-Audit step) to emit the
3-sheet **Content Tracker** `docs/content-tracker.xlsx` from `sp-expect.json` + `enrich.json` and
surface it to the build site's Documents library. The tracker's per-asset migration status
(Migrate/Review/Archive/Rewrite) is ADVISORY — **you still migrate every `content[]` block verbatim**;
the tracker never changes what you build or what the gate checks.

**What the audit can read from a CLASSIC source (capability verdict — read this):**

| Source artifact | Graph path | Readable? | Notes |
|---|---|---|---|
| Modern SitePages | `/sites/{id}/pages` + `$expand=canvasLayout` | yes | Returns ONLY modern pages. A purely-classic source returns empty here. |
| Classic wiki/web-part pages | `'Site Pages' drive` → `.aspx` items → `/content` | yes (as HTML) | Server-rendered `.aspx` markup; NOT canvasLayout JSON. Content extracted as text/HTML. |
| Classic publishing pages | `'Pages' drive` → `.aspx` items → `/content` | yes (as HTML) | Only if publishing infra enabled; same HTML-extraction caveat. |
| Lists & libraries | `/sites/{id}/lists` + `/items` | yes | Classic + modern lists are the same Graph resource. Recorded for migration. |
| QuickLaunch / top nav | (Graph v1.0: not exposed) | no | Reconstructed from the page set; SP REST `/_api/web/navigation` out of scope for the app cert. |
| Publishing page LAYOUTS / managed metadata / web-part config | — | no (structured) | Available only as rendered HTML. Faithful rebuild, NOT a byte-for-byte web-part clone. |

So the audit captures **page names + titles + visible TEXT-content markers + list names** —
enough for a faithful modern rebuild and a deterministic gate. If the source exposes neither
`/pages` nor a readable page-library drive (locked-down CA / missing grant), `sp-audit.py`
EXITS NONZERO — escalate the Sites.Selected/Read grant for the source site; do NOT proceed
with an empty gate.

**Review the emitted markers** before building — the audit's marker heuristic (title + longest
distinctive phrases) is a starting point; tighten any noisy markers so the gate is meaningful.

**`lastModified` is now captured** — all 4 read paths (modern pages, classic drive, SP REST,
capture bundle) emit a `lastModified` ISO timestamp per page into `sp-expect.json`. The scorer
uses this for recency signals; it does NOT affect gate logic.

---

## 1b. BATCH MANAGEMENT — Large Sites (>10 pages)

Sites with >10 pages are handled **fully autonomously**. No mid-job human gate. Default mode:
**Priority-first** (O/C decides migration order; client reviews at handover only).

### How it works

**Phase 1 — Score** (`cc_sp_scorer.py`):
Reads `sp-expect.json`, scores every page, writes `sp-scored.json`.

Scoring signals:
- `is_homepage` — Home.aspx / Default.aspx always Tier 1, priority 100
- `inbound_links` — count of other pages referencing this page's name in their content
- `days_since_modified` — from `lastModified`; recent = higher priority
- `source_text_len` — content volume proxy

Tier logic:
| Tier | Criteria |
|---|---|
| T1 | homepage OR (inbound ≥ 2 AND modified ≤ 180 days ago) |
| T2 | inbound ≥ 1 OR modified ≤ 365 days ago |
| T3 | everything else (orphans, archive, low-traffic) |

`complexity_flag = True` when `len(webparts) > 5` OR `sourceTextLen > 8000`.

**Phase 2 — Notify** (`cc_sp_notify_plan.py`):
Sends a Telegram + Teams message with the tier breakdown immediately after scoring.
Message includes T1/T2/T3 page counts + titles (first 5 per tier). O/C proceeds without waiting
for a reply — if the client wants to change the order, they reply to Teams and it's handled as a
manual exception at the operator level.

**Phase 3 — Batch Runner** (`cc_sp_batch_runner.py`):
- Reads `sp-scored.json`; filters out homepage (handled by `sp_home_compose.py`)
- Applies `buildCap` limit (same as `--build-cap` in compose)
- Splits into batches of 10, Tier 1 first
- For each batch: runs `canvas_compose.py --pages <batch>`, catches non-zero exit, logs
  failed pages to `sp-exceptions.json` with reason — NEVER aborts the whole job
- After each batch: Teams progress ping `"📦 [JOB] Batch N/M complete. [E exceptions so far]"`
- Always exits 0 — exceptions surface at handover, not mid-run

Exception log: `<jobDir>/sp-exceptions.json`
```json
{ "exceptions": [{ "name": "Page.aspx", "reason": "compose failed (batch 2)", "batch": 2 }] }
```

**Phase 4 — Handover** (`cc_sp_handover.py`):
Runs after the tracker, before closeout. Reads sp-scored.json + sp-exceptions.json + qa-verdict-*.json.
Writes `sp-handover-summary.json` and sends a Teams ping:
```
✅ [JOB####] Handover Summary — <sourceUrl>
Migrated: N pages | T1: N | T2: N | T3: N
Exceptions (needs review): N — see Content Tracker
Deferred (low-priority, not migrated): N pages
Target: <targetSite>
```

### Artefacts produced

| File | Produced by | Consumed by |
|---|---|---|
| `sp-scored.json` | cc_sp_scorer.py | cc_sp_notify_plan, cc_sp_batch_runner, cc-sp-tracker, cc_sp_handover |
| `sp-exceptions.json` | cc_sp_batch_runner.py | cc_sp_handover |
| `sp-handover-summary.json` | cc_sp_handover.py | closeout / operator |

### Resuming after a partial run
If the batch runner is interrupted mid-job:
- `sp-exceptions.json` already has the failed pages logged
- Resume from compose: `cc-sp-mirror --config ... --from compose`
- The batch runner re-reads `sp-scored.json`; already-built pages are idempotent (canvas_compose
  PATCHes an existing page rather than failing on a name collision)

---

## 2. What `create_page` can actually do (constrains the REBUILD — honest limitation)

`spclient.SP.create_page(name, title, inner_html, page_layout="article", publish=True)`:

- Emits **exactly ONE web part per page**: a `#microsoft.graph.textWebPart` whose `innerHtml`
  is the `inner_html` string you pass, inside a single **one-column** section (`_text_canvas`).
  It then POSTs the page and (publish=True) calls `microsoft.graph.sitePage/publish`
  (v1.0 → beta fallback).
- It does **NOT** place real OOTB web parts — no Quick Links, no list/library view web part,
  no hero, no multi-column canvas.

**Conversion consequence (state this honestly in the deliverable):** a classic source page that
had multiple web-part zones / columns is migrated as **ONE rich-text web part per modern page**:
all of the source page's visible content is rebuilt as **structured HTML** (`<h2>`, `<ul>`,
`<table>`, `<a>`…) inside that single text web part. Layout fidelity is approximate; **content
fidelity is the contract** (every marker the audit captured must appear). For a classic LIST,
use `create_list(...)` + `create_item(...)` to recreate a genuine modern list (the gate's
optional `check_lists` verifies it exists) — but the page can only *link* to it, not embed a
list-view web part. Do NOT claim an OOTB web part you cannot provision; the gate reads the
canvas back and a faked claim FAILS.

---

## 3. REBUILD on the assigned isolated build site (engineer steps, on the VPS)

Run with the openclaw venv and `PYTHONPATH=/root/.openclaw/sp-provision`. Point `SP` at the
**assigned BUILD site** (NOT the Command Center default, NOT the source) via `site.json`:

```python
import json
from spclient import SP

site = json.load(open("/srv/projects/<JOB>/site.json"))      # the assigned BUILD site
sp = SP(site_host="<build-host>.sharepoint.com", site_path="/sites/CCBuild-<JOB>")
assert sp.site_id() == site["siteId"]    # the gate uses site.json.siteId; they MUST match
```

Then, **driven by `sp-expect.json`** (the source audit output), for each `pages[]` entry build
the modern equivalent so every `markers[]` string appears verbatim in that page's `inner_html`:

```python
expect = json.load(open("/srv/projects/<JOB>/sp-expect.json"))
for pg in expect["pages"]:
    inner_html = build_modern_html(pg)        # rebuild source content as structured HTML;
                                              # MUST contain every pg["markers"] string verbatim
    sp.create_page(pg["name"], pg["title"], inner_html, publish=True)

for lst in expect.get("lists", []):
    sp.create_list(lst["name"], COLUMNS_FOR(lst))   # recreate migrated lists (optional but verified)
```

Every marker is the contract — present verbatim (case-insensitive) in the page's web-part HTML.
Carry brand/palette in the page theme + HTML. **Hero image:** `cc-assets` (optional, nice for QA).

---

## 4. Deploy = Graph provisioning on the BUILD site (NOT Vercel)

There is no separate deploy step and **no Vercel** on this rail. `create_page(..., publish=True)`
IS the deploy: the modern page is live + published on the **isolated build site** the moment the
call returns 201 and the publish action succeeds. Confirm `sp.site_id() == site.json.siteId`
before provisioning — provisioning to the wrong site (source, Command Center, or another tenant)
is the #1 failure here.

---

## 5. REGISTER the build in the Command Center 'Client Sites' index

After a clean build, upsert a row so the build appears in the Command Center "Client Sites"
left-nav index (one row per build, linking into the isolated build site):

```python
from client_sites_index import add_build_row
add_build_row("<JOB>", {
    "Client": "<client>", "SourceURL": expect["sourceUrl"],
    "BuildSiteURL": "https://<build-host>.sharepoint.com/sites/CCBuild-<JOB>",
    "Status": "Internal QA", "ReviewLink": "<review link>"})
```

(The QuickLaunch nav item itself is one-time; see `client-sites-index.py` NAV CAVEAT + NOTES.)

---

## 6. The 3 verify points (what `cc-verify-sp` proves — agent cannot fake)

The deterministic gate is **`cc-verify-sp <JOB>`** (conversion rail). It reads the
**source-derived** `/srv/projects/<JOB>/sp-expect.json` (BUILD siteId injected from `site.json`)
and asserts, live via Graph against the **BUILD site**:

- **Verify point 1 — Pages exist + published.** Every `pages[].name` (derived from the source)
  exists on the BUILD site (`/sites/{buildSiteId}/pages`) and `publishingState.level ==
  "published"`. A draft page FAILS.
- **Verify point 2 — Migrated content present.** Each page's canvas is fetched back
  (`/sites/{buildSiteId}/pages/{id}/microsoft.graph.sitePage?$expand=canvasLayout`); the gate
  confirms the expected web-part **type** (`textWebPart`, `min` count) AND that **every
  `markers` string** (content carried over from the source) appears in the page's web-part HTML.
- **(Optional) Migrated lists.** If the audit recorded `lists[]`, each named list must exist on
  the BUILD site (`check_lists`). Skipped when no lists were derived.
- **Verify point 3 — Visual-QA screenshot.** A real (>5KB) PNG/JPG exists under
  `/srv/projects/<JOB>/qa/` (from `cc-visual-qa`; for authed SP may be produced Mac-side and
  copied in — the gate only checks the file exists).

PASS → writes `/srv/projects/<JOB>/.sp-verified`, moves the card (Internal QA→Staging, or
Production→Closed), pings the operator. FAIL → removes the marker, bounces the card to Build
(BLOCKED on 2nd consecutive fail), pings with reasons. `cc-board` hard-refuses Closed for an SP
job without `.sp-verified`. Manual dry run: `cc-verify-sp <JOB> --check-only` (exits 0/1).

---

## 7. Common CONVERSION failure modes → recovery

| Symptom | Likely cause | Recovery |
|---|---|---|
| `sp-audit.py` exits 3 "no readable pages on source" | Source is classic but the page-library drive isn't readable / no grant | Grant Sites.Selected (read) for the SOURCE site; never broaden tenant-wide. |
| Gate: "page missing on build site" | Provisioned to the source/Command Center, not the build site | `SP(site_host=…, site_path=/sites/CCBuild-<JOB>)`; assert `sp.site_id() == site.json.siteId`. |
| Gate: "migrated content missing markers" | The source content wasn't carried into `inner_html` (or wording drifted from the audit) | Put every `sp-expect.json` marker verbatim into the page HTML; the markers ARE the contract. Re-run the audit if the source changed. |
| Gate: "page not published" | `publish=False` or publish action 4xx'd | Re-run with `publish=True`; check `publishingState`. |
| Markers too noisy / wrong | Audit heuristic picked boilerplate | Hand-tighten `sp-expect.json` markers after the audit (review step), then build. |
| Provisioning 403 | Build site not granted to the app (Sites.Selected write) | Escalate to devops to grant THAT specific build site. |

---

## 8. Escalation rules (when the agent must stop and ask)

- Any **403 / permission** failure on source READ or build WRITE → escalate to devops with the
  exact site URL and the missing Sites.Selected grant. Never broaden app permissions yourself.
- Source exposes **no readable pages** → STOP; report which library/grant is missing.
- If a faithful conversion truly needs **real OOTB web parts / custom interactivity** → that is
  the **SPFx rail** (`runbook-sp-build.md`), a later milestone. `create_page` cannot do it.
  Flag it; do not fake an OOTB part inside a text web part.
- Wrong build site / missing `site.json` → STOP, tell Sukaimi; never guess the target site.

---

## 9. Level 2 — Client-Tenant Deployment

After the build is gate-verified in the C&C build tenant, the client receives it in their own
SharePoint tenant. This is **not** an automated pipeline step — it's a **manual dev handover**:
the client reviews via screenshare, and on approval a C&C developer deploys the pages into the
client tenant (Graph-native page recreate + image migration + branding; no PnP `.sppkg`).

**Sole owner of the how-to: `docs/engine/SP_CLIENT_TENANT.md`** — the full dev handover guide
(access grant, page recreation with `@odata.*` strip, image migration, branding, verify, and the
canvasLayout export reference). Do not duplicate those steps here.

---

## Relationship to the other runbooks

- `runbook-sp-pages.md` (greenfield fixed-brief pages) is **superseded by this file** for
  conversion jobs.
- `runbook-sp-build.md` (SPFx → CI → `.sppkg` → app catalog) is **NOT** used on this rail; it is
  the later custom-code milestone. This conversion rail ships with zero CI and zero catalog,
  using only Graph provisioning the team already has.


## IMAGE MIGRATION -- carry the source's brand/logo imagery

The audit now captures each page's `images[]` ({src, filename, alt}) from the classic source's WikiField/CanvasContent1 `<img>` tags. `create_page` accepts inner HTML INCLUDING `<img>`, so the modern page CAN show the original imagery -- but the `<img src>` must point at an asset on the BUILD site (the source server-relative URL is the wrong tenant/path).

Run the migrator BEFORE rebuilding pages:

    PYTHONPATH=/root/.openclaw/sp-provision /root/.openclaw/venv/bin/python \
        /root/.openclaw/sp-provision/image_migrate.py --job <JOB>

It downloads each `images[].src` from the source (app READ, SP REST), uploads each to the build site's **Site Assets** library under `Migrated/<JOB>/<filename>`, and writes `/srv/projects/<JOB>/image-map.json` (`_map`: old-src -> new build URL). Idempotent.

Then, building each page's inner HTML, REWRITE the `<img src>` before create_page:

    import json
    from importlib import import_module
    im = import_module("image_migrate")
    image_map = json.load(open("/srv/projects/<JOB>/image-map.json")).get("_map", {})
    for pg in json.load(open("/srv/projects/<JOB>/sp-expect.json"))["pages"]:
        inner_html = build_modern_html(pg)                 # rebuild source content as structured HTML
        inner_html = im.rewrite_img_src(inner_html, image_map)   # point <img> at build assets
        # inner_html MUST contain every pg["markers"] verbatim AND SHOULD show each pg["images"][].filename
        sp.create_page(pg["name"], pg["title"], inner_html, publish=True)

The build is NO LONGER text-only: it MUST emit `<img>` tags for the migrated images. If a source image fails to download (`image-map.json` detail status `download-failed`), STOP and check the Sites.Selected READ grant on the SOURCE -- do not ship a page with a dead image src.

---

## MODERN COMPOSER + NATIVE WEB PARTS -- the polished build path

The page REBUILD (sec 3) is now done by **`canvas_compose.py`**, which authors a real modern
`canvasLayout` (multi-column sections + NATIVE web parts) instead of one stripped text blob. Run it
AFTER the image migrator, per page:

    PYTHONPATH=/root/.openclaw/sp-provision /root/.openclaw/venv/bin/python \
        /root/.openclaw/sp-provision/canvas_compose.py --job <JOB> --page Home.aspx

It reads `/srv/projects/<JOB>/sp-expect.json` (`content[]` verbatim copy + `images[]`),
`image-map.json` (migrated URLs), and `site.json` (build site), recreates+publishes the page, and
self-reports `COPY_COVERAGE` + `STRUCTURE_OK`. Then run the gate: `cc-verify-sp <JOB> --check-only`.

### Build priority (composer picks automatically)
1. **`/srv/projects/<JOB>/design-spec.json`** present -> build EXACTLY that (the ux-designer's
   ordered sections/web parts). This is the polished path.
2. No design-spec -> **heuristic auto-layout** from `content[]` (hero image + main/sidebar + news grid).
3. Oldest audits with no `content[]` -> legacy marker layout.
Force the fallback with `--no-spec`; point at an explicit spec with `--spec <path>`.

### Native web parts now supported (verified shapes; empirically tested on CCBuild-0022)
- **Hero** (`c4bd7b2f-...`) -- full-width banner (title + tagline + image; image by default).
- **Quick Links** (`c70391ea-...`) -- link list (<=8; titles/urls in serverProcessedContent; overflow noted).
- **Image** (`d1d91016-...`) -- native image web part (as before; CEO portrait, news cards).
- **Embed** (`490d7c76-...`) / **File and media / File viewer** (`b7dd04e1-...`) -- VIDEO, judicious only.
- **News** stays the clean image-card grid (a true News web part needs real news posts -> out of scope).

**Graph endpoint:** Hero / Quick Links / Embed are accepted ONLY on the **beta** pages endpoint
(v1.0 returns "not supported in current version of API"). `apply_page` auto-prefers beta when those
parts are present; File viewer + Image work on both. **Quick Links gotcha:** a `properties.items`
array of objects makes Graph 400 ("Parsing JSON Light resource sets ... without entity set") -- so
links are carried ENTIRELY in `serverProcessedContent` (searchablePlainTexts=titles, links=urls).

### VIDEO (judicious -- never automatic; see DESIGN-PLAYBOOK sec 4)
Only added when a design-spec section requests it (`"video": {"query": "..."}` or `{"url": "..."}`).
The composer searches the **Pexels VIDEO api** (reuses `PEXELS_API_KEY` from
`/root/.openclaw/secrets/cc-secrets.env`, same as `cc_assets`), downloads an mp4, uploads it to
`Documents/Migrated/<JOB>/`, and renders it via File viewer (or Embed). Hero defaults to an image; do
NOT inject stock video into a faithful conversion.

### design-spec.json schema (the ux-designer produces this; composer builds it 1:1)
```jsonc
{ "page": "Home.aspx",
  "sections": [
    { "layout": "fullWidth|oneColumn|twoColumns|threeColumns|oneThirdLeftColumn|oneThirdRightColumn",
      "emphasis": "none|neutral|soft|strong",
      // top-level shorthand = one column, OR an explicit "columns": [ ... ]
      "columns": [
        { "webpart": "hero|quicklinks|text|image|news|embed|fileviewer",
          // hero:       "title","tagline","image":{"src"|"url","alt"},"link"
          // text:       "contentBlocks":["<kind>",...]  (pull content[] blocks VERBATIM) | "blocks":[{heading,html}] | "html"
          //             optional inline "image":{"src"|"url","alt","caption"}
          // quicklinks: "links":[{title,url,description}]  OR  "fromBlock":"quicklinks","limit":8
          // image:      "image":{"src"|"url","alt","caption"}
          // news:       "fromBlock":"news"   (-> clean image-card grid, becomes its own sections)
          // embed/fileviewer (VIDEO): "video":{"query":"pexels terms"} | {"url":"<hosted mp4>","fileType":"mp4"}
        } ] } ] }
```
`contentBlocks` reference `sp-expect.json` `content[]` entries by `kind`
(intro/welcome/news/quicklinks/documents/events/contacts/brands/section). The composer pulls their
EXACT html so copy fidelity stays 1.00. A **marker safety net** folds any source `markers[]` not
otherwise present (e.g. the page-title "Home") into the hero's accessible text so the gate's marker
check still passes.

### Verified on JOB0022 (2026-06-12)
Hand-authored a design-spec exercising Hero(image) + News grid + Quick Links(8) + Image(4) + verbatim
text across 5 sections. Result: `cc-verify-sp JOB0022 --check-only` -> **PASS**, copy fidelity **1.00**,
8/8 markers, 13 web parts, published. Fallback (`--no-spec`) also PASS (4 sections, fidelity 1.00).
Video (Embed + File viewer with a Pexels mp4) was render-tested on a scratch page then removed --
JOB0022's hero stays an image per the playbook.
