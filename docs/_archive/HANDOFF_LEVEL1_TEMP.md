> **ARCHIVED 2026-06-14 — superseded; SP Phases A–C done + Level 2 closed (see [[project_sp_level2_access_model]]).** Current comprehensive SP record + forward backlog: `docs/handoffs/HANDOFF_HOMEPAGE_MIRROR.md`. Content below preserved for history.

# TEMP HANDOFF — SharePoint classic→modern conversion (Level 1 + hardening round)

_Live working doc. Survives /clear & /compact. Last updated 2026-06-11._
Deep detail also in memory: `project_sharepoint_team_deployed`, `project_sp_intake_flow`, `project_version_rollback_baseline`, `feedback_claude_sets_up_oc_runs`.

## Mission
OpenClaw O/C agent team performs **SharePoint classic→modern site conversions**. Claude's role = **set the team up to run independently + observe/tweak**, NOT build (see [[feedback_claude_sets_up_oc_runs]]).

## Access / infra
- Server: `sshpass -p "$CC_SP_PASS" ssh root@76.13.179.220` (srv1330842; password in `~/.codecraft/verify-watch.json`, NOT committed). Python: `/root/.openclaw/venv/bin/python`.
- Tools: `/root/.openclaw/sp-provision/*.py` + `/usr/local/bin/cc-*`. Config/cert: `/root/.openclaw/config.json` (app `OpenClaw-SharePoint-Agent`, Sites.Selected).
- Hub agent: **`main` → workspace `/root/.openclaw/workspace-delivery-lead`** (272-line prompt). 8 agents (main, product-manager, architect, full-stack-engineer, code-reviewer, qa-engineer, cybersecurity, devops-deploy) + workspace-technical-writer exists. Profile A (DeepSeek V4 via OpenRouter).
- Server `gh` authed (PAT — BURNED, in chat; rotate, see [[openclaw-keys-upgrade-todo]]).
- Visual QA: authed SP screenshots MUST run **Mac-side** (`~/Workspace2/OpenClaw/tools/cc-visual-qa`, `node qa.mjs <url> <out> --auth`; seed at `~/.codecraft/sp-storage-state.json`). Server-side authed shots FAIL (no session + Conditional Access) → 5KB login page. Ship the PNG to `/srv/projects/<JOB>/qa/`.

