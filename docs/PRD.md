# SPARK v1 — Product Requirements

**SharePoint Autonomous Rebuild Kit**
Internal PRD · Status: SP rail shipped and proven · Last reviewed 2026-07-19

---

## 1. Summary

SPARK v1 is an autonomous multi-agent system that migrates a classic SharePoint
intranet to a modern SharePoint site with **no human at the keyboard** between
job intake and handover sign-off. It crawls the source, tiers the pages by
importance, rebuilds them as modern web parts over Microsoft Graph, and refuses
to close the job until a fail-closed verify gate confirms the content matches the
original. It runs on the OpenClaw agent platform.

---

## 2. Problem

Classic → modern SharePoint migration is done manually today: an operator
re-authors each page by hand, one at a time. It is slow, inconsistent, and
effectively unverifiable — there is no automated proof that the modern page
actually carries the source page's content. Large intranets (dozens of pages
across multiple hubs) make this worse, and "done" usually means "someone looked
at it and it seemed fine."

**Who it's for**

- **Organisations** stuck on classic SharePoint intranets who need to move to
  modern communication sites without a hand-built, page-by-page project.
- **The agency (Code&Craft / OpenClaw)** delivering those migrations — SPARK is
  the production engine that lets one operator run a migration instead of
  authoring it.

---

## 3. What it does

A **13-stage autonomous pipeline** driven by **12 specialized agents**, from
intake to closeout. The source site is treated as strictly **read-only**; all
writes go to an isolated, assigned build site.

| # | Stage | Agent | What happens |
|---|-------|-------|--------------|
| 1 | Intake | Intake Clerk | Parse the client request, open the job card, lock the run scope. |
| 2 | Verify Access | Gatekeeper | Preflight source READ and target WRITE scopes before anything runs. |
| 3 | Capture Classic | Scout | Crawl the classic site; snapshot every page, zone, and asset. |
| 4 | Audit | Auditor | Classify assets, flag broken links and low-res images, log pain points. |
| 5 | Score & Tier | Strategist | Score pages by reach and freshness; tier them (T1/T2/T3). |
| 6 | Plan & Notify | Liaison | Post the tiered plan to Teams (informational — not a gate). |
| 7 | Migrate Images | Image Handler | Migrate usable images; flag low-res ones for rewrite or SVG swap. |
| 8 | Compose Pages | Builder | Rebuild interior pages as modern web-part sections, tier-ordered, in batches. |
| 9 | Compose Home | Builder | Rebuild the homepage. |
| 10 | Style | Stylist | Apply theme, fonts, wallpaper, and brand voice. |
| 11 | **Verify Gate** | **Inspector** | **Fail-closed.** Diff each built page's content zone against source; demand copy fidelity **1.00**. No agent can self-approve. |
| 12 | Content Tracker | Registrar | Stamp final migration status; export the 3-sheet tracker workbook. |
| 13 | Handover & Closeout | Closer | Deliver the handover report, ping the operator, archive, close the job. |

### The verify gate (the core guarantee)

The Inspector is the only agent that can pass a page, and it cannot pass its own
work. It reads the built page's canvas back from Graph and diffs the content zone
against the captured source manifest; every marker the audit recorded must
reappear. A job cannot close until **copy fidelity 1.00** is reached. This is
what makes SPARK's output trustworthy rather than self-reported.

### Honest conversion contract

Graph's `create_page` emits one rich-text web part per page inside a single-column
section — it cannot provision arbitrary OOTB web parts (Quick Links, list views,
hero). SPARK therefore rebuilds all source content as **structured HTML**
(headings, lists, tables, links) inside that web part. **Layout fidelity is
approximate; content fidelity is the contract** — and the gate reads the canvas
back, so a faked web-part claim fails. Classic lists are recreated as genuine
modern lists (create_list / create_item) that pages link to.

### Deliverables per job

Modern rebuilt pages + homepage, a branded theme, a 3-sheet Content Tracker
workbook (every asset classified: Migrate / Rewrite / Review / Archive), a
per-page QA verdict, and a Teams-native handover report with an exception summary.

---

## 4. Architecture

- **Platform:** OpenClaw multi-agent harness. The 12 agents are specialized roles
  on one config-driven orchestrator (`cc-sp-mirror`), one job config per run — no
  site-specific hardcoding.
- **Substrate:** Microsoft Graph / SharePoint REST. Source read via delegated
  session; build target is an isolated assigned site addressed by site ID.
- **Models:** all agents run on **DeepSeek V4 in production.** (Earlier design
  notes referencing Gemini 2.0 Flash / Claude Sonnet as the model roster are
  obsolete.)
- **Human touchpoints — exactly two:** (1) intake form submission and (2)
  handover sign-off. **Zero mid-job gates** — the Teams tier-plan notification is
  informational; the pipeline proceeds autonomously.
- **Safety:** source is read-only; writes are confined to the assigned build
  site; the fail-closed verify gate blocks closeout on any content shortfall;
  exceptions are logged non-fatally and surfaced in the handover, never silently
  dropped.

---

## 5. Status

- **SP rebuild rail is the live, primary product.** The pipeline is codified and
  wired into OpenClaw and has been proven end-to-end on real jobs — JOB0022
  (design-spec build, verify PASS at copy fidelity 1.00) and JOB0023 (Mondelez
  RDQ homepage + article pages).
- **Demo is live:** a public showcase replays a real 13-stage run (rebranded as
  "Crestfield Foods" / DEMO-0022) with the before/after slider, agent roster, and
  verify-gate framing. Suitable for OPC Hackathon / BUIDL_QUESTS 2026 positioning.
- Large-site batch management (scoring, tiering, batched compose, non-fatal
  exceptions, handover report) is built and proven.

---

## 6. Roadmap / parked

**Next**

- Live calibration on the next real client site with operator verification before
  trusting full autonomy (rule-of-three: RDQ was #1).
- Client-tenant redeploy hardening and verify-at-intake automation (production-
  hardening backlog from the Level-2 access work).
- Higher-fidelity layout via custom SPFx web parts (deferred design polish — does
  not affect the content-fidelity contract).

**Out of scope / parked**

- The earlier **web + EDM delivery rail** (static site + email campaigns) was
  **deprioritised on 2026-06-11** in favour of the SharePoint rail. It remains in
  TEST mode and is not part of SPARK v1's headline scope; it is mentioned here
  only so its parked status is explicit.
