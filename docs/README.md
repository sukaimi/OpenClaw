# SPARK v1 — Docs Index

Internal engineering docs for **OpenClaw** / **SPARK v1** (SharePoint Autonomous Rebuild Kit) — the
autonomous SharePoint classic→modern rebuild team run by **Code&Craft** (the AI software-delivery
unit of **Code&Canvas Pte. Ltd.**). These are private internal docs; real client/infra names appear
and stay private.

**Live headline rail:** SharePoint autonomous rebuild (the `engine/` runbooks). A second **web/EDM
rail** was deprioritised 2026-06-11 and its docs are parked under `web-rail/`.

Production model roster: all 10 agents run **DeepSeek V4** (Profile A `deepseek-v4-flash` /
`deepseek-v4-pro`), surfaced to users as **Standard** (A) / **Restricted** (B).

## Map

| Path | What it is |
|------|-----------|
| `PRD.md` | Product requirements — SPARK/SP as headline, web/EDM parked. |
| `BACKLOG.md` | Single source of truth for feature/platform builds (P0–P3 + recent Done). |
| `JOBS_REGISTRY.md` | Pointer to the canonical server jobs ledger (`/srv/cc-archive/REGISTRY.md`) + lifecycle/convention notes. |
| `engine/SP_PIPELINE.md` | ★ Crown-jewel runbook: the SharePoint classic→modern conversion rail. |
| `engine/SP_CLIENT_TENANT.md` | Level-2 client-tenant deployment — the manual dev handover guide (sole owner). |
| `features/` | Feature specs: `feature-request-12themesx12layouts.md` (CLOSED→repo), `feature-request-Immersive site builder.md` (PARKED), `feature-request-deniedMessage.md` (open upstream request). |
| `web-rail/` | Deprioritised web/EDM rail — local mirrors of the live landing + legal pages. |
| `_archive/` | Historical record: `HISTORY.md` (consolidated project history), `backlog-history.md` (full Done log), `Code_and_Craft_PRD_v1.0.md` (old damaged export), old snapshots. |

Root-level (outside `docs/`): `CLAUDE.md` (context-mode routing rules), `RELATED-REPOS.md` (sibling
repos map). Ops code snapshots live under `tools/ops/` — see `tools/ops/README.md`.