## Architecture LOCKED (2026-06-11)
- Each build = its OWN isolated site `/sites/CCBuild-<JOB>` in codeandcanvas tenant; cataloged by a Command Center **"Client Sites"** index list + QuickLaunch nav. NOT pages inside the Command Center; NOT the client tenant.
- Deliverable = classic→modern conversion. Human dev redeploys to client later (Level 2) via PnP template extract — autonomous flow NEVER touches a client tenant.
- Per-build site CREATE needs a 1-time admin device-code (app is Sites.Selected, can't create sites). Script: `/root/.openclaw/sp-provision/create_grant_buildsite.py` (creates+grants+writes site.json; also grant-only for a source site via `--role read`). It writes the device code to `/tmp/cc-device-code.txt` early → relay to operator.

## Intake (LIVE)
- SharePoint-native form = **"Intake Briefs"** list (Command Center) + **"Client Profiles"** + **"Client Sites"** lists. Field help/warnings set as column descriptions.
- Flow: form (Status=Approved + SignedOff ✓ = AUTO-RUN trigger) → `cc-intake-clarify` (Confirm-or-Call audit+questions) → `cc-intake-watch` (creates JOB in **Ready** gated, type=`sp_convert`) → dispatch. Orchestrator `cc-intake-autorun` (clarify→watch→dispatch). **CRON OFF** (run manually). cc-intake-watch does NOT copy site.json into the workspace — operator/step must `cp /root/.openclaw/sp-provision/sites/<JOB>.site.json /srv/projects/<JOB>/site.json`.

## Conversion harness (INSTALLED)
- `sp-audit.py <SOURCE_URL> --job <JOB>` → emits `/srv/projects/<JOB>/sp-expect.json` (pages + content markers). Has **SP-REST fallback** for classic sites whose pages live in a classic "Site Pages" library Graph drives don't expose (reads WikiField/CanvasContent1). Normalizes page-url→site-root.
- `cc-verify-sp <JOB>` (gate) → checks BUILD-site pages published + markers + a >5KB qa screenshot; PASS writes `.sp-verified`; `board_cli.py` refuses Closed for SP types without it. Gate reads `site.json.siteId` + `sp-expect.json`.
- `runbook-sp-convert.md` (engineer), `## DISPATCH-SP` block (delivery-lead).
- Backups: `*.bak-spgate-*`, `*.bak-convert-*`, `*.bak-sprest-*`, `*.bak-siteidfix-*`, `*.bak-spskip-*`, `*.bak-intake-*`, `*.bak-vqa-runbooks-*`, `*.bak-desilo-2026-06-11`.

## LEVEL 1 RESULT (JOB0022, Crestfield)
- Source: `https://codeandcanvas.sharepoint.com/sites/CrestfieldClassic` (classic STS; granted read). Build: `https://codeandcanvas.sharepoint.com/sites/CCBuild-0022` (siteId in `/srv/projects/JOB0022/site.json`).
- **PASSED the gate**: built modern Home.aspx with 8 content markers, `.sp-verified`. Board card now at **Internal QA**.
- **BUT 3 real gaps (the hardening round below).**

## Fixes already made during Level 1
1. sp-audit SP-REST fallback (classic-site read). 2. siteId `setdefault` gate bug → override-if-falsy. 3. `cc-verify-sweep` spammed JOB0022 (web gate on SP job) → added SP-skip + reset `.failcount`. 4. Mac-side authed QA (server shot was bogus login page; **gate's screenshot check is size-only = foolable, harden later**).

## ⏳ HARDENING ROUND — IN PROGRESS (3 subagents prep → /tmp/desilo/hardening/)
1. **Board management** — DISPATCH-SP must require explicit `cc-board move <JOB> "<stage>"` at EACH transition (Ready→Content Audit→…→Internal QA→Staging) + verify the move. Agents narrated cards but never moved the physical board card (it jumped Ready→Build).
2. **Technical Writer** — wire into SP flow: produce a human-readable **Content Audit doc** (like FARA) after the audit + a **handoff/redeploy doc** at the end, into `/srv/projects/<JOB>/docs/`. Writer agent exists but never ran.
3. **Image migration** — sp-audit captures source image refs (WikiField `<img>` + Site Assets) → build downloads + re-uploads to build-site assets → references in the modern page. Current conversion is TEXT-ONLY (0 images; brand imagery dropped).
- Prep artifacts land in `/tmp/desilo/hardening/{board,writer,images}/`. Claude installs to live under review (backups), then **re-run JOB0022** to validate (managed board + docs + images).
- Other follow-ups: make `cc-autocloseout`/`cc-notify-closed` SP-aware (they key on `.verified`, ignore SP jobs); migrate classic content LISTS too; lists-template filter in sp-audit; enable `cc-intake-autorun` cron for true hands-off; Power Apps form for a pre-save confirm dialog.

## Level 2 (not started)
Real client: read their classic site (their tenant) → build modern in our env → client reviews → human redeploys.
**⚠️ ACCESS MODEL CORRECTED 2026-06-12 — see "LEVEL 2 — ACCESS MODEL LOCKED" at the very bottom.** The app-consent / multi-tenant / Sites.Selected cross-tenant approach (and anything below about the Azure signInAudience flip, dev-tenant, Graph grants, `--tenant` plumbing) is **SUPERSEDED**: client source reads now use the interactive login-session method (FARA-style), needing NOTHING provisioned in the client tenant.

## HARDENING ROUND — INSTALLED 2026-06-11 (re-run validating)
All 3 fixes APPLIED to live agent prompts (`.bak-hardening-*`):
- **Board**: delivery-lead `## DISPATCH-SP` now requires `cc-board move`+read-back at every stage (BOARD = SOURCE OF TRUTH).
- **Writer**: 2 spawn points (content-audit.md after audit, handoff.md after verify); block added to `workspace-technical-writer/AGENTS.md`.
- **Images**: `sp-audit.py` emits `pages[].images[]`; `image_migrate.py` installed (downloads source imgs → uploads to build site **Documents**/`Migrated/<JOB>/` → `image-map.json`); runbook + DISPATCH-SP updated to migrate + emit `<img>`. **image_migrate.py fixes made:** site.json key=`siteUrl`, asset drive=`Documents` (comm site has no Site Assets drive), download URL targets the **source SITE web** (`/sites/<name>/_api`, not root — app grant is site-scoped). PROVEN: 5/5 Crestfield images migrated to CCBuild-0022.
- **Re-run**: JOB0022 reset to Ready + `.sp-verified` cleared; re-dispatched to validate board-trace + docs + images. **Authed QA screenshot still Mac-side** — operator runs `node qa.mjs <CCBuild-0022 Home> /tmp/x.png --auth` and ships to `/srv/projects/JOB0022/qa/` before the gate passes.

## PRE-LEVEL-2 HARDENING (2026-06-11, in progress)
- **#2a gate freshness DONE**: `cc_verify_sp.check_visual_qa` now needs a **>50KB** shot **newer than the run's sp-expect.json** (kills 5KB login pages + stale shots). Backup `.bak-qafresh-*`.
- **#1 cross-tenant DESIGNED** (`/tmp/desilo/crosstenant/`): Option A = app multi-tenant + client admin-consent + per-site Sites.Selected read; our cert auths against the CLIENT tenant (authority=client tenantId). Tooling param (`--tenant`, 2 chokepoints: `spclient.graph_token` + `sp-audit._sp_rest_token`, default=our tenant) PREPARED, **NOT applied** (apply AFTER the Azure change). Client review = B2B guest scoped to one CCBuild-<JOB>. **OPERATOR ACTION (gating, Azure portal): set app `83822d9d-...` signInAudience=AzureADMultipleOrgs (multi-tenant); confirm Sites.Selected survives.** Nothing cross-tenant works until then.
- **🔴 DATA-RESIDENCY GAP (must fix before a real client):** `cc_closeout.py` is Vercel-only — NO SharePoint build-site teardown. Client content/images in `CCBuild-<JOB>` are never purged. Need an SP build-site purge at closeout (delete the site or its content).
- **STILL OWED for #2:** prove the gate-pause -> client-review -> resume flow with a real run (don't pre-approve gates).

## DESIGN-QUALITY ROUND — DECISIONS (2026-06-12, agreed; build pending)
- **Copy fidelity DONE**: sp-audit captures full verbatim `content[]`; canvas_compose builds it 1:1; cc_verify_sp has a `check_copy_fidelity()` (>=0.9, FAILs lossy). JOB0022 copy=1.00. **canvas_compose.py is the new composer (multi-section + native Image web parts) — applied to JOB0022 but NOT yet wired into the build runbook (still calls create_page).**
- **NO new UI-designer seat** — the existing **`ux-designer`** ("UX/Brand Designer", registered) spans UX+UI. The gap was it got BYPASSED on runs. Fix = ENGAGE it in Wireframes/Design + give it a **SharePoint Design Playbook** (2026 best practices: hero top, news above fold, <=8 quick links, white space + section backgrounds, mobile-first single-column, native web parts).
- **Composer upgrade**: use native web parts (Hero, Quick Links, News) executing the ux-designer's design.
- **Video = YES but judicious** (Embed/File-viewer web part + Pexels VIDEO api; ux-designer decides placement, e.g. hero; NOT auto-injected; sparing on 1:1 conversions, more on enrichment/greenfield).
- **Immersive-for-SP = PARKED** (SharePoint resists bespoke/immersive; that's the separate web/immersive rail = JOB0019 + 12x12 lib, also parked). SP ceiling = polished modern intranet.
- **Nav migration = YES** (source top nav `Home/Corporate Sites/Functions/Region-Country Sites/Search` readable via SP REST; each build site nav is ISOLATED -> zero cross-project impact).
- **Still PARKED for real Level 2** (separate track): cross-tenant source access (needs OPERATOR Azure action: app signInAudience=AzureADMultipleOrgs) + tooling `--tenant` apply; gate-pause/client-review flow test; **data-residency teardown (cc_closeout is Vercel-only — no SP build-site purge)**.

## DESIGN-QUALITY ROUND — VALIDATED 2026-06-12 (JOB0022 upgraded re-run)
Full upgraded flow ran end-to-end (Claude re-kicked across the spawn-and-yield): board moved every stage → **ux-designer produced a real design-spec.json** (hero/news/text/quicklinks/events) per DESIGN-PLAYBOOK → **canvas_compose built NATIVE web parts** (Hero/News-grid/Quick Links/Image/Text; beta endpoint) to the spec → **nav_migrate** (5 top nodes + the one real "News" QuickLaunch; SP-defaults dropped; dedup fixed; dupes cleaned) → gate PASS (fidelity 0.93, fresh Mac shot) → board auto-advanced Internal QA→Staging. News section now a clean 3-col card grid (was the cramped complaint).
- **Composer/audit/gate/nav all wired into DISPATCH-SP + runbook** (canvas_compose REPLACES create_page; image_migrate + nav_migrate in the BUILD step; ux-designer spawned at Wireframes/Design). Backups `.bak-designwire-*`, `.bak-webparts-*`, `.bak-navfix-*`, `.bak-playbook-*`.
- **Copy = faithful** (build 2112 chars > source 2039; 0.93 is REORDERING not loss) EXCEPT the **footer dropped** (©/Internal Use Only/Managed by Corporate Comms/last-updated) — design-spec had no footer section. TODO: add a footer to DESIGN-PLAYBOOK so every design keeps it.
- **SP SUPERVISOR BUILT (DISABLED): `/usr/local/bin/cc-dispatch-loop-sp`** + `sp_dispatch_helper.py` + uninstalled cron/systemd spec at `/root/cc-dispatch-loop-sp.cron.spec`. Targets sp_convert jobs, gate=cc-verify-sp, skips GATE-PAUSED/BLOCKED/Closed, one card/tick, exits when idle. Enable (after JOB0022 settled, verify `--dry` first): cron `*/5 * * * * root /usr/local/bin/cc-dispatch-loop-sp >> /var/log/cc-dispatch-sp.log 2>&1` OR the systemd timer. Recommended 5-min cadence. **NOT enabled — Sukaimi's call (token cadence).**
- Video web parts (Embed/File-viewer + Pexels video) BUILT in canvas_compose, used only when design-spec calls for it (JOB0022 hero stayed image per playbook).

## ============================================================
## CURRENT STATE — resume here (updated 2026-06-12, before /clear)
## ============================================================

### Where we are: Level-1 SP conversion quality round — essentially DONE, in final visual polish on JOB0022 (CrestfieldClassic -> CCBuild-0022).

**The full upgraded conversion pipeline is built, wired, and validated end-to-end:**
intake form -> auto-JOB (sp_convert) -> dispatch -> board moves every stage -> **ux-designer** produces `design-spec.json` (per DESIGN-PLAYBOOK) -> **engineer**: `image_migrate.py` -> `canvas_compose.py` (NATIVE web parts to the spec, VERBATIM copy) -> `nav_migrate.py` -> **technical-writer** content-audit.md + handoff.md -> `cc-verify-sp` gate (pages + copy-fidelity >=0.9 + fresh >50KB Mac-side authed screenshot) -> board auto-advances. All wired into `## DISPATCH-SP` (delivery-lead AGENTS.md) + `runbook-sp-convert.md`.

**JOB0022 latest build = GOOD.** Gate PASS, **fidelity 0.97**, 15 web parts, at stage **Staging**. Iterated through operator feedback:
- v1 cramped single-text-web-part -> v2 verbatim heuristic -> v3 ux-designer design-spec + native web parts (News 3-col grid) -> v4 fixed 4 defects -> **v5 (latest): native page-title header IS the hero**.
- **Fixes now baked into reusable tooling + playbook:** (a) HERO = native page-title-area (Graph **beta** PATCH titleArea, layout `imageAndTitle`, MUST set BOTH `imageWebUrl` AND `serverProcessedContent.imageSources[].value`), company-led title `Crestfield Foods International — Global Intranet Portal`, brand image as background, NO separate hero web part. (b) Sidebar de-dup. (c) Nav: comm sites render the menu from the **quicklaunch/Current** store NOT topnavigationbar — `nav_migrate.py` now routes top nav to quicklaunch on comm sites; SP-default QL links dropped; dedup fixed. (d) Footer = full-width Text web part (verbatim), now a playbook rule. (e) Gate QA check hardened (>50KB + newer-than-audit). (f) Copy-fidelity gate (>=0.9). 
- Latest screenshot: `/tmp/job0022-v5-hero.png` (local; title confirmed company-led via qa.mjs). Live: https://codeandcanvas.sharepoint.com/sites/CCBuild-0022/SitePages/Home.aspx

### OUTSTANDING (minor, immediate): BOTH DONE 2026-06-12
1. ~~Final visual confirm of v5~~ **DONE** — full-page authed shot confirms clean hero, nav, News 3-col grid, sidebar (no dupes), and **footer present** (© 2026 · Internal Use Only · Managed by Corporate Communications · Last updated 12 Jan 2026; verified visually + text markers). Latest: `/tmp/job0022-qa-verify.png`.
2. ~~Rename the build SITE~~ **DONE** — renamed to plain **"CCBuild-0022"** via SP REST `POST /_api/web` MERGE `{"Title":"CCBuild-0022"}` (HTTP 204; read-back confirms). Also updated cached `displayName` in `/srv/projects/JOB0022/site.json`. Browser chrome now reads "CCBuild-0022".
3. **qa.mjs full-page fix** — SP modern pages scroll inside an inner region so `fullPage:true` only grabbed the first viewport (1000px). Fixed in `tools/cc-visual-qa/qa.mjs`: measure content scrollHeight → grow viewport to match before screenshot → genuine full-page capture (was 1000px, now 2534px on JOB0022). Gate's screenshot check is no longer viewport-clipped.

### FARA ABSORPTION — DECIDED + SCOPED + PLANNED (2026-06-12)
The SP pipeline's content-audit deliverable is being upgraded from the thin prose `content-audit.md` to FARA's real **3-sheet .xlsx Content Tracker** (intent-drop fix: "like FARA" had shipped as a narrative, not the structured artifact). **Decided:** absorb FARA's engine into the pipeline → then decommission + archive standalone FARA. Scope = **engine only** (no UI); **engine-first, then retire**. Full direction in memory `project_fara_absorb_into_sp_pipeline`; scoping in `/tmp/fara-absorb-scoping.md`.
- **Key insight:** do NOT absorb FARA's scanner (Playwright, interactive auth) — keep `sp-audit.py` (Graph+app-cert, unattended) as the feed. Absorb only FARA's `excel-generator.js` (exceljs, de-branded Node CLI) + net-new enrichers into sp-audit.py (DPI, broken-links, asset taxonomy, freshness, migration-status).
- **Migration-status = ADVISORY flags only; build always migrates verbatim.** Migrate (default) / Review (broken-link, low-res, garbled) / Archive (stale >12mo) / Rewrite (undated time-sensitive).
- **Splice:** delivery-lead AGENTS.md:269 — emit `docs/content-tracker.xlsx` augmenting content-audit.md; gate stays on sp-expect.json (non-gating phase 1). **Surface:** build-site Documents lib + board-card link; Command Center Project Archive at closeout; NOT client-facing by default.
- **Decommission surface (after proven):** docker `fara-backend-1` (3001), `*/5` git-poll cron, nginx `fara.codeandcraft.ai` vhost. 🔴 `/opt/fara` git remote embeds a live GitHub PAT — rotate/scrub.
- **STATUS: TRACK 1 DONE + LIVE (2026-06-12).** Cloud /ultraplan branch never pushed (no remote in ephemeral container) → Claude rebuilt + tested the engine locally, deployed to server, and wired it into the live pipeline. LIVE: `sp-audit.py` now emits `enrich.json` (broken-links + measured image dims); `cc-sp-tracker <JOB>` generates the 3-sheet `docs/content-tracker.xlsx` + uploads to the build-site Documents library; spliced into delivery-lead AGENTS.md (line ~269) + engineer runbook; gateway restarted. Validated on JOB0022 (31 assets, 25 Migrate/5 Rewrite/1 Review[low-res CEO img]; xlsx surfaced to CCBuild-0022 Documents). Engine at `/root/.openclaw/sp-provision/sp-content-tracker/`; helper `sp_audit_http.py`; backups `.bak-fara-20260612-133202`. **TRACK 2 (kill standalone FARA) DEFERRED ~1 week** — Sukaimi will trigger + check ~2026-06-19; FARA stays up till then. **PAT rotation DROPPED** per Sukaimi (don't re-raise).

### IMMEDIATE POLISH — ALL DONE (2026-06-12)
v5 visual confirm ✓ (full clean page incl. footer) · site renamed to `CCBuild-0022` ✓ · `qa.mjs` full-page-capture fix ✓ (was viewport-clipped at 1000px; now grows viewport to content height → gate screenshots no longer clipped). See the "OUTSTANDING (minor, immediate): BOTH DONE" block above.

### BIG-PICTURE OPEN DECISIONS (Sukaimi's call):
- **Enable the SP supervisor?** Built + dry-tested + DISABLED: `/usr/local/bin/cc-dispatch-loop-sp` (+ `sp_dispatch_helper.py`, spec `/root/cc-dispatch-loop-sp.cron.spec`). Makes SP runs hands-off (no Claude re-kicks). Enable via cron `*/5 * * * * root /usr/local/bin/cc-dispatch-loop-sp >> /var/log/cc-dispatch-sp.log 2>&1` (verify `--dry` first). Off due to token-cadence concern.
- **Level-2 PREREQUISITES (parked, separate track, for a REAL client):**
  1. **Cross-tenant source access** — needs OPERATOR Azure action: set app `83822d9d-4ce3-4b8f-b1dd-93161b69279f` `signInAudience=AzureADMultipleOrgs` (multi-tenant). Then per-client admin-consent + Sites.Selected read. Tooling `--tenant` param PREPARED (`/tmp/desilo/crosstenant/`), NOT applied (apply after the Azure flip). Client review = B2B guest scoped to one CCBuild-<JOB>.
  2. **Gate-pause -> client-review -> resume flow** UNTESTED (we pre-approved gates on the dogfood).
  3. **Data-residency teardown** — `cc_closeout.py` is Vercel-only; NO SP build-site purge. A real client's content sits in CCBuild-<JOB> forever. Must build an SP teardown before a real client.
- Lower-priority: make cc-autocloseout/cc-notify-closed SP-aware; migrate classic content LISTS; context-mode MCP broken (better-sqlite3 ABI — `ctx upgrade`/npm rebuild).

### KEY GOTCHAS for next context:
- Authed SP screenshots = Mac-side ONLY (`OpenClaw/tools/cc-visual-qa`, `node qa.mjs <url> <out> --auth`; seed at `~/.codecraft/sp-storage-state.json`); ship PNG to `/srv/projects/<JOB>/qa/`. Server-side authed shots fail (CA).
- Bash commands containing `requests.get(` are BLOCKED by the context-mode hook — put HTTP python in a FILE + scp + run, don't inline.
- SP supervisor NOT running; Claude has been hand-driving re-kicks (`openclaw agent --agent main --message "..."`). main agent -> workspace-delivery-lead.
- GitHub PAT (server gh) is BURNED (pasted in chat) — rotate.

## ============================================================
## LEVEL 2 — ACCESS MODEL LOCKED (2026-06-12)  ← authoritative; supersedes all app-consent cross-tenant notes above
## ============================================================

**Core correction:** reading a CLIENT's classic site uses **interactive delegated browser-session auth** (the proven FARA / `cc-visual-qa` Playwright storage-state method: login popup → human authenticates → session captured), NOT app-only cross-tenant. Enterprises refuse to admin-consent a third-party app into their directory; the login popup needs NOTHING in the client tenant and is client-familiar. App-cert (`graph_token`/`_sp_rest_token`) stays ONLY for writes into OUR tenant (building CCBuild sites).

**Verify-at-intake (Sukaimi's UX, locked):** the intake form's `URL` field gets a **"Verify"** button. Verify = O/C capture-runner (Mac) opens the login popup → human authenticates → confirms access AND does the FULL source capture while the session is hot (pages + raw `WikiField`/`CanvasContent1` + nav + image binaries) → writes `AccessVerified ✓` back to the intake record. **Form submit is BLOCKED until verified.** One human login total; the JOB build later consumes the capture bundle (no second login, no session-expiry risk).

**Flow:**
```
intake URL + [Verify] → popup login → capture/ bundle + AccessVerified✓ (submit gated)
  → JOB(sp_convert) → ux-designer → engineer build (canvas_compose + upload captured
    images + nav_migrate) → writer → cc-verify-sp gate → [card PAUSES for CLIENT REVIEW
    via #2 pause/resume] → resume on sign-off → done → #3 content-wipe teardown
```

**Design decisions:**
- Capture pulls **raw `WikiField`/`CanvasContent1` verbatim** (keeps the ≥0.9 copy-fidelity gate meaningful); **DOM-scrape fallback** if a tenant blocks `_api`. (Q2 = best-practice.)
- **Operator-driven intake first** — the popup renders on the operator's Mac (capture-runner host); they authenticate with the client-provided login / screen-share the client through it. **Remote-client self-serve DEFERRED** (popup-reaches-Mac model breaks; different capture host needed — do NOT solve now).
- `#2` pause/resume (built + proven) is repurposed for the **post-build client-review gate**, not the source login. `#3` content-wipe teardown (built, gated `CC_SP_PURGE` off) unchanged & still needed.

**DROPPED (do not pursue):** Azure multi-tenant `signInAudience` flip (do NOT save that dropdown), dev-tenant signup, Graph per-site grants, admin-consent. The `--tenant` app-cert plumbing added during the wrong turn (5 files: `spclient.py`, `cc_provision_intake.py`, `sp-audit.py`, `image_migrate.py`, `nav_migrate.py`; backups `.bak-tenant-20260612-061825`) is now dead — **REVERT it** (inert today since it defaults to our tenant, but clean it up).

**BUILD LIST (NOT yet implemented — awaiting Sukaimi greenlight):**
1. NEW thin Mac-side `cc-sp-capture <SOURCE_URL> --job <JOB>` (login popup → pull raw pages/nav/images → `capture/` bundle → ship to `/srv/projects/<JOB>/capture/`). Model on `tools/cc-visual-qa/qa.mjs` (already auths via `~/.codecraft/*-storage-state.json`).
2. NEW Power Apps–customized intake form: `Verify` button → Flow/webhook → capture-runner → `AccessVerified` writeback + submit-gate. (This is the previously-noted "Power Apps pre-save dialog", now with a concrete purpose.)
3. `sp-audit.py --from-capture <dir>` — parse the captured raw locally (reuse ALL existing parsing/normalization/enrichment; no server-side auth).
4. Point `image_migrate.py` upload at `capture/images/`; retire the app-cert source *download* half.
5. Revert the `--tenant` edits (#5 above).

Memory: `project_sp_level2_access_model` (locked); related `project_sp_intake_flow`, `project_fara_absorb_into_sp_pipeline`.

### IMPLEMENTED 2026-06-12 (capture spine + supervisor)
- **`tools/cc-visual-qa/cc-sp-capture.mjs`** (Mac, NEW): `node cc-sp-capture.mjs <SRC_URL> --job <JOB> [--login] [--out <dir>] [--state <p>]`. Login popup (`--login`, persists session) or seeded headless. Authed `context.request` reads the Site Pages library (FileLeafRef/Title/WikiField/CanvasContent1), nav (topnav+quicklaunch), non-hidden lists, and downloads every `<img>` binary → `capture/` bundle (`manifest.json`, `pages/*.html`, `images/*`, `images-map.json`, `nav.json`).
- **`sp-audit.py --from-capture <dir>`**: `load_capture()` feeds the bundle into the SAME parsing/markers/segmentation; `enrich_from_capture()` measures image dims from local files + broken-link HEAD (no auth). Backup `.bak-fromcapture-*`.
- **`image_migrate.py --from-capture <dir>`**: upload half reads `capture/images/` by src (no app-cert source download). Backup `.bak-fromcapture-*`.
- **PROVEN (CrestfieldClassic):** from-capture sp-expect.json byte-identical to a fresh app-cert read (sourceText 2039==2039, markers equal, 8==8 blocks). The on-disk JOB0022 expect was STALE (9 blocks) — live source is 8; both readers agree. 5/5 images mapped + dims measured.
- **`--tenant` reverted** on spclient.py / cc_provision_intake.py / nav_migrate.py (`.pretrevert-*` saved). sp-audit.py + image_migrate.py keep an INERT `--tenant` (bypassed by from-capture) — strip later if desired.
- **SP SUPERVISOR ENABLED:** `/etc/cron.d/cc-dispatch-sp` → `*/5 * * * * root /usr/local/bin/cc-dispatch-loop-sp >> /var/log/cc-dispatch-sp.log 2>&1`. cron active. **JOB0022 PARKED** (`cc-board pause`, status=Staging GATE-PAUSED) so the showcase isn't churned; `cc-board resume JOB0022` to reactivate. Supervisor drains clean (all jobs Closed/BLOCKED/GATE-PAUSED → exits).

- **`tools/cc-visual-qa/cc-verify-watch.mjs`** (Mac, NEW — task 5a, BUILT+PROVEN): polls a SERVER queue `/srv/verify-queue/<id>.json {itemId,url}` (the Mac↔server rendezvous; Mac takes no inbound), runs cc-sp-capture (headless w/ per-client session, else `--login` popup), ships bundle → `/srv/intake-captures/<id>/`, writes `<id>.result.json {ok,pages,images}`. Creds from `~/.codecraft/verify-watch.json` (600, NOT committed) or env CC_SP_HOST/USER/PASS. `--once`/`--interval N`. PROVEN: TEST1 CrestfieldClassic → queue→capture→ship→`sp-audit --from-capture` parsed clean (2 pages, 5 imgs, 8 lists). Run: `node cc-verify-watch.mjs` (operator keeps it running on the Mac).

### LEVEL-2 READINESS (2026-06-12)
**Pipeline is staged + proven SAME-TENANT.** Decision: **B first (manual real-client run), then A (automate the form).** B is blocked ONLY on a real foreign site + a login (the client gives a read account/guest, or operator does the popup). Cross-tenant capture = built but never run against a FOREIGN tenant (just standard M365 sign-in; low risk, unproven). NOTE: a throwaway dry-run is now trivial — the interactive model needs NOTHING provisioned in the other tenant (no app-consent/Azure), just a site + a login — so any free 2nd M365 tenant can play "client" to prove the foreign-tenant popup + full flow before a paying client.

### RDQ PILOT LAUNCHED — JOB0023 (2026-06-12, self-driving)
First REAL cross-tenant Level-2 conversion, running autonomously via O/C. Source: Mondelez `intranet.mdlz.com/sites/RDQ` (authorized engagement; safe TEST site). **3 representative publishing pages** captured (`Is This the Simplest Way`, `Innovation is the Key to Success`, `Building Superior Consumer Brand Value`) — chosen because RDQ's real content is a 482-page publishing archive + list-driven homepage + subsites (out of scope for v1). Build target `CCBuild-0023` (our tenant). Staged at `/srv/projects/JOB0023/` (capture/ + sp-expect.json + enrich.json + site.json + brief.json type=sp_convert). DISPATCH-SP made **capture-aware** (delivery-lead AGENTS.md: if `capture/` exists → `sp-audit --from-capture` + `image_migrate --from-capture`, SKIP nav_migrate; backup `.bak-capaware-*`).
- **Capture-aware CONFIRMED working:** dispatched live, board auto-moved Ready→Content Audit, content-tracker.xlsx + content-audit.md generated, sp-expect.json untouched (used from-capture, no app-cert 403). Agent picked up the edited AGENTS.md.
- **Supervisor IS live** (the `DRY=1` in cc-dispatch-loop-sp logs is a cosmetic bug: `${DRY:+ DRY=1}` is truthy for "0"; real default DRY=0=live). Cron `*/5` drives the rest.
- **Quality caveat:** these publishing pages have NO semantic h1-h3 → segment_content makes 1 'intro' block each → build will be copy-FAITHFUL but visually FLAT (one text web part/page). Plus 4 broken links + mojibake (legacy 2013-era). Acceptable for pilot.
- **DELIVERED + REFINED 2026-06-12:** all 3 pages built on CCBuild-0023, gate PASS, **copy-fidelity 1.00**. Claude did a one-time push (fix/verify the demojibake normalizer, drive the per-stage gates, take the authed QA shots — our tenant so headless seed works). **Design refine:** `canvas_compose.py` was hero-ing the intro's first image in TWO places (content Image web part via `_img_for` + native titleArea background via `derive_title_hero`) → the 159px Jean Spence signature blew up as a giant doubled hero. FIXED at source (backup `.bak-herofix-*`): `_IMG_DIMS`/`_FEATURE_MIN_W=400` loaded from `enrich.json`; `_img_for` + `derive_title_hero` skip <400px images (stay inline only); `set_title_area_hero` uses `colorBlock` (no image) when no feature image. Systemic — every future job benefits. Rebuilt 3 pages → clean colour-band header + verbatim body; gate re-passed 1.00. JOB0023 parked at Staging GATE-PAUSED. Minor leftover: title duplicated in colorBlock header + body `<h1>`; signature now inline-only.
- **(superseded) NEXT OPERATOR STEP:** it will pause at the Internal QA gate needing a Mac-side authed QA screenshot of CCBuild-0023 — run `cd tools/cc-visual-qa && node qa.mjs <CCBuild-0023 Home.aspx> /tmp/x.png --auth` → ship to `/srv/projects/JOB0023/qa/`. Then gate can PASS → client-review pause.

### STILL TODO (Level-2 intake wiring)
- **Task 5b — Power Apps Verify button + submit-gate** (operator/portal) + **server enqueue/reconcile**: on Verify, write `/srv/verify-queue/<itemId>.json` + flip the list to Processing; read the watcher's `result.json` → set `AccessVerified ✓`/failed + unblock submit; on submit, `cc-intake-watch` moves `/srv/intake-captures/<itemId>/` → `/srv/projects/<JOB>/capture/` (JOB association). NONE of this server glue is built yet.
- **`nav_migrate --from-capture`** (read bundled `nav.json`) for real cross-tenant clients — capture already produces nav.json; nav_migrate still reads nav via app-cert (fine same-tenant, breaks cross-tenant).
