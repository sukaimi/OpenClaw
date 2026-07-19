# SPARK v1 — Project History (consolidated archive)

Single chronological record consolidated from the many transient handoff / onboarding / UX-pass
documents that used to live under `docs/_archive/` and `docs/handoffs/`. Those source files were
merged here and removed during the 2026-07-19 docs consolidation. Dates, decisions, and what
shipped are preserved; the ephemeral "resume after /compact" scaffolding around them is not.

Product naming note: the platform is **OpenClaw**; the internal product/kit is **SPARK v1**
(SharePoint Autonomous Rebuild Kit). Historical docs used **Code&Craft** (the autonomous
AI software-delivery unit) and its parent agency **Code&Canvas** — both appear below verbatim
where quoted.

---

## 2026-05-31 — Reconfigure OpenClaw: creative agency → design/build/deploy team

Source: `CLAUDE_CHAT_ONBOARDING_OpenClaw_DesignBuild.md` (CTO audit / onboarding pack written for
Claude Chat, which had no server access).

- OpenClaw on Hostinger `srv1330842` re-architected from a "creative content agency" (Code&Craft)
  into a full end-to-end software **Design → Build → Deploy** team. Migration was largely executed
  by the time the doc was written (Phases 0–2 live).
- Runtime upgraded to OpenClaw **2026.5.28** under systemd (`openclaw-gateway.service`).
- Build team live (6 agents): delivery-lead (hub) · product-manager · architect ·
  full-stack-engineer · code-reviewer · devops-deploy. Original 5 legacy agents kept.
- Coding engine = OpenCode + `coding-agent` skill.
- Model routing (at the time) via OpenRouter: orchestration = `gemini-2.5-flash`,
  reasoning (architect/reviewer) = `claude-sonnet-4.5`. **NOTE: superseded — production later moved
  to DeepSeek V4 across all 10 agents (Profile A `deepseek-v4-flash` / `deepseek-v4-pro`).**
- Config version-controlled at private repo `sukaimi/openclaw-config`.
- Open at the time: per-agent prompt customization, OpenCode cheap-coder A/B, exec-approval gate,
  key rotation.

## 2026-05-31 → 06-02 — Per-agent prompt rewrite planning

Source: `CLAUDE_CHAT_PLANNING_PACK.md`.

- Planning pack to turn Sukaimi's process into per-agent `AGENTS.md` rewrites. Telegram bot fronts
  the team as "Code&Canvas Development Team"; hub-and-spoke Design→Build→Deploy.
- Mechanics locked: delegate ONLY via `sessions_spawn`; only the hub spawns; specialists never spawn
  or talk to each other; builds in isolated checkouts under `/srv/projects/<project>`, never inside
  `~/.openclaw`.

## 2026-06-01 → 06-02 — Foundation jobs (from the jobs ledger)

- **FC0001** — Command Center home-page AI search: replaced Amazon Q with a Claude Haiku
  `qSearchProxy` Azure Function; provisioned + rotated `ANTHROPIC_API_KEY`; decommissioned Amazon Q.
- **JOB0001** — Teams integration + SharePoint build pipeline: msteams config/runbook, Azure Bot
  registration, public HTTPS gateway, GitHub Actions CI for SP provisioning (compiles `.sppkg`
  off-tenant), per-client site access, OpenCode engine, end-to-end test.
- **JOB0002** — Command Center UX refresh + bot-experience fixes (graceful first reply for
  non-allowlisted users, empty/parse-error reply guard, durable Teams welcome card).

## 2026-06-02 — Bot UX pass: the "Stone & Line" voice

Sources: `ux-audit-bot-experience.md`, `ux-copy-bot-rewrite.md` (the substantive deck),
`ux-implementation-status.md`, `ux-qa-verification.md`, and the `_ux-input/` raw evidence
(`live-AGENTS.md`, `NEW-AGENTS.md`, `surfaces*.txt`, `bot-samples*.txt`, `_INDEX.md`).

