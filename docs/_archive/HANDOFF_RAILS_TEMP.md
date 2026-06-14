> **ARCHIVED 2026-06-14 — superseded; SP Phases A–C done + Level 2 closed (see [[project_sp_level2_access_model]]).** Current comprehensive SP record + forward backlog: `docs/handoffs/HANDOFF_HOMEPAGE_MIRROR.md`. Content below preserved for history.

# TEMP HANDOFF — Final Setup Track: O/C-Independent, User-Verified Pipeline (Rails 1-3)

_Live working doc. Survives /clear & /compact. Created 2026-06-12._
Related: `HANDOFF_LEVEL1_TEMP.md` (the conversion pipeline), memory `project_sp_level2_access_model`, `feedback_verify_gate`, `feedback_claude_sets_up_oc_runs`, `project_oc_team_calibration`.

## OBJECTIVE
Make the OpenClaw O/C SharePoint classic→modern conversion pipeline **fully O/C-independent**, with the **USER (not Claude)** as the verification/approval point. After this track, **Claude exits the run loop permanently** — Claude's only remaining role is this one-time setup build. O/C builds, runs, and self-verifies; machines catch invisible defects; the user approves visible outputs.

## WHY (the two failures that defined the rails — 2026-06-12)
1. **Spawn-and-yield stall** → the engineer built `sp_normalize.py` but never applied it: `main` yielded and nothing drove the sub-agent to completion. → **Rail 1**.
2. **A bug a naive check would pass** → `sp_normalize.py` step-1 (`paired ï¿½…ï¿½ → quotes`) wrongly pairs contraction apostrophes (`thatï¿½s … Weï¿½ve` → `that"s … We"ve`); a bare "0× ï¿½" acceptance would STILL pass while the prose is corrupted. → **Rail 2** (fixtures + output-sanity, not just absence-of-marker).

## DELIVERABLES
- **D1 — Rail 2:** a deterministic, blocking, per-step gate+fixture harness. No stage advances on red; agents cannot self-mark done.
- **D2 — Rail 1:** a self-completion loop that drives every agent task (conversion stages AND tool-builds) to gate-green, with stall→user escalation.
- **D3 — Rail 3:** user-as-gate — each client checkpoint pauses and surfaces the visible artifact to the user via Teams + board, with Approve / Reject-with-comment driving the pipeline.
- **D4 — Proof:** JOB0023 converted end-to-end on hardened rails, user-approved, Claude-untouched.

## OWNERSHIP
- **Build the rails:** Claude (this is the final SETUP pass; setup ≠ running).
- **Run conversions afterward:** O/C (board + agents + supervisor).
- **Verify/approve:** the USER (machine gates for the invisible; user approval for the visible). Claude: none, post-track.

## SEQUENCE
**Rail 2 → Rail 1 → Rail 3 → Proof.** (Rail 2 defines "done" that Rail 1 drives toward and Rail 3 surfaces.)

---

## BREAKDOWN

### RAIL 2 — Machine self-verification (gate + fixtures) — DO FIRST
Extends the existing deterministic gate pattern (`cc-verify-sp`).
- **R2.1 Gate framework** — a uniform `cc-gate-<step> <JOB>` convention: exit non-zero = BLOCK, prints reasons. One entry the supervisor/agents call per stage.
- **R2.2 Fixture runner** — `/root/.openclaw/sp-provision/tests/` + `cc-run-fixtures <tool>`: runs input→expected fixtures, returns pass/fail. Used by gates + the code-reviewer agent.
- **R2.3 Fix `sp_normalize.py`** — drop the buggy step-1 paired-quotes; global `ï¿½ → '` (rare real-quotes degrade to `'x'`); keep Win-1252 fixes. Idempotent.
- **R2.4 `sp_normalize` fixtures + gate** — fixtures incl. the contraction-corruption case; gate = `0× ï¿½` **AND** no `"`-wrapped contractions **AND** length-preserved. **Must FAIL the OLD buggy version** (proves the harness catches it) and PASS the fixed one.
- **R2.5 Gate existing steps** — wrap with blocking gates: from-capture (schema/page-count), `canvas_compose` (copy-fidelity ≥0.9, exists), tracker (sheet/asset sanity). 
- **R2.6 Reviewer wiring** — code-reviewer + qa-engineer agents run `cc-run-fixtures` + the gate on ANY tool change before first use (their AGENTS.md).
- **DoD:** every stage has a blocking gate; the step-1 bug is auto-caught by fixtures; nothing advances on red.

