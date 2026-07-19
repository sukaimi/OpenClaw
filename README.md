# SPARK v1 — SharePoint Autonomous Rebuild Kit

[![OpenArena](https://openarena.to/api/badge/cmrh8qdfj000004jio6lbj0td)](https://openarena.to/en/projects/cmrh8qdfj000004jio6lbj0td)

**An autonomous multi-agent pipeline that rebuilds legacy _classic_ SharePoint intranets into modern SharePoint — end to end, with a fail-closed quality gate the agent cannot bypass.**

---

## The problem

Thousands of organizations still run **classic SharePoint** intranets: dated layouts, no
responsive design, no modern web parts, and a look that hasn't moved in a decade. Moving them
to **modern SharePoint** is almost always a manual, slow, page-by-page effort — an agency reads
the old site, re-keys the content, rebuilds each page by hand, and hopes nothing was dropped.
It's expensive, it's error-prone, and "did we actually carry over everything?" is answered by
eyeballing, not evidence.

## What SPARK does

SPARK treats the rebuild as an **assembly line of autonomous agents**. You point it at a classic
source site; it audits the site, scores every page by importance, rebuilds each page as modern
SharePoint via Microsoft Graph, restyles and rebrands it, and then **proves** — with a
content-zone diff — that the modern page carries the source's copy at full fidelity before the
job is allowed to close.

The defining feature is the **fail-closed verify gate**: an agent can never mark its own work
"done." A deterministic diff between the built page and the captured source must reach a **copy
fidelity of 1.00** before a job can advance. Self-approval is structurally impossible.

---

## The autonomous pipeline

Thirteen stages run in order. Human involvement is limited to two touchpoints — submitting the
intake brief and signing off at handover. Everything between is autonomous.

| # | Stage | What happens |
|---|-------|--------------|
| 1 | **Intake** | A submitted intake brief is validated, clarified if needed, and turned into a job. |
| 2 | **Verify Access** | Read access to the classic source and write access to the modern build site are confirmed before any work starts. |
| 3 | **Capture Classic** | The source site is crawled and captured — pages, layout, images, and per-page content manifests. |
| 4 | **Audit** | The capture is reduced to a contract (`sp-expect.json`): pages, last-modified dates, and content markers the rebuild must satisfy. |
| 5 | **Score & Tier** | Every page is scored by importance and bucketed into Tier 1/2/3, so the most valuable pages are rebuilt first. |
| 6 | **Notify** | A tier breakdown is posted to the team channel — informational, not a gate. |
| 7 | **Migrate Images** | Source brand/logo/content imagery is downloaded and re-uploaded into the modern site's asset library. |
| 8 | **Compose Pages** | Pages are rebuilt in tier order, in batches, as native modern web parts via Microsoft Graph. A failed page is logged and skipped — the run never aborts. |
| 9 | **Compose Homepage** | The homepage is composed separately with its hero, quick links, and news layout. |
| 10 | **Style & Brand** | Site wallpaper, header, and brand theme are applied to match the source's identity. |
| 11 | **Verify Gate (fail-closed)** | A per-page diff compares the built page's content against the captured source manifest. **Copy fidelity must reach 1.00.** The agent cannot self-close — this gate is the only path forward. |
| 12 | **Content Tracker** | A multi-sheet `content-tracker.xlsx` is generated (pages sorted by tier and priority) as the migration record of what moved and its status. |
| 13 | **Handover & Closeout** | A handover summary is produced, the client is notified, artifacts are archived, and the job card is closed. |

### Why the gate matters

Autonomous agents are prone to declaring victory. SPARK removes that failure mode by making
completion a **measured** event, not a claimed one. The verify gate diffs actual built content
against the captured source; anything short of full copy fidelity keeps the job open. It is the
difference between "the agent says it's done" and "the content demonstrably matches."

---

## The demo (`spark-demo/`)

`spark-demo/` is a **Next.js showcase plus an interactive sandbox** that walks through a real
rebuild without touching any live system.

- It is a **canned replay of a real rebuild** — there is **no live Microsoft 365 connection, no
  credentials, and no network calls**. Every stage, score, and diff is served from static
  fixtures, so it runs anywhere and is safe to share.
- The sample organization, **"Crestfield Foods," is fictional** — used purely to make the replay
  concrete.
- The sandbox steps through all thirteen stages, streams a live-style console, shows the tier
  scoring, and reveals the verify gate reaching copy fidelity 1.00.

### Run the demo locally

```bash
cd spark-demo
npm install   # first time only
npm run dev   # http://localhost:3000
```

Routes: `/` (showcase / landing) and `/sandbox` (interactive replay).

---

## Tech

- **Demo:** Next.js 16 (App Router) + React 19 + Tailwind CSS v4, fully static-capable (no
  backend, no env vars, no secrets). Theme-aware light/dark with a manual toggle.
- **Pipeline:** a mixed Python + Node toolchain driving Microsoft Graph — audit, scoring, image
  migration, page/homepage composition, and the fail-closed verify gate. The engine source is
  **proprietary and not included in this public preview**; the demo is a faithful replay of what
  it produces.
- **Platform:** Microsoft Graph, scoped to read the source site and write the build site.

---

## Repo layout

```
spark-demo/    Next.js showcase + interactive sandbox (canned replay; static)
```

> This public preview contains the **demo only**. The autonomous pipeline engine is proprietary
> and kept in a private repository ahead of launch.

---

_SPARK v1 is a hackathon submission. This public preview ships the self-contained, static demo;
the pipeline engine that performs real rebuilds is proprietary and not included here._
