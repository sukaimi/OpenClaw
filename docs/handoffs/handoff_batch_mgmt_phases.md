# Handoff: SP Batch Management — Phase Plan
**Status:** Planning / Pre-implementation
**Context:** Extends the SP Classic→Modern pipeline to handle sites >10 pages autonomously. O/C manages all steps — no human in the loop between intake and handover. Default mode: Priority-first (O/C decides migration order, client reviews at handover only).

---

## Design Principle
One approval gate at intake. One sign-off at handover. Everything in between is O/C.

No mid-job approval gates. No park-and-resume infrastructure. Client trusts O/C to prioritise correctly — they review the output, not the process.

---

## Phase 1 — Crawl Enhancement: Page Scoring
**Goal:** O/C produces a prioritised, tiered inventory after crawl — not just a raw page list.

**What to build:**
- Add scoring model to crawl phase (post-Playwright extraction)
- Score signals: nav depth, last-modified date, inbound link count (orphan detection), web-part complexity flag
- Output: scored page list written into Content Tracker with Tier 1 / 2 / 3 assignments
- Tier logic:
  - Tier 1 = top-nav pages + recently modified (last 6 months)
  - Tier 2 = secondary/linked pages
  - Tier 3 = orphans, archive, low-traffic

**Inputs:** Playwright crawl output (existing)
**Outputs:** Content Tracker with `tier`, `priority_score`, `complexity_flag` columns populated
**Depends on:** Nothing — builds on existing crawl

---

## Phase 2 — Client Notification: Teams Inform (No Gate)
**Goal:** O/C informs the client of the migration plan via Teams after scoring — informational only, no approval required.

**What to build:**
- After Phase 1, O/C sends a Teams message:
  > "I've crawled [site]. Found [N] pages. I'll migrate them in this order:
  > **Tier 1 ([N] pages):** [list] — starting now.
  > **Tier 2 ([N] pages):** [list] — follows Tier 1.
  > **Tier 3 ([N] pages):** [list] — low-priority, follows Tier 2.
  > You'll receive a progress update after each batch and a full handover report when complete."
- O/C immediately proceeds to Phase 3 — no wait, no reply parsing
- If client wants to intervene (exclude a page, change order), they reply to Teams and it is handled as an exception by the operator — not an automated flow

**Inputs:** Phase 1 Content Tracker
**Outputs:** Teams notification sent; O/C continues autonomously
**Depends on:** Phase 1, Teams send capability (cc-notify-operator)

---

## Phase 3 — Autonomous Batch Execution with Exception Handling
**Goal:** O/C processes all pages in tier order, batch by batch (10 per batch), without human gates. Exceptions are flagged and skipped — never blockers.

**What to build:**
- Batch loop: Tier 1 first, batches of 10, then Tier 2, then Tier 3
- After each batch: Teams progress ping (informational):
  > "Batch [X/Y] complete. [N] pages migrated. [E] exceptions flagged. Continuing..."
- Exception handler per page:
  - Page fails (missing asset, unsupported web-part, Graph error) → log to Content Tracker as `Exception - [reason]`
  - O/C continues to next page — does not halt
  - Exceptions surfaced at handover, not mid-run
- Last batch of last tier → trigger Phase 4

**Inputs:** Phase 1 Content Tracker (tier-ordered queue)
**Outputs:** Built pages on target SP; Content Tracker with `Migrated`, `Exception` statuses per page
**Depends on:** Phase 2

---

## Phase 4 — Handover Report
**Goal:** Complete, honest handover. Client sees exactly what was migrated, what was skipped, and what needs follow-up.

**What to build:**
- O/C compiles handover package:
  - Migrated pages: count + preview link
  - Exception pages: page name + reason (needs manual review)
  - Tier 3 pages not yet migrated (if any, flagged as low-priority deferred)
- Handover email to client includes all four artefacts:
  - SPPKG (source file)
  - Technical instructions for dev team
  - Content Tracker (full status)
  - Preview link
  - Exception + deferred summary
- If exceptions > 0:
  > "[N] pages could not be migrated automatically. See Content Tracker for details. Reply to open a follow-up JOB."
- Kanban card → Closed

**Inputs:** Final Content Tracker (all statuses)
**Outputs:** Handover email; JOB closed on Kanban
**Depends on:** Phase 3

---

## Summary

| Phase | What | Key Output | Gate? |
|---|---|---|---|
| 1 | Page scoring + tiering | Prioritised Content Tracker | None |
| 2 | Teams inform | Client notified; O/C continues | None — informational only |
| 3 | Autonomous batch loop + exceptions | All pages migrated or logged | None |
| 4 | Handover report | Complete package to client | Client sign-off at handover |

**Build order:** 1 → 2 → 3 → 4

**Human touchpoints:** 2 only — intake form submission + handover sign-off.
**Mid-job gates:** None.
