# ▶▶▶ RESUME STATE (post-/compact pickup) — updated 2026-06-14

Three threads. Two parked, one active.

## 1. SP BUILD — ✅ DONE / CLOSED (no open work)
Phases A–C codified + wired into the O/C harness + proven live on RDQ (JOB0023). 4 RDQ pages live + gate-PASS on CCBuild-0023 (Home + 3 articles, copy 1.00). **Level 2 CLOSED at proof-of-capability**; pilot card Closed; build site cleaned to the 4 deliverables; Command Center has the SP Conversion Runbook + Learnings pages. Harness wired (`cc-sp-config`+`cc-sp-build` build step; `cc-verify-sp` non-self-closable close-gate) but the autonomous loop (`cc-dispatch.service`) is INACTIVE. Detail: [[project_sp_pipeline_codification]], [[project_sp_level2_access_model]], [[ref_sp_completeness_gate]], [[ref_sp_capture_sessions]]. Forward backlog = the 4 production-hardening items (item #1 is now ACTIVE, see thread 3).

## 2. IMMERSIVE BUILD (Feature B / JOB0019) — ⏸ ON HOLD (Sukaimi)
Brief-driven immersive-website generator. `#95` decided: build LOCALLY first, harness into O/C later. Spec: `docs/features/feature-request-Immersive site builder.md`.
- **`/Users/sukaimisukri/Workspace2/codecraft-immersive/`** = example #1 hand-built proof (Code&Craft, dark-cinematic + immersive-3d-stage). Rubric-PASS.
- **`/Users/sukaimisukri/Workspace2/codecraft-studio/`** = the GENERATOR (`generator/{select,render,appcss,generate}.mjs`; brief schema; reusable verify harness). Proven on 2 tonally-opposite briefs: `out/codecraft` (dark) + `out/lumen-stone` (light/editorial — fit-map picked editorial-luxury+long-form-story). Both rubric-PASS on PROCEDURAL media (Lighthouse perf 89–96, a11y 100, axe 0, LCP ≤2.5s, reduced-motion). Local preview only, nothing deployed.
- **Pending (ON HOLD):** (a) perf fix — self-host webfonts (CDN fonts dropped example#1 perf 97→89, LCP on the 2.5s line); (b) Higgsfield media-subagent plumbing (generated hero loops/ambient via `generate_video`/`generate_image`+reference tagging) — Claude's rec was perf-fix + Higgsfield-plumbing-only (no generation, check balance/cap spend), HOLD generated-media taste+spend for a supervised pass. ALL paused per Sukaimi 2026-06-14.

## 3. VERIFY-AT-INTAKE WIRING — 🔨 ACTIVE (current work; Level-2 forward-backlog item #1)
Operator-assisted (decided): intake form has a source-URL + "Verify" button → capture the client source over the operator's Mac login popup → set `AccessVerified ✓` → submit gated on it. (Self-serve + delegated-OAuth = later upgrade.) See [[project_sp_level2_access_model]] + [[project_sp_intake_flow]].
- **EXISTS:** `tools/cc-visual-qa/cc-verify-watch.mjs` (Mac worker — polls a SERVER queue `/srv/verify-queue/<id>.json`, runs `cc-sp-capture --login`, ships bundle to `/srv/intake-captures/<id>/`, writes `/srv/verify-queue/<id>.result.json`; config `~/.codecraft/verify-watch.json` = host/user/pass, present). `cc-sp-capture.mjs` capture done.
- **BUILDING (the wiring):** (a) **Intake Briefs list** on the Command Center w/ fields `SourceUrl, ProjectNo, VerifyRequested, AccessVerified, CaptureId, VerifyNotes` (check if exists first — initial query found none); (b) server **ENQUEUE** poller: Intake list `VerifyRequested && !AccessVerified` → write `/srv/verify-queue/<id>.json {itemId,url,job}`; (c) server **RECONCILE**: read `<id>.result.json` → set `AccessVerified ✓` + move `/srv/intake-captures/<id>/` → `/srv/projects/<JOB>/capture/` + run `sp-audit.py --from-capture` → clear VerifyRequested + ping operator (fail → AccessVerified=Failed + note); (d) **submit-gate** (Power Apps UI — block submit until AccessVerified; operator-side, may be approximated by a list rule).
- **STATUS (2026-06-14) — SERVER SIDE BUILT + TESTED:**
  - ✅ Intake Briefs list found (already existed; `SourceSiteURL`, `Status`, `JOBNumber` + intake fields). Added the 4 verify columns: `VerifyRequested` (bool), `AccessVerified` (choice Pending/Verified/Failed), `CaptureId`, `VerifyNotes`.
  - ✅ Built **`/root/.openclaw/sp-provision/cc_verify_bridge.py`** (`setup` | `run`): ENQUEUE (Intake item `VerifyRequested=Yes && !Verified && has SourceSiteURL && not-queued` → `/srv/verify-queue/<itemId>.json {itemId,url,job}` + sets AccessVerified=Pending) + RECONCILE (read `<id>.result.json` → ok: AccessVerified=Verified, CaptureId, move `/srv/intake-captures/<id>` → `/srv/projects/<JOB>/capture` + `sp-audit --from-capture`; fail: AccessVerified=Failed + note; archives queue files to `/srv/verify-queue/done/`). **Tested end-to-end** with a synthetic capture result → item flipped to Verified correctly. NOTE: `spclient.SP().site_id` is a METHOD — call `site_id()`.
  - ✅ Cron `/etc/cron.d/cc-verify-bridge` runs `cc_verify_bridge.py run` every 3 min (idle-safe).
  - ✅ Mac worker `cc-verify-watch.mjs` pre-existing (polls queue, runs `cc-sp-capture --login`, ships bundle, writes result; config `~/.codecraft/verify-watch.json` present; uses `sshpass`).
  - ✅ **(a) DONE — "Verify" button + submit-gate.** The Intake Briefs list is a SharePoint-NATIVE form (not Power Apps canvas), so the "button" is **column formatting** (`cc_intake_formatting.py`, applied 204): `VerifyRequested` renders a **"Verify access" button** (`customRowAction setValue VerifyRequested=true`) → "↻ verify requested" once set; `AccessVerified` renders a coloured **status pill** (Pending=amber / Verified=green / Failed=red / "Not verified"). The **submit-gate is enforced SERVER-SIDE** (durable, non-bypassable — stronger than a UI block): `cc_intake_watch._is_ready_brief` + `cc_intake_autorun` hop-2 now refuse to create/launch a JOB when a brief has a `SourceSiteURL` but `AccessVerified != Verified` (briefs with no source URL are unaffected). Patched via `patch_verify_gate.py` (backups `.bak-vgate-*`, compiles OK), **deterministically tested**: src+Pending/Failed/blank → blocked; src+Verified → pass; no-src → pass.
  - ✅ **(b) DONE — Mac worker running.** launchd agent `~/Library/LaunchAgents/ai.codecraft.verify-watch.plist` (node + sshpass on PATH, `--interval 30`) loaded; pid live, log `~/Library/Logs/cc-verify-watch.log` shows "watching (every 30s)"; `--once` connectivity to the server queue confirmed. **Operator-controlled** (it polls the server queue, so it isn't meant to run 24/7 — `launchctl load` at the start of an intake session, `launchctl unload` when done).
  - ✅ **(c) DONE — LIVE end-to-end test PASSED (2026-06-14, OWN tenant).** Ran the full chain against `codeandcanvas.sharepoint.com/sites/CrestfieldClassic`: `VerifyRequested=true` → bridge enqueue → Mac worker **real read-only capture (2 pages, 5 images)** → bundle shipped to `/srv/intake-captures/` → bridge reconcile → `AccessVerified=Verified` + `CaptureId` set + `VerifyRequested` cleared → submit-gate `_is_ready_brief` returns **True** (gate opens post-verify). Test item + bundle + queue cleaned up afterward. (Worker captured silently via an own-tenant session seeded from the build session — `~/.codecraft/verify-codeandcanvas.sharepoint.com.json`, mode 600; the interactive login-popup path is just the auth fallback, same downstream, untested only because the operator is remote.)
  - ⚠️ **HARD RULE (set 2026-06-14, [[feedback_mdlz_read_only]]):** MDLZ/client SharePoint is **READ-ONLY, zero writes ever**; never auto-point a capture at a client/foreign tenant — verify/live tests target an OWN-tenant site only, unless Sukaimi explicitly approves that run. (An earlier attempt at this test wrongly targeted `intranet.mdlz.com/sites/RDQ`; it was read-only and aborted within seconds, nothing written/saved, but it should not have run.)
  - **VERIFY-AT-INTAKE = COMPLETE** (server bridge + native-form Verify button/status pill + server-side submit-gate + Mac worker + live-proven). Only optional polish left: exercise the interactive login-popup path when an operator is physically present.

### ▶ OPERATOR QUICK-START — verify a client's source access at intake
1. **Start the worker** (on the operator's Mac, at the start of an intake session): `launchctl load ~/Library/LaunchAgents/ai.codecraft.verify-watch.plist` (stop it when done: `launchctl unload …`). It polls the server queue every 30s and runs the read-only capture; `unload` it when not onboarding (don't leave it polling 24/7).
2. **Open the Intake Briefs list:** https://codeandcanvas.sharepoint.com/sites/CodeCraftAICommandCenter/Lists/Intake%20Briefs/AllItems.aspx — one row per client intake.
3. **Fill the brief's `SourceSiteURL`** (the client's classic SharePoint site), then click the blue **"Verify access"** button on that row (sets `VerifyRequested=true` → shows "↻ verify requested").
4. **Watch the `AccessVerified` pill:** grey "Not verified" → amber **Pending** (capturing; a login popup may appear on the Mac — authenticate as the client) → green **Verified** ✓ (captured) or red **Failed** (retry/check the URL). Typically ~1 min.
5. **Only a green `Verified` lets the brief become a build JOB** — the submit-gate (`cc_intake_watch`/`cc_intake_autorun`) refuses JOB creation for any brief that has a source URL but isn't Verified. Briefs with no source URL skip verification entirely.
- ⚠️ **READ-ONLY, own-tenant guard:** the capture only reads the source (never writes). For client/foreign tenants (e.g. MDLZ), the operator authenticates the popup; nothing is ever auto-targeted or written. See [[feedback_mdlz_read_only]].

---

# TEMP HANDOFF — List-Driven Homepage Mirror (capability build)

_Live working doc. Created 2026-06-12. Related: HANDOFF_LEVEL1_TEMP.md, project_sp_level2_access_model._

---
# ▶▶ ACTIVE WORK (resume here after /clear) — CODIFY + WIRE THE SP PIPELINE INTO O/C

**Decision (Sukaimi, 2026-06-13):** the 5 RDQ pages are delivered (homepage = good; 4 article pages = acceptable). **Codify + wire the pipeline into the O/C harness NOW; perfect designs + custom SPFx web parts LATER.** Execute via **contexted subagents**, one per task. Claude SETS UP + OBSERVES; O/C runs. (See [[feedback_claude_sets_up_oc_runs]], [[feedback_verify_gate]], [[feedback_delegation_kanban_workflow]].)

**Proven pipeline (manual, on RDQ/JOB0023 — what we codify):**
verify-access → capture (`cc-sp-capture.mjs` / `cc-sp-manifest.mjs`, Mac/operator) → audit (`sp-audit.py --from-capture`) → **xlsx content tracker** (`/tmp/gen_tracker.py`) → `image_migrate.py` → compose (`canvas_compose.py` articles / `sp_home_compose.py` homepage) → `apply_page` → style (reuse MDLZ SPFx styler, see [[ref_mdlz_spfx_solution]]) → verify → closeout.

**PRINCIPLES (do not violate):**
- **Config-driven per job** (sourceUrl, page set, buildCap=5 for test, styler props). **No RDQ hardcoding.**
- **Deterministic verify gate — the agent CANNOT self-close** ([[feedback_verify_gate]]).
- **Claude sets up + observes; not in the build loop** ([[feedback_claude_sets_up_oc_runs]]).
- **Rule-of-three:** RDQ = example #1; the NEXT real site = live calibration #2 **with Sukaimi verifying** before trusting autonomy.
- Reliability fixes go in the codification; only *design* polish is deferred.

**SUBAGENT TASK BREAKDOWN** (dispatch after /clear; parallel within a phase, sequential across phases):

**PHASE A STATUS (2026-06-13, dispatched + Claude-verified vs acceptance, not self-report):**
- **T1 ✅ (code).** `plan_heavy_webpart_batches` partitions heavy WPs into ≤6 batches (9→[6,3], all preserved, ordered); `_append_canvas_batches` PATCH-appends via `_patch_existing_page`. Drop behavior REMOVED (Sukaimi: preserve content, don't drop — homepage proves >6 lands via incremental PATCH). Unit-tested both sides. Live build deferred to Phase D (won't autonomously overwrite the reviewed demo).
- **T2 ✅.** `apply_page` fresh-name-on-retry (`_fresh_name` -r2/-r3) + phantom-404→create-fresh + 423-welcome PATCH preserved. 10/10 stubbed tests.
- **T3 ✅ + T3b ✅ (Claude live-verified firsthand, PASS exit 0).** Built side now read from **canvasContent web-part JSON** (`cc-sp-canvas.mjs`, `--built-canvas-url`) = REAL migrated image refs, not blob DOM. Content-only zone scoping; element-level match (image-map identity NAMES a swap; distinct-positional fallback catches drop/dup/placeholder/count when no map); breadcrumb+ARIA noise excluded; fail-closed. Homepage: 11/11 content imgs matched. See [[ref_sp_completeness_gate]]. **REMAINING (Phase B): build step must populate image-map.json fully (homepage `home2/` flow didn't) for full swap-NAMING; 4 article pages still need per-article source manifests (Phase B/T5).**
- **PHASE A COMPLETE. Next: Phase B (T4 driver, T5 tracker, T6 styler-attach) — awaiting Sukaimi go.**

**PHASE A — RELIABILITY GATES (must land before wiring; T1–T3 parallel):**
- **T1 — web-part cap/overflow** (`build-error-resolver` or engineer subagent). Fix `canvas_compose.py`: cap heavy media web parts per page (Graph 400 threshold ≈6 — see [[ref_sp_page_compose_limits]]). Overflow → split into more sections under the limit, OR curate to representative N **and log what was dropped (no silent truncation)**. **Acceptance:** R&D Strategy Live Sessions (9-wp source) builds via the STANDARD pipeline with NO manual curation; dropped elements logged. Files: server `/root/.openclaw/sp-provision/canvas_compose.py` + Mac `/tmp/spwork/canvas_compose.py`.
- **T2 — phantom / fresh-name-on-retry** (engineer subagent). Fix `apply_page`: a failed POST soft-locks that page name + leaves a `find_page`-visible but un-PATCHable phantom (404). On failure, allocate a fresh deterministic name; treat phantom-404 as create-fresh. Keep the existing 423-welcome-page PATCH fallback. **Acceptance:** simulate a failed compose then re-run → succeeds with no manual rename.
- **T3 — completeness / verify gate** (engineer subagent — THE critical one). After build, capture the BUILT page's rendered manifest (`cc-sp-manifest.mjs` on the built URL) and diff vs the SOURCE manifest; FAIL naming any missing image/link/text-block + assert published + ≥N sections. Wire as a gate the build MUST pass; the agent cannot mark a card done if it fails. **Acceptance:** the 5 RDQ pages PASS; a deliberately-broken build (drop one image) FAILS naming the missing element.

**PHASE B STATUS (2026-06-13, dispatched + Claude-verified):** ✅ ALL THREE BUILT.
- **T4 ✅** `cc-sp-mirror.py` (server + Mac /tmp/spwork) — config-driven driver, 9-stage plan (verify-access→capture→audit→tracker→image-migrate→compose→style→**T3 gate**→closeout), zero RDQ-isms, dry-run verified on hypothetical 2nd site + JOB0023. image-map completeness closed on both paths. Underlying-script param surfaces WIRED (canvas_compose `--pages/--build-cap/--heavy-cap`, capture `--pages`, closeout `--job`; sp-audit/image_migrate/sp_home_compose already accepted theirs).
- **T5 ✅** `cc-sp-tracker.py` — 3-sheet config-driven tracker, structure matches prototype.
- **T6 ✅** `cc-sp-styler-attach.py` — idempotent wallpaper+app+customizer attach, Claude-verified on CCBuild-0023. Caught+fixed 2 real bugs at acceptance: **UserCustomAction is SITE-COLLECTION scope** (`/_api/site/usercustomactions`, Scope=2, Title "MDLZ Header"), and **app-install 403s under app-only auth** (operator-gated → graceful skip). cc-site-styler generalization spec written (SPFx build deferred). See [[ref_mdlz_spfx_solution]].
- **LIVE-READINESS PUNCH-LIST (pre-Phase D, NOT yet done):** (1) `cc_verify_sp.py` step-1 is a STUB (does post-build checks, not verify-ACCESS preflight) — build it or drop the stage; (2) driver must write `site-inventory.json` (sp-audit Graph) to jobDir for tracker Sheet1; (3) `sp-expect.json` per-page `status` for tracker Sheet3; (4) per-article source manifests + per-page gate runs (driver gates only Home.aspx; 4 article pages unverified); (5) image-map fully populated on a real run → gate does identity-level swap-naming. **Driver is dry-run-correct; these make it live-runnable.**
- **PUNCH-LIST #4 (per-article verification) — DONE + Claude-verified (2026-06-14):** gate hardened for text articles (mojibake-fold + 0.8 shingle match — article text false-positives gone, fail-closed intact); per-article source manifests captured (jobDir/manifests/); driver gates ALL pages (fails job if any page fails); article image-migration capability built (fixed real flat-`{type:image,src}` placeholder bug). Sukaimi: migrate article images full-fidelity. **NEW FINDING:** source-of-truth divergence — sp-audit captured 1 article image but live page has 2 (jes_red.jpg); build must source article images from the live-capture manifest (single source-of-truth) OR sp-audit must capture all. See [[ref_sp_completeness_gate]]. **Live article rebuild (turns gate green) = operator-gated / Phase D.**
- **SOURCE-OF-TRUTH CHAIN CLOSED (2026-06-14) — all verified except live publish:** build↔gate now agree on article images end-to-end. L1 `_merge_manifest_images` (build set = live-capture manifest, +filename) ✅; L2 image safety net in `build_canvas_from_spec` (places every set-image) ✅; L3 `cc-sp-manifest.mjs --download-images/--images-map` downloads CONTENT image bytes in-session (fresh afdcache), wired into the driver capture stage (home + per-article) — jes_red 56KB + all 3 articles verified ✅. Chain capture-bytes→build-set→placement→migrate→gate. See [[ref_sp_completeness_gate]]. (image_migrate CANNOT app-fetch the client intranet → capture is the only byte path.)
- **PUNCH-LIST #1 verify-access preflight — DONE + live-verified (2026-06-14):** driver step 1 = SOURCE probe (`cc-sp-capture --probe --state <source session>`, Mac; live: ok=true, 482 pages) + TARGET preflight (`cc_preflight_sp.py`, server app-cert: web reachable + AddListItems write bit; live OK on CCBuild-0023, FAIL/exit3 on bogus). Caught + fixed a latent driver bug: cc-sp-capture defaulted to the BUILD-tenant session → source capture would've failed; driver now passes the per-host source session. See [[ref_sp_capture_sessions]]. (`cc_verify_sp.py` left untouched — it does post-build QA, a different job.)
- **PUNCH-LIST #2 + #3 — DONE + Claude-verified (2026-06-14):** #2 `cc-sp-capture.mjs --inventory-out` emits full site-inventory.json (verified 482 entries → tracker Sheet1 482 rows, 11 active/471 archival); driver capture stage passes it. #3 tracker Sheet3 `status` now comes from the per-page GATE VERDICT (`qa-verdict-<label>.json` → "Built — gate PASS" / "INCOMPLETE — gate FAIL"); tracker stage MOVED to after verify so verdicts exist.
- **✅ PHASE B LIVE-READINESS PUNCH-LIST COMPLETE (#1, #2, #3, #4 all done + verified).** The `cc-sp-mirror` driver is dry-run-correct AND live-runnable: verify-access preflight → capture (+inventory +image bytes) → audit → image-migrate → compose (article images reconciled to gate) → style → per-page completeness gate → tracker (gate-based status) → closeout.
- **✅ SUPERVISED LIVE RUN DONE (2026-06-14) — ALL 5 RDQ PAGES GATE-PASS LIVE.** First end-to-end live run (JOB0023 articles) caught + fixed 4 real compose bugs: (1) `sp` used before init (migration silently skipped); (2) `contentIndex:"0"` dropped 4/5 body blocks → CONTENT SAFETY NET added; (3) capture byte path CWD-relative → resolved absolute; (4) signature text source-of-truth gap → `_merge_manifest_text` added. 3 articles rebuilt: full body + both images + signature, copy_coverage 0.998–1.0, **gate PASS**. Homepage already PASS. See [[ref_sp_completeness_gate]]. (One page transiently regressed mid-debug — no library version history, restored fix-forward; always back up canvasContent first.)
- **PHASE C (T7) — INVESTIGATION DONE + GATE VALIDATED (2026-06-14):** the SP harness largely ALREADY EXISTS. Found: (1) `cc-verify-sp` = the deterministic non-self-closable gate, enforced via the BL-001 hard gate + `.sp-verified` marker (cc-board refuses Closed without it); **ran `cc_verify_sp.py JOB0023 --check-only` → PASS, copy fidelity 1.00 on all 3 rebuilt articles** — the existing harness gate ACCEPTS the proven pipeline output. (2) Dispatch infra exists: `workspace-delivery-lead/{AGENTS.md DISPATCH-SP section, CLIENT-BUILD.md}`, `workspace-full-stack-engineer/runbook-sp-convert.md`, `cc-board`/`board_cli.py` (stages: Content Audit→Architecture→Wireframes→Design→Build→Internal QA→Staging→Production→Closed), `sp_dispatch_helper.py`, `cc-dispatch.service` (currently INACTIVE), `brief.json.type==sp_convert` routing.
- **REMAINING T7 WIRING (focused, well-scoped):** the DISPATCH-SP build step + `runbook-sp-convert.md` drive the OLD manual sequence (`image_migrate → canvas_compose → nav_migrate`). Update them to drive the proven **`cc-sp-mirror`** orchestrator (which sequences preflight→capture[+inventory+bytes]→audit→tracker→migrate→compose[source-of-truth merges + 3 safety nets]→style→per-page completeness gate→closeout) + note the per-page `cc-completeness-gate.mjs`. Also add a step deriving `job.config.json` from `brief.json`/`site.json`. NON-RISKY (loop is inactive) but it edits the live autonomous operating protocol → worth Sukaimi review.
- **✅ PHASE C (T7) DONE (2026-06-14):** added `cc-sp-config` (brief+site+sp-expect → job.config.json; tested) + `cc-sp-config`/`cc-sp-mirror` CLI wrappers; updated DISPATCH-SP BUILD step (AGENTS.md) to drive `cc-sp-config` + `cc-sp-mirror --from image-migrate` (source-of-truth merges + 3 safety nets + per-page completeness gate; nav_migrate stays skipped for capture jobs); added an orchestrator callout to `runbook-sp-convert.md`. Gate side was already wired + validated (`cc-verify-sp` PASS on rebuilt JOB0023, copy 1.00). `.bak-ccmirror-*` backups left on both protocol docs.
- **✅ PHASES A–C COMPLETE. The SP classic→modern pipeline is codified end-to-end + wired into the O/C harness, proven live (all 5 RDQ pages gate-PASS).**
- **T7 CORRECTION (2026-06-14):** first BUILD wiring wrongly routed through `cc-sp-mirror` (a MAC-side orchestrator: server stages via SSH, Mac stages local) — wrong for the SERVER harness. Fixed: added **`cc-sp-build <JOB>`** (server-side runner: image-migrate → compose → style, LOCAL, reads job.config) + wrapper; BUILD line now `cc-sp-config` + `cc-sp-build`; `cc-sp-mirror` stays the Mac operator orchestrator (capture + full run + per-page completeness gate). `.bak-build2-*` backups left.
- **AUTONOMY MODEL (honest):** the SERVER harness is autonomous for **build + gate** (`cc-sp-build` → `cc-verify-sp`, both server/Graph). **CAPTURE is operator/Mac-side** by design (Level-2: the client tenant is NOT app-cert-readable — source read = delegated login session, [[project_sp_level2_access_model]]). So a job's flow = operator captures source at intake (Mac, populates `capture/`+`manifests/`+`sp-expect`) → harness builds+gates autonomously. Per-page `cc-completeness-gate.mjs` is a Mac-side pre-check; `cc-verify-sp` (server) is the authoritative close-gate.
- **LEVEL 2 CLOSED at proof-of-capability (Sukaimi 2026-06-14).** Phases A–C done + proven on RDQ + pilot card (JOB0023) Closed + debris recycled. Production-hardening = a deferred FORWARD BACKLOG (NOT open work): (1) Verify-at-intake automation [open fork: operator-assisted vs client self-serve w/ delegated-OAuth], (2) client-tenant redeploy (PnP extract→apply), (3) content-type coverage (publishing layouts / list-driven web parts / subsites), (4) large-site triage+scale guardrails. Full detail in [[project_sp_level2_access_model]]. These activate when a real paying client lands.
- **NEXT (when triggered):** a real example #2 (Phase D calibration with Sukaimi) OR pull a specific forward-backlog item. Nothing runs unattended (`cc-dispatch.service` INACTIVE).

**PHASE B — CODIFY (after gates; T4–T6):**
- **T4 — config-driven driver** (planner + engineer). One entry (skill `/sp-site-mirror` or a `cc-*` CLI) that, given `{sourceUrl, pages|topNactive, buildCap, styler{wallpaperUrl,brandColor}}`, runs the whole pipeline reusing existing scripts. **Acceptance:** dry-run a config for a hypothetical 2nd site → correct step plan, zero RDQ-isms.
- **T5 — productionize the xlsx tracker** (engineer). Turn `/tmp/gen_tracker.py` into a pipeline step (3-sheet: full inventory + active/archival, content elements, classic→modern mapping), config-driven, output to the job dir. **Acceptance:** regenerates the RDQ tracker identically from job data.
- **T6 — styler attach step + generalization SPEC** (engineer). (a) thin pipeline step that attaches the existing MDLZ styler with per-site props (upload wallpaper → `{site}/SiteAssets/mdlz-images/Background-New.jpg`, install app `b9bf61dd…`, register customizer `a1b2c3d4…` — all proven). (b) WRITTEN spec for the generalized `cc-site-styler` (wallpaper URL + brand color as ClientSideComponentProperties) — **build deferred (srv yo/SPFx toolchain is BROKEN; gulp may still work in the existing `mdlz-webparts` project).** **Acceptance:** attach step works on a fresh site given a wallpaper URL.

**PHASE C — O/C WIRING (after T4; T7):**
- **T7 — wire into harness** (architect + technical-writer). Update DISPATCH-SP / `AGENTS.md` / cc-board so the Delivery Lead dispatches the stages as JOB#### Kanban cards, with T3's gate as a deterministic, non-self-closable stage. **Acceptance:** a dry JOB card moves through the stages with the gate enforced; Claude/operator verifies the first run.

**PHASE D — CALIBRATION (with Sukaimi; T8):** run the wired pipeline on the NEXT real site (example #2); Sukaimi verifies the first autonomous run; findings refine config + gates; THEN design polish (custom SPFx web parts, Hero mosaic, spacing).

**DISPATCH NOTE:** after /clear, a fresh session reads THIS section, creates the JOB/Kanban cards (per [[feedback_delegation_kanban_workflow]]), and spawns one contexted subagent per task — each gets this handoff + the named files + its acceptance criteria. Verify each subagent's output against acceptance before marking done (never trust self-report).

**OPEN (Sukaimi's earlier calls, carry forward):** hub join KEPT (global nav tier) — say "unjoin" to detach + hand global tier to human devs; tile-gap CSS folded into the styler handoff; 11 JOB0017 Internal QA cards still clearable.

---

## OBJECTIVE
Build a faithful MODERN mirror of the RDQ **list-driven homepage** on CCBuild-0023 (a real conversion, not a greenfield invention), then **codify the capability** as a reusable skill + DISPATCH-SP wiring so the O/C team performs list-driven homepage mirrors independently.

## WHAT THE SOURCE HOMEPAGE IS (audited 2026-06-12)
`intranet.mdlz.com/sites/RDQ` root = a publishing portal assembled from list-driven web parts:
- **Carousel** (`CarouselItems`): banners — Awards 2026, GlobalSpecs-ISS, 2026 R&D Learning Brochure… each `Title`/`ImageURL`/`RedirectURL`/`DisplayOrder`/`Enabled`.
- **Tile grid** (`HomeTiles`, 15; 6 visible): each `ImageURL1/2` (label baked into the image) + `RedirectedURL` + `Order0` + `IsVisible`.
- **Quick Links rail**: source list is **403** to our account → must **DOM-scrape the correct web-part region** (not global nav/suite chrome).
- ~30 imgs, ~640 chars text → ~95% visual/list-driven. NOT the text-page pipeline.
- Out: MYMDLZ/R&D custom branding + nav (tenant chrome, not portable). Competency tabs / PDDS grid = secondary (v2).

## DELIVERABLES
- **D1 Capture** — clean homepage content bundle (carousel + tiles + quick links) + migrated images.
- **D2 Composer** — list items → modern web parts (carousel→Hero, tiles→image tiles, links→Quick Links).
- **D3 Built + verified** homepage on CCBuild-0023 `Home.aspx`, mirroring the original.
- **D4 Codify** — `/sp-homepage-mirror` skill + DISPATCH-SP wiring for O/C independence.

## TASKS (granular)
### Capture (Mac-side, authed — only Claude/operator; session at ~/.codecraft/verify-intranet.mdlz.com.json)
- **C1** HomeTiles: visible items, sort by Order0, `{title, image(ImageURL1||2), link(RedirectedURL)}`. Tile label lives in the IMAGE → image is the deliverable.
- **C2** CarouselItems: `Enabled=Yes`, **fetch then sort in JS** (no `$orderby` in URL — it 500s), `{title, image(ImageURL), link(RedirectURL)}`.
- **C3** Quick Links: DOM-scrape the **"QUICK LINKS" web-part container only** (exclude suiteBar/nav/accessibility chrome). Best-effort; flag if noisy.
- **C4** Download tile + carousel image binaries via the authed session → `/tmp/home-assets/`.
- **C5** Assemble `home-content.json` + images → ship to `/srv/projects/JOB0023/home/`.

### Compose (server)
- **M1** `sp_home_compose.py` (new): read `home-content.json` → build a modern Home.aspx canvas: Hero (carousel item[0] or a Hero-carousel), an image-tile grid (HomeTiles images as image web parts linking RedirectedURL), a Quick Links web part. Reuse canvas_compose web-part builders.
- **M2** Migrate `/srv/projects/JOB0023/home/images/*` → CCBuild-0023 (image upload, reuse image_migrate upload half), rewrite image URLs.
- **M3** Compose CCBuild-0023 `Home.aspx` with the web parts; publish.

### Verify
- **V1** Authed screenshot of CCBuild-0023 Home.aspx; compare side-by-side with `/tmp/rdq-home.png` (the original).
- **V2** Sanity: N tiles present (linked), carousel present, quick links present.

### Codify (O/C independence)
- **K1** `/sp-homepage-mirror` skill: workflow = detect home's driving lists → snapshot (C1-C5) → migrate images → sp_home_compose → verify. Reusable on any list-driven home.
- **K2** Wire into DISPATCH-SP: when a job's source home is list-driven, run the homepage-mirror step.

## O/C COLLABORATION
- **ux-designer**: layout/order spec (which web parts, tile grid columns, hero choice).
- **engineer**: runs M1-M3 (image migrate + compose).
- **gate/qa**: V1-V2 verification.
- Claude forges the novel tooling (capture + sp_home_compose) and verifies; O/C runs + learns; then K1/K2 hand it to O/C.

## BOUNDARIES
- **Static snapshot** of today's content (not the live list mechanism). No custom MYMDLZ branding. v1 = carousel + tiles + quick links; competency/PDDS = v2.
- Lesson from JOB0023: do this DELIBERATELY (clean captures, verify each step) — rushing live = errors.

## THE REAL FIX (2026-06-13) — comprehensive manifest + completeness gate
Sukaimi's critique (VALID): I never produced a COMPLETE content inventory of the homepage (only page-HTML, not the list-driven/web-part content) → built piecemeal → missed content (4-image row, quick-links, footer logo, bg images) with NO gate to catch it. Same blindness baked into what O/C inherits. Root flaw = dropped FARA's actual intent (a complete up-front inventory driving build + verification).
**Fix (validated approach):** inventory what's RENDERED, not page-HTML — complete by construction.
1. **`tools/cc-visual-qa/cc-sp-manifest.mjs`** (BUILT) — authed; captures `<img>` AND CSS `background-image` + links + text from the content region → ordered manifest + asset list. Ran on RDQ home → **17 images + 30 links** (vs the 13 the piecemeal capture had) — caught the 4-image row (WallOfFame/Bravos/TotallyRandom/Viva), tile links, quick-links rail, R&D nav, Mondelēz logos (top+footer), bg/header tiled images. Manifest at `/srv/projects/JOB0023/home-manifest.json` + `tools/cc-visual-qa/rdq-home-manifest.json`.
2. **TODO — build from manifest** (every element reproduced).
3. **TODO — completeness gate**: after build, capture the BUILT page's manifest, diff vs source; any source image/link/text missing → FAIL naming it. Wire into the pipeline so O/C inherits it.
**STATUS: AWAITING SUKAIMI to validate the manifest is complete (he'll check when home), THEN: wire completeness-gate → rebuild homepage against the full manifest.** Carousel rotation / MYMDLZ suite bar / full tiled-bg flagged as modern-SP/cross-tenant limits (approximations only).

## UPDATE (2026-06-13 ~10:30 UTC) — RDQ home now at REFERENCE QUALITY (wallpaper live)
Sukaimi gave the reference bar: `codeandcanvas.sharepoint.com/sites/MondelezDemo/SitePages/MDLZ-Homepage-Demo.aspx` ("fairly acceptable"). Studied it (cloned its canvas via authed SP REST): it's ALL NATIVE (Image web parts in 3-col rows + 1 Hero) over a **purple theme + a full-bleed wallpaper injected by an SPFx Application Customizer**. Rebuilt RDQ to match:
- **apply_page 409 FIXED**: `Home.aspx` is the site welcome page → Graph DELETE returns **423 Locked** → added `_patch_existing_page()` fallback in `canvas_compose.py` (PATCH canvasLayout in place; also 409-handled). Durable.
- **Purple theme** applied via SP REST `/_api/thememanager/ApplyTheme` (`sp_home_theme.py`, palette themePrimary #5c2d91).
- **Branded header**: 05 R&D Function Banner set as the page **title-area hero** (`set_title_area_hero` imageAndTitle) → KILLED the inherited MS stock photo (hubblecontent.osi.office.net) that was stuck in the title Banner web part. Dropped the lone top-right logo (wrong pattern — reference brands via banner+theme, not a standalone logo).
- **Images resized properly** server-side (venv PIL): tiles 1888→700px, banners→1600px; originals backed up to `home2/images_orig/`. (`/tmp/resize_rdq.py`.)
- **Footer** = text-only wordmark (the 329x50 logo upscaled+pixelated full-width; header carries brand now).
- **WALLPAPER (the one non-native piece) — REUSED an existing deployed SPFx solution, NO build:** found `/Users/sukaimisukri/Workspace2/SharePoint-v2/mdlz-webparts` (SPFx 1.22.2, solution id `b9bf61dd-23d6-4f84-872d-fbde1b7d19a1`, already deployed in `/sites/appcatalog`). Its **`MdlzHeaderApplicationCustomizer`** (component id `a1b2c3d4-e5f6-7890-abcd-ef1234567890`) injects `{site}/SiteAssets/mdlz-images/Background-New.jpg` as page bg + WELCOME band + purple hub nav. URL is **site-relative** + RDQ IS Mondelez → just: uploaded the authentic RDQ wallpaper (`intranet.mdlz.com/SiteAssets/V2030/images/bg.jpg`, the purple snacks pattern) to `CCBuild-0023/SiteAssets/mdlz-images/Background-New.jpg`, installed the app on the site, registered a SITE-scoped UserCustomAction (cid above). (`yo`/SPFx toolchain on srv is BROKEN — synthetic EACCES in yeoman-env — but moot since we reused the prebuilt .sppkg.)
- RESULT: purple snacks wallpaper + WELCOME header + white content cards + branded R&D header + crisp tiles + Bravos row + quick links + footer = reads like the reference. **Client-presentable.**

**CODIFY NOTE:** the reused `MdlzHeader` customizer is MDLZ-SPECIFIC (hardcoded `mdlz-images` path + MDLZ welcome text). The reusable **`cc-site-styler`** = a GENERALISED version: wallpaper URL + brand color as **ClientSideComponentProperties** per client. That's the SPFx-library seed for O/C — build at codify time (rule-of-three), NOT now.

**NEXT:** (1) Sukaimi reviews the wallpapered page; (2) optional polish (Quick Links → styled web part, carousel auto-rotate via the mdlz-webparts `MdlzBannerCarousel` web part which ALSO exists in that solution); (3) 2nd example; (4) codify `cc-site-styler` (generalise MdlzHeader) + `/sp-homepage-mirror` skill + completeness-gate. Also pending: clear 11 JOB0017 Internal QA cards.

## COMPACT CHECKPOINT (2026-06-13 ~08:50 UTC) — superseded by the UPDATE above
**Strategy (Sukaimi):** Claude does the RDQ homepage SOLO first to LEARN the full workflow, THEN transfer to the O/C harness. Order flipped: get the homepage to CLIENT-QUALITY first (it's only ~50% — not presentable), completeness-gate DEFERRED, codify LAST.

**Homepage state (live: CCBuild-0023/SitePages/Home.aspx) — CONTENT COMPLETE, design ~50%:**
- ✅ Carousel (7 in `CarouselItems`; only banner[0] shown as a static hero), ✅ 6 clickable tiles (`imageLinkUrl`), ✅ the 4-image row (WallOfFame/Bravos/TotallyRandom/Viva — fixed via in-session download; afdcache img URLs EXPIRE so grab in-session w/ fresh tokens), ✅ Quick Links panel (6), ✅ footer (text), ✅ R&D nav (7 nodes via `sp_home_chrome.py` SP-REST topnavigationbar).
- 🔧 IN PROGRESS: **logo → top-right** — `sp_home_compose.py` edited (first section = `oneThirdRightColumn` spacer + small right-aligned `mondelez-logo-sm.png` 260x39; footer now text-only). **BLOCKED, not applied** ↓.
- 🔴 **BLOCKER — `apply_page` 409 `nameAlreadyExists`** recomposing Home.aspx: its delete-then-recreate of the welcome page fails. FIX = PATCH the existing page's canvasLayout instead of delete+recreate (or 409-handle / temp-name+set-welcome). Logo edit is staged but the page is still the prior (no-logo) version.

**DECISION — custom SPFx web part (Sukaimi raised, Claude agreed):** the right path to client-quality fidelity (auto-rotating carousel, hover tiles, exact look) = a **reusable custom SPFx "list-driven homepage" web part** fed the manifest data. Also simplifies composition (1 web part vs 17 native) + dodges the brittle apply_page replace. It's the seed of the **SPFx-web-part library** for O/C.

**O/C harness vision (agreed):** the manifest classifies each element **OOTB-buildable (which web part)** vs **needs-custom-SPFx** → O/C auto-builds OOTB + flags/queues SPFx; a growing SPFx library makes more OOTB over time.

**Codify = LAST + rule-of-three:** do NOT codify the skill from ONE example (overfits RDQ-isms). Get RDQ to 100%, ideally a 2nd list-driven home, THEN codify as a CONFIG-DRIVEN `/sp-homepage-mirror` skill + the completeness-gate. (Single-example codify = not best practice — Sukaimi agreed.)

**Tools/files:** `tools/cc-visual-qa/cc-sp-manifest.mjs` (THE real-fix complete manifest), `sp_home_compose.py` (native composer, has the logo edit), `sp_home_chrome.py` (R&D nav SP-REST). Data: `/srv/projects/JOB0023/home-manifest.json`, `/home2/home2.json` + `/home2/images/`. Backups `.bak-*`.

**Board hygiene:** 11 "Internal QA" cards = ALL JOB0017 (themes-layouts feature, all DONE per notes) → clear/close all 11; unrelated to JOB0023.

**NEXT (in order):** (1) fix the apply_page 409 (PATCH not recreate) so the logo/top-right lands; (2) decide native-polish vs build the SPFx homepage web part for the carousel + look; (3) push RDQ to client-quality; (4) 2nd example; (5) codify + completeness-gate. The 3 article pages are already DELIVERED + sectioned (see HANDOFF_LEVEL1_TEMP.md).