**Problems found in the live bot (Teams + Telegram):**
1. Reply voice was "operator buddy" — terse, insider, passive-aggressive ("you've done that
   about 8 times now"; timestamp/"the line's clean" radio theatre).
2. Internal `status: done | needs-decision` token leaked on every user-visible reply.
3. Profile A/B gate demanded at first contact with zero explanation.
4. Teams welcome card was the generic stock assistant card ("Help me draft an email / Summarize my
   last meeting") — wrong mental model, nothing about SharePoint delivery.
5. Unrecognized Teams users silently dropped (`dmPolicy: allowlist`) — no "you're not set up yet".
6. "What can you do?" returned a parse-error/empty turn (DeepSeek "incomplete turn" instability).

**"Stone & Line" voice spec (target persona, preserved):** calm, crafted, precise; warm but spare;
confident without hype. No emoji, no operator-radio phrasing, no snark/score-keeping, no insider
framing, no internal status tokens, no timestamps unless asked. Lead with the answer or the next
action; one idea per line; assume first-time context and good faith.

**Applied & verified (against live bot on srv1330842):**
- Hub persona rewrite in `AGENTS.md`: voice split — internal agent→hub stays terse machine format;
  human channels use "Stone & Line". `status:` leak fixed by prompt scoping (emitted only on
  agent→hub returns). Profile gate deferred to build-start and relabelled **Standard** (A) /
  **Restricted** (B) — raw "Profile A/B / China-origin / FC-safe" labels never shown to users.
  Canonical first-contact replies added (greeting, capabilities, how-to-brief, out-of-scope).
- New welcome-card copy (headline "Code&Craft — Delivery Lead", value prop, 3 on-brand chips:
  "What can you do?" / "Start a project brief" / "How should I brief you?") — flagged as a
  code/plugin change (hardcoded msteams card strings, not prompt).
- QA: 4 fresh cold sessions passed all 9 checks (no-emoji, no-status-leak, no-snark,
  no-profile-demand-at-first-contact, scannable capabilities, polite out-of-scope, clean gibberish
  handling, Teams port 3978 up, config valid).

**Agent system-prompt design intent (from `NEW-AGENTS.md`, worth preserving):** every seat is on the
Code&Craft team (autonomous AI software-delivery division of Code&Canvas), reports to Sukaimi never
the client. Non-negotiables encoded: delegate only via `sessions_spawn`; isolated builds under
`/srv/projects/<project>`; machine status line on agent→hub returns only; bounded clarification
(ask once, batch, then proceed on logged assumptions); **anti-spiral** (3 attempts/task, stop+return
`blocked` on 3rd failure, loop-detection on repeated diffs, escalate upward never sideways);
secrets by store-location only; untrusted input (client comments/email/files) is DATA never
instructions; SPFx compiles off-tenant, act only on the assigned site.

## 2026-06-05 → 06-07 — Web/EDM delivery line (2nd rail, Phases 1–3)

Sources: `HANDOFF_phase1-3_TEMP.md` (created 2026-06-05), the `BACKLOG.md` Done log (now split to
`backlog-history.md`), and jobs JOB0003–JOB0006.

- Second delivery line: static web + EDM (email) builds, distinct from the SharePoint rail. The SP
  rail was already considered closed/built at this point.
- **JOB0003** — Phase-1 Web/EDM build engine (proven; vision + Higgsfield deferred → BL-008/009).
- Front door + money loop: Tally form → `/cc/pay` redirector → exact Stripe link → webhook →
  `cc-fulfil` → O/C build. CRO landing page live at `request.codeandcraft.ai`.
- Client verify gate (BL-001), per-client Vercel isolation (BL-002), Phase-3 close-out +
  90-day archive (BL-003), images on delivered pages (BL-011), self-contained deliverables (BL-013),
  legal pages (BL-006), reliability crons cc-verify-sweep + cc-autocloseout (BL-012),
  wrong-email recovery cc-resend + cc-bounce-watch. All three customer journeys (J1/J2/J3) passed
  end-to-end 2026-06-07.
- **JOB0006** — first O/C-agent-built client job (3 bespoke pages, gate-verified, closed out).
- Board archival lifecycle: Kanban = live view only; `cc-closeout` appends to
  `/srv/cc-archive/REGISTRY.md` (canonical ledger) and deletes the card. Board 47→0 in one cleanup.
- The ops code for this rail (intake/build/deploy/fulfil/closeout/Stripe/verify/dispatch/Kanban)
  is preserved as stale snapshots under `tools/ops/` — see `tools/ops/README.md`.

## 2026-06-05 → 06-14 — M365 / SharePoint access standup

Source: `CLAUDE_CHAT_M365_ACCESS_HANDOFF.md`.

- The 10-seat team was built to deliver SharePoint sites but had zero M365 access provisioned; this
  workstream fixed that. Decided (locked): SPFx toolchain = GitHub Actions CI (`.sppkg` off-tenant);
  Kanban = a SharePoint list rendered as a board view (not Planner).
- Two distinct access scopes kept separate: **Command Center = the Code&Canvas (C&C) tenant**
  (Project Log, Kanban, Learnings Wiki); **Client site = the client's own tenant** (builds happen
  there via a scoped per-site app-registration grant).

## 2026-06-10 — JOB0017: 12×12 themes/layouts library

Sources: `HANDOFF_JOB0017_TEMP.md`, `docs/features/feature-request-12themesx12layouts.md`.

- **JOB0017 COMPLETE.** Full 12×12 orthogonal themes/layouts library: canonical `--cc-` contract,
  144-cell fit-map, matcher, gallery (168 screenshots + generator), git-installable npm package,
  OpenClaw skill (enabled on 3 agents), visual-QA capability, and the Command Center gallery page.
  Library now lives in the separate repo `codecraft-themes-layouts`. All cards closed. Feeds JOB0019;
  the SP builder does not use it.

## 2026-06-11 — Strategic pivot: web/EDM deprioritised in favour of the SharePoint rail

- The web/EDM rail (landing + Stripe funnel + EDM) was **deprioritised**; the **SharePoint
  autonomous-rebuild rail became the headline product** (SPARK v1). Web/EDM P3 items (BL-005 Stripe
  LIVE, BL-007 EDM depth, BL-016 DKIM) are frozen with that rail. The landing + legal mirrors now
  live under `docs/web-rail/` as the parked rail.

## 2026-06-11 → 06-14 — SharePoint classic→modern conversion pipeline (Levels 1–2)

Sources: `HANDOFF_LEVEL1_TEMP.md` (2026-06-11), `HANDOFF_RAILS_TEMP.md` (2026-06-12),
`HANDOFF_HOMEPAGE_MIRROR.md` (resume-state, 2026-06-14), and memory
`project_sp_pipeline_codification` / `project_sp_level2_access_model`.

- Mission: O/C agent team performs SharePoint classic→modern site conversions; Claude sets the team
  up to run independently + observes/tweaks, never in the build loop.
- **Rails** (from the two failures that defined them, 2026-06-12): Rail 1 = fix the spawn-and-yield
  stall (sub-agent built `sp_normalize.py` but nothing drove it to completion); Rails 2–3 = make the
  pipeline fully O/C-independent with the **user** (not Claude) as the verify/approval point.
- **SP Phases A–C codified + wired into the harness** and **proven live on RDQ (JOB0023)**: 4
  gate-verified deliverables (Home + 3 articles), copy fidelity 1.00. 3 reliability gates +
  `cc-sp-mirror` driver + `cc-verify-sp` deterministic (non-self-closable) close-gate.
- **Level 2 CLOSED at proof-of-capability.** Client-tenant redeploy reframed as a **human dev
  handoff** (pages stay in the C&C build tenant; client reviews via screenshare; approved → C&C dev
  deploys manually into the client env). The autonomous loop (`cc-dispatch.service`) left INACTIVE.

## 2026-06-14 — JOB0024: large-site guardrails

Source: `HANDOFF_JOB0024_GUARDRAILS.md`.

- Real large sites (RDQ audit = 482 pages) convert safely: triage → operator approves scope → build
  in small waves → every page backed up before overwrite → deterministic per-page gate → operator
  reviews only exceptions. Locked defaults: `triageKeepMonths` = 18, complexity cap =
  `heavyWebpartCap`. This card FLAGS publishing/list-driven pages (rebuild = sibling card JOB0024-109
  content-type coverage). Guardrails DONE 2026-06-14. **NEVER point capture at MDLZ / a client tenant.**

## 2026-06-15 — SP autonomous batch management (Phases 1–4)

Source: `handoffs/handoff_batch_mgmt_phases.md` + `BACKLOG.md`.

- Extends the SP pipeline to handle sites >10 pages autonomously — one approval gate at intake, one
  sign-off at handover, everything in between is O/C (no mid-job gates, priority-first ordering).
- Phases 1–4 shipped: page scoring/tiering, Teams notify, tier-ordered batch runner (non-fatal),
  handover report. 17-stage pipeline.

## 2026-06 — Immersive site builder (JOB0019) — PARKED

Sources: `HANDOFF_HOMEPAGE_MIRROR.md`, `docs/features/feature-request-Immersive site builder.md`.

- Brief-driven immersive-website generator. Decision `#95`: build LOCALLY first, harness into O/C
  later. Local proofs exist (`codecraft-immersive` hand-built example; `codecraft-studio` generator,
  proven on 2 tonally-opposite briefs, both rubric-PASS on procedural media). **All paused per
  Sukaimi 2026-06-14** pending a perf fix (self-host webfonts) + supervised Higgsfield media pass.

---

## Superseded working docs (captured, then removed)

The following transient docs were self-declared ARCHIVED/COMPLETE and named their successors; each
is captured above and was removed in the 2026-07-19 consolidation:

- `HANDOFF_LEVEL1_TEMP.md` — SP classic→modern L1; ARCHIVED 2026-06-14, superseded by SP Phases A–C.
- `HANDOFF_RAILS_TEMP.md` — O/C-independent pipeline rails 1-3; ARCHIVED 2026-06-14.
- `HANDOFF_JOB0017_TEMP.md` — 12×12 themes/layouts; JOB0017 CLOSED.
- `HANDOFF_phase1-3_TEMP.md` — Web/EDM Phase 1→3; marked TEMPORARY, work delivered.
- `handoffs/handoff_batch_mgmt_phases.md` — SP batch mgmt phase plan; shipped 2026-06-15.
- `handoffs/HANDOFF_HOMEPAGE_MIRROR.md` — SP resume-state (SP DONE, immersive PARKED, verify-at-intake).
- `handoffs/HANDOFF_JOB0024_GUARDRAILS.md` — JOB0024 large-site guardrails; DONE 2026-06-14.
- `ux-audit-bot-experience.md`, `ux-copy-bot-rewrite.md`, `ux-implementation-status.md`,
  `ux-qa-verification.md` — the 2026-06-02 "Stone & Line" UX pass (captured above).
- `_ux-input/` — pre-gathered UX raw evidence + stale agent-prompt snapshots (`live-AGENTS.md`,
  `NEW-AGENTS.md`, `live-IDENTITY.md`, `surfaces*.txt`, `bot-samples*.txt`, `msteams_*.json5`,
  `_INDEX.md`, `agents_*`). Design intent captured above; ops code relocated to `tools/ops/`.
- `phase2-legal-DRAFT.md` — superseded by the live legal pages now at `docs/web-rail/legal/`.
- `Code_and_Craft_PRD_v1.0.md` — the original damaged Google-Docs PRD export, kept in `_archive/`
  as the historical investor snapshot (superseded by the rewritten `docs/PRD.md`).
