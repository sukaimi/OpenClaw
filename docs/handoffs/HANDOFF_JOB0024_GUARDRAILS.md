# ▶▶▶ HANDOFF — JOB0024-108: Large-site guardrails (SP classic→modern)

**Working doc for the current build. Safe to resume after /compact or /clear.** Started 2026-06-14.
Sibling cards (separate work): JOB0024-109 content-type coverage, JOB0024-110 client-tenant redeploy. Parent backlog: [[project_sp_level2_access_model]] forward item #4. Main SP record: `HANDOFF_HOMEPAGE_MIRROR.md`.

## GOAL
Real large sites (RDQ audit = 482 pages) convert SAFELY: never build a whole site blind. Triage → operator approves scope → build in small waves → every page backed up before overwrite → deterministic per-page gate → operator reviews only EXCEPTIONS. Every error caught deterministically, isolated to one page, reversible, surfaced as a named exception.

## LOCKED DEFAULTS (config-driven; changeable)
- `triageKeepMonths` = 18 (keep if modified within; else archive)
- complexity cap = existing `heavyWebpartCap`
- **This card FLAGS publishing/list-driven pages — does NOT rebuild them** (rebuild = JOB0024-109)
- Calibration site (Phase F) = TBD (need own-tenant site w/ publishing + list pages; CrestfieldClassic likely too simple). **NEVER MDLZ.**

## HARD CONSTRAINTS
- Config-driven, NO site-specific hardcoding. · Flag-don't-fake (un-buildable = flagged, never faked).
- Per-page completeness gate = deterministic close-gate; agent CANNOT self-close.
- Client/foreign tenants (MDLZ/RDQ) READ-ONLY, zero writes; never auto-target. Calibrate own-tenant only. [[feedback_mdlz_read_only]]
- Operator-driven runs (SP auto-dispatch cron DISABLED). Claude sets up + observes, not in the loop. [[feedback_claude_sets_up_oc_runs]]
- Reversibility + per-page isolation over speed; resumable across waves; idempotent.

## DEPLOY MODEL (3 locations — keep in sync)
- **Repo = source of truth.** `/Users/sukaimisukri/Workspace2/OpenClaw/` (branch off `main`, PR/merge).
- `tools/cc-visual-qa/*.mjs` = the **Mac runtime** location (capture/gate/rollup run here).
- `tools/sp-provision/*.py` = mirror of the **server** engine. After editing, **DEPLOY** to `root@76.13.179.220:/root/.openclaw/sp-provision/` (sshpass; pass in `~/.codecraft/verify-watch.json`).
- Job runtime dirs on server: `/srv/projects/<JOB>/` (capture/, sp-expect.json, site-inventory.json, backups/, worklist.json, exceptions.md).

## WHERE IT SLOTS (cc-sp-mirror.py stages)
Today: `preflight → capture → audit → compose(≤buildCap) → style → tracker → closeout`.
New: insert **triage** after capture; **scope gate** before compose; compose's blunt `buildCap` → **worklist/waves** loop; **backup** inside `apply_page`; **rollup** at closeout.
Anchors: `cc-sp-capture.mjs:115` inventoryAll.push · `canvas_compose.py:1313` apply_page (delete+recreate; Home.aspx=PATCH-in-place) · `cc-completeness-gate.mjs` writes per-page verdict (exit 0=PASS) · `cc-sp-mirror.py` stages ~170-256, `--from`/`buildCap`.

## DATA SCHEMAS
- **scope-sheet.json** (per page): `{file,title,lib,modified,bytes,webPartCount,isPublishing,hasListWebpart, keep:bool, buildable:bool, flagReason:str|null}`
- **scope-approved.json**: `{approvedFiles:[...], approvedAt, by}`
- **worklist.json**: `{job, waveSize, pages:[{file, status:"pending|done|failed", verdict?, wave?}]}`
- **exceptions.md / .json**: per page PASS/FAIL/flagged-skipped + reason; summary counts.

## TRIAGE HEURISTICS
- `keep` if `modified` within `triageKeepMonths` & not system/template; else `archive`.
- `buildable` if `lib=="Site Pages" & webPartCount≤heavyWebpartCap & !hasListWebpart & !isPublishing`; else `flag` w/ reason (`publishing-layout` / `list-driven` / `subsite` / `heavy-media`).

## BUILD ORDER + TASK TRACKER  (recommended: read-only first, publish-path last)
Status: ⬜ todo · 🔨 doing · ✅ done

### Phase A — Triage classifier (read-only) ✅ DONE
- ✅ **A1** enriched `cc-sp-capture.mjs` inventory rows w/ `bytes, webPartCount, isPublishing, hasListWebpart` (heuristic regexes; parses OK). Backward-compatible add.
- ✅ **A2** `tools/sp-provision/cc_sp_triage.py` built — inventory → `scope-sheet.json` + `.csv`; config-driven (`triageKeepMonths`/`heavyWebpartCap`). **Tested on synthetic 6-page inventory: keep 4/archive 2, buildable 1, flagged 3 (publishing/list/heavy) — all paths correct.** NOTE: B1 (`--approve`) + C1 (`--worklist`) are ALSO scaffolded inside this script (test them in their phases). Deployed to server.

