# SPARK v1 — Jobs Registry (pointer)

> **The canonical jobs ledger is `/srv/cc-archive/REGISTRY.md` on the server.** This file is only a
> pointer + the lifecycle/convention notes — it does **not** try to mirror the live ledger (which
> runs to JOB0026+, while any table here would stall at the 2026-06-07 board cleanup).

## Where jobs live

- **Live board:** SharePoint Kanban (active + just-delivered jobs). Read: `cc-board read <JOB####>`.
- **Durable ledger (canonical):** `/srv/cc-archive/REGISTRY.md` — `cc-closeout` appends here + deletes
  the card automatically, keeping the board lean.
- **Deliverable files:** `/srv/cc-archive/<JOB>/` (bundle + manifest + brief; 90-day retention via
  `cc-archive-purge`).

## Lifecycle model (live since 2026-06-07)

The Kanban is the **live operational view only** — active + recently-delivered jobs. When a job is
fully done (client jobs = at `cc-closeout`), it's appended to the durable ledger and its card is
removed from the board.

**Stage pipeline (all jobs):** Intake → Content Audit → Content Architecture → Wireframes → Design →
Build → Internal QA → Staging → Production → Closed.

## Prefix convention

`FC####` and `JOB####` currently coexist. Worth standardising — e.g. reserve `JOB####` for
client/delivery jobs and `FC####` for an internal/function series — so the registry stays unambiguous
as volume grows.

_Early job history (FC0001, JOB0001–JOB0006) is summarised in `_archive/HISTORY.md`; the full record
lives in the server ledger above._