### RAIL 1 — Self-completion (kill stalls)
- **R1.1 Diagnose** the OpenClaw spawn/await model — why `openclaw agent` returns before spawned sub-agents finish; what `subagents/runs.json` + `flows/registry.sqlite` + `tasks/runs.sqlite` track; whether await is possible or polling is required.
- **R1.2 Completion-driver** — after dispatch, poll the stage's Rail-2 gate; re-kick the responsible agent until green or N retries. Generalize `cc-dispatch-loop-sp` from "one tick" to "drive to gate-green."
- **R1.3 Stall/timeout escalation** — no progress in M ticks → escalate to the USER via Teams (not Claude); never silently stop.
- **R1.4 Generalize** — one "task-with-a-gate" abstraction covering conversion stages AND tool-builds (so a tool-build like R2.3 would itself self-complete).
- **R1.5 Tests** — (a) a normal multi-step task reaches gate-green with zero nudges; (b) a deliberately-broken step re-kicks then escalates to the user after N.
- **DoD:** multi-step tasks finish without human/Claude re-kicks; broken work escalates to the user.
- **RISK:** hardest rail — OpenClaw harness-level. If true await is unavailable, fall back to a gate-polling cron driver. Flag framework limits early.

### RAIL 3 — User-as-gate (approve outputs, not code)
- **R3.1 Gate-pause → Teams** — at Content-Audit Gate 1, QA Gate 2, final review: `cc-board pause` (exists) + push a Teams card (msteams plugin) with the visible artifact (tracker xlsx link / authed page screenshot / before-after diff) + **Approve / Reject-with-comment**.
- **R3.2 Approve** → `cc-board resume <JOB>`.
- **R3.3 Reject-with-comment** → re-kick O/C with the comment (feeds Rail 1), card back a stage.
- **R3.4 QA screenshot** — the authed Mac-side shot (operator step) flows into the same approve card.
- **R3.5 Test** — a run pauses, user gets the card, approve resumes, reject re-kicks — zero Claude.
- **DoD:** a run is driven entirely by user Teams actions.

### PROOF — JOB0023 on hardened rails
- **P.1** Re-run JOB0023 through the rails: normalize (fixed+gated) → tracker regenerated clean → **user approves Gate 1** → Design → Build → QA gate → **user approves screenshot** → done. Confirm **zero Claude touches**; all gates machine-checked; all approvals user/Teams.
- **DoD:** JOB0023 converted, user-approved, Claude-untouched end-to-end.

---

## BOUNDARIES / OUT OF SCOPE (separate tracks)
- **Task 5** — intake Verify form (Power Apps + auto-job-creation). The front door; complements but not part of the rails.
- **`nav_migrate --from-capture`** — cross-tenant nav for real clients.
- **Bespoke-site shapes** — publishing layouts, list-driven web parts, subsites (RDQ's full intranet).

## CURRENT STATE (fold-ins as of 2026-06-12)
- **JOB0023** — PAUSED at Gate 1 (Mondelez RDQ pilot, Excel-only tracker ready). Becomes the **P.1 proof run**. Stage monitor still armed.
- **`sp_normalize.py`** — built by O/C, **NOT applied**, has the step-1 bug. Becomes **R2.3/R2.4** (the harness's first fixtured catch). Do not apply until fixed+gated.
- **Pipeline config already wired:** DISPATCH-SP is capture-aware + has the STANDING normalize step + Excel-only Gate-1. Supervisor live (`/etc/cron.d/cc-dispatch-sp`, `*/5`). Gate `cc-verify-sp` deterministic (copy-fidelity ≥0.9 + authed >50KB screenshot). Backups `.bak-capaware-*`, `.bak-normalize-*`.
- **User-only Mac steps that stay (never Claude):** client capture login (`cc-sp-capture --login`), build-site device-code (`create_grant_buildsite.py`), authed QA screenshot (`tools/cc-visual-qa/qa.mjs --auth`).

## RISK SUMMARY
- Rail 1 is the load-bearing risk (agent-harness completion semantics). Build Rail 2 first so "done" is well-defined before attacking Rail 1.
- Bootstrapping reliability via the system being made reliable is why **Claude builds the rails** (not O/C) — avoids the circular dependency.