### Phase E — Exceptions rollup (read-only)
- ✅ **E1** `tools/cc-visual-qa/cc-sp-rollup.mjs` built — verdicts (`qa-verdict-*.json`) + scope-sheet + worklist → `exceptions.json` + `exceptions.md` (failures + flagged-skipped only; passing pages counted not listed). **Tested** on synthetic verdicts: 1 fail surfaced w/ reason, 3 flagged-skipped, 2 archived, 1 pass omitted. ✓
- ⬜ **E2** wire rollup into `cc-sp-mirror` closeout — DEFERRED to the orchestrator-integration pass (below).

### Phase C — Page-level waves
- ✅ **C1** worklist generator (`cc_sp_triage.py --worklist`) — approved+buildable → `worklist.json` (status pending/done/failed, waveSize). **Tested** ✓ (respects scope-approved.json).
- ⬜ **C2** driver consumes worklist — DEFERRED to orchestrator pass.

### Phase D — Backup-before-republish ✅ DONE (tools; live test at F)
- ✅ **D1** `canvas_compose._backup_page` + pre-delete call in `apply_page` (gated on env `CC_SP_BACKUP_DIR`; no call-site changes). Snapshots canvasLayout+title+sid → `/srv/projects/<JOB>/backups/<page>.<ts>.json`. Best-effort (recycle bin = fallback). Compiles OK, deployed.
- ✅ **D2** `cc_sp_restore.py <JOB> [<page> | --list] [--at <ts>] [--site-path …]` — re-applies the newest (or chosen) backup via `apply_page`. Compiles OK, deployed. *Live overwrite→restore test at F.*

### Phase B — Scope sign-off gate
- ✅ **B1** `cc_sp_triage.py --approve [--all-buildable]` → `scope-approved.json`. **Tested** ✓.
- ⬜ **B2** build refuses un-approved pages — DEFERRED to orchestrator pass.

### ✅ ORCHESTRATOR-INTEGRATION PASS — DONE (covers C2 + B2 + D-env + E2 pointer)
Wired into `cc_sp_build.py` (the server harness path), **backward-compatible** (legacy behaviour when no worklist/approval):
- ✅ **C2 waves** — `worklist.json` present → build next `waveSize` pending pages, `_mark_worklist` done/failed (resumable). Unit-tested.
- ✅ **B2 scope-gate** — skips pages not in `scope-approved.json` (logged). Unit-tested.
- ✅ **D-env** — sets `CC_SP_BACKUP_DIR=<jd>/backups` so compose snapshots before overwrite.
- ✅ triage auto-run — emits informational `scope-sheet.json` when an inventory is present.
- ✅ **E2** — rollup runs STANDALONE after the close-gate (`cc-sp-rollup.mjs <jd>`); cc_sp_build's final message points to it. (Not wired into cc-sp-mirror — the Mac orchestrator is the operator-full-run path; the server harness + standalone tools are the guardrail path. cc-sp-mirror wiring = optional later.)
Deployed + compiles on server. **ALL BUILD WORK DONE — only Phase F (live calibration) remains.**

### Phase F — Calibrate + prove (own-tenant)
- ⬜ **F1** pick/seed own-tenant multi-page site w/ known good + known-unbuildable pages.
- ⬜ **F2** full dry run end-to-end; confirm flags-not-fakes, gate FAILs caught, restore works, rollup shows only exceptions; calibrate thresholds + gate vs known good/bad.

## OPEN DECISIONS (non-blocking; defaults assumed)
1. Triage thresholds (18mo / heavyWebpartCap) — assumed, revisit at F.
2. Calibration site — decide at F1.
3. Flag-only boundary (rebuild = 109) — assumed agreed.

## CURRENT STATUS (update as we go)
**2026-06-14:** ✅ **ALL BUILD WORK DONE** — A1 inventory-enrich, A2 triage, B1 approve, C1 worklist, D1 backup, D2 restore, E1 rollup, + orchestrator integration (C2 waves / B2 scope-gate / D-env / E2 pointer) all built, unit-tested on synthetic data, deployed to server, and committed on branch `job0024-guardrails` (3 commits). Backward-compatible (legacy build path unchanged). **ONLY Phase F (live calibration) remains.**

**Phase F nuance discovered (decision needed):** a seeded own-tenant site CANNOT exercise every path live — `Modified` dates can't be backdated (archive path) and classic publishing infra can't be created in modern SPO (publishing-layout flag). What IS live-testable on an own-tenant site: buildable+gate-PASS, heavy-media flag, list-web-part flag (if the regex fires), gate-FAIL, waves+resume, backup→restore, scope-gate, rollup. Archive + publishing flags stay synthetic-validated (A2) — justify with a regex unit-test against representative body samples. **Proposed F:** seed a small own-tenant site (~4 pages: simple / heavy / list-part / deliberately-incomplete) + capture→triage→approve→worklist→build(2 waves)→backup→restore→gate→rollup. Awaiting go (provisioning a site in the tenant = confirm first).
