# Code&Craft — Jobs Registry

**Lifecycle (best practice, live since 2026-06-07):** the Kanban is the **live operational view only**
— active + recently-delivered jobs. When a job is fully done (client jobs = at `cc-closeout`), it's
appended to the durable ledger and its card is **removed from the board**, keeping the board lean.

- **Live board:** SharePoint Kanban (active + just-delivered jobs). Read: `cc-board read <JOB####>`.
- **Durable ledger (canonical):** `/srv/cc-archive/REGISTRY.md` on the server — `cc-closeout` appends here + deletes the card automatically.
- **Deliverable files:** `/srv/cc-archive/<JOB>/` (bundle + manifest + brief, 90-day retention via `cc-archive-purge`).

The table below is the historical snapshot up to the 2026-06-07 board cleanup (all these were completed
and pruned from the board; they live on in `/srv/cc-archive/REGISTRY.md`).

| Job | Cards | Status | Dates | Summary |
|-----|-------|--------|-------|---------|
| FC0001  | 9  | ✅ Closed | 2026-06-02 | Command Center home-page AI search: replace Amazon Q with a **Claude Haiku `qSearchProxy`** Azure Function; provision + rotate `ANTHROPIC_API_KEY`; smoke-test canonical queries; decommission Amazon Q. |
| JOB0001 | 9  | ✅ Closed | 2026-06-01 → 06-02 | **Teams integration + SharePoint build pipeline**: msteams config/runbook, Azure Bot registration, public HTTPS gateway, `channels.msteams` wiring, GitHub Actions CI for SP provisioning, per-client site access, OpenCode coding engine, end-to-end test. |
| JOB0002 | 5  | ✅ Closed | 2026-06-01 → 06-02 | **Command Center UX refresh + bot-experience fixes**: UX refresh of Command Center; graceful first reply for non-allowlisted users; empty/parse-error reply guard; Telegram command-menu decision; durable Teams welcome card. |
| JOB0003 | 12 | ✅ Closed | 2026-06-05 → 06-07 | **Phase 1 · Web/EDM build engine** (2nd delivery line). Proven; deferred vision+Higgsfield tracked in `BACKLOG.md` (BL-008/009). Cards pruned 2026-06-07. |
| JOB0004 | 10 | 🗑️ Removed | 2026-06-07 | Phase-2 planning cards — superseded by `BACKLOG.md`; pruned. |
| JOB0005/6 | 2 | 🧪 Test | 2026-06-06/07 | Client pay/build test jobs; pruned (JOB0006 closed-out). |

## Notes
- **Prefix convention** is currently mixed: `FC####` and `JOB####` coexist. Worth standardising
  (e.g. reserve `JOB####` for client/delivery jobs, `FC####` for an internal/function series) so
  the registry stays unambiguous as volume grows.
- **Stage pipeline** (all jobs): Intake → Content Audit → Content Architecture → Wireframes →
  Design → Build → Internal QA → Staging → Production → Closed.
- Summaries are derived from card titles — refine each row with the true one-line goal as jobs close.
- Keep this file current: add a row when a new `JOB####` is opened; flip status when it closes.
