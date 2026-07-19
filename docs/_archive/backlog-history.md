# SPARK v1 — Backlog History (closed / Done log)

The long historical **Done** log split out of `docs/BACKLOG.md` on 2026-07-19 to keep the active
backlog focused on P0–P3. Chronological record of shipped feature/platform builds. Most of these
belong to the **web/EDM rail (deprioritised 2026-06-11)** or the SharePoint rail's early build-out.

---

## SharePoint rail

- **SharePoint builder hardening + first end-to-end run** — DONE 2026-06-14 (pivot 2026-06-11 →
  delivered). SP classic→modern pipeline codified + wired into O/C (Phases A–C: 3 reliability gates +
  `cc-sp-mirror` driver + `cc-verify-sp` deterministic close-gate) and **proven live on RDQ (JOB0023)**
  — 4 gate-verified deliverables (Home + 3 articles), copy fidelity 1.00. **Level 2 closed at
  proof-of-capability.** Memory: `project_sp_pipeline_codification`, `project_sp_level2_access_model`.
- **JOB0017 · 12×12 themes/layouts library** — CLOSED (all cards). Feeds JOB0019; the SP builder does
  NOT use it. Library lives in repo `codecraft-themes-layouts`.

## Web/EDM rail (deprioritised 2026-06-11)

- **Wrong-email recovery: cc-resend + cc-bounce-watch** (2026-06-08) — `cc-resend <JOB> <email> [--dry]`
  re-sends an already-delivered job (live URL + source zip, reuses the gate's `deliver()`) to a
  corrected address, no rebuild; updates brief email, notes card, pings op, clears `.bounced`.
  `cc-bounce-watch [--dry]` (cron */30m) scans hello@ for NDRs and flags the matching active job
  (`.bounced` marker, op ping). Proven: caught JOB0010's real bounce to `sukaimi@nowthatsfresh.com`.
  Limitation: only catches invalid mailboxes (bounces); valid-but-wrong needs the client to reach out.
- **BL-015 · Form page-count UX + type-safe pricing** (2026-06-07) — fixes the contradiction where a
  client could pick "Single web page" + 3 pages. Server (done, proven): `/cc/pay` takes `type` and
  forces 1 page for single-page/EDM, parses count as first integer in `pages`, backward-compatible if
  `type` absent; `cc_go.map_type()` tolerant mapper. Tally form: options set + redirect updated;
  progressive disclosure + price-anchoring to kill checkout bill-shock.
- **CRO landing page** (2026-06-07) — `https://request.codeandcraft.ai` LIVE (deferred JOB0004
  front-door). Warm single-page CRO; CTA → Tally form; within-24h claim; honest early-access note;
  live slots from `availability.json`; legal footer; sticky mobile CTA. Static HTML at `/var/www/request`
  (local: `docs/web-rail/landing/index.html`), nginx vhost + Let's Encrypt, DNS via Hostinger API.
  **Funnel TEST-mode — don't promote until BL-005 Stripe LIVE.**
- **BL-007 · EDM rail hardened** (2026-06-07) — engine EDM template emits a bulletproof VML CTA
  (Outlook `v:roundrect`+`anchorlock` + gated `<a>` fallback); Outlook-safe wrapper, inline CSS,
  preheader. "Email-HTML rules" checklist in CLIENT-BUILD.md. 17/17 robustness + 33/33 engine tests.
- **BL-012 · Reliability automations** (2026-06-07) — `cc-verify-sweep` (cron */20m) auto-runs the
  gate on cards stuck in Build/Internal QA without `.verified`; `cc-autocloseout` (daily 03:45,
  N=14d) auto-runs `cc-closeout` on delivered jobs past the window. Both idempotent, `--dry` mode.
- **BL-006 · Legal pages finalized** (2026-06-07) — Terms (11 sections) + Privacy (5 sections) for
  Code&Canvas, plain-language + "not legal advice" disclaimer, dated. Live at
  `teams.codeandcraft.ai/legal/{terms,privacy}.html`; local copies now in `docs/web-rail/legal/`.
- **Agent↔tool handoff audit** (2026-06-07) — hardened tools against agent output variance:
  `cc-deploy` accepts many output dirs; `cc-verify-client` counts any internal route, excludes assets,
  requires real HTML (fixes false-FAIL); `cc-board move` normalizes stage names case-insensitively.
- **J1/J2/J3 customer journeys PASSED** (2026-06-07) — all three rails proven end-to-end
  (multipage+image, single page+Pexels, EDM+preview), O/C-built, gated, self-contained delivery.
- **BL-014 · CTA link wiring + agent wind-down** (2026-06-07) — `parse_brief` captures the form's CTA
  URL → carried in brief+manifest (`ctaUrl`); CLIENT-BUILD points primary CTA at it. Delivery Lead
  kills background processes + ends after the gate closes.
- **BL-013 · Self-contained deliverables** (2026-06-07) — images bundled INTO the site (relative
  `assets/img-NN`) instead of hosted on `teams.codeandcraft.ai`; source zip includes images.
  Dropped the hosting route entirely. Live site + client zip have zero dependency on our infra.
- **Source code at delivery** (2026-06-07) — the verify gate's delivery email attaches the site source
  zip; close-out re-sends + takes the site down. `cc-board move` accepts `JOB####`.
- **J1 customer journey PASSED** (2026-06-07) — JOB0007 (Northbrew): Tally+image → Stripe SGD30 →
  webhook → intake+cc-assets → O/C built 3 on-brand pages → isolated deploy → gate PASS → delivered.
- **Board archival lifecycle** (2026-06-07) — Kanban = live view only; `cc-closeout` appends each
  finished job to `/srv/cc-archive/REGISTRY.md` + deletes its card. One-time cleanup: board 47→0.
- **BL-011 · Images on delivered pages** (2026-06-07) — `cc-assets <JOB>` downloads client Tally
  uploads + fetches brief-relevant Pexels fills, re-hosts both, rewrites manifest `images[]`.
  Wired into `cc-intake`. Pexels needed a browser User-Agent (Cloudflare 1010).
- **BL-001 · Client verify gate** (2026-06-07) — `cc-verify-client` deterministic gate (200,
  page-count vs paid, no placeholder, image loads); `cc-board` hard-refuses Closed without
  `.verified`; agents cannot self-close. Calibrated real→PASS / fake→FAIL.
- **BL-002 · Per-client Vercel isolation** (2026-06-07) — `cc-deploy <JOB>` → own project `cc-<job>`;
  kills shared alias that corrupted verification.
- **BL-003 · Phase 3 close-out** (2026-06-07) — `cc-closeout <JOB>`: bundle → email client + feedback
  → takedown → archive (90d, daily purge cron) → case-study ping → card note. `cc-archive-purge`.
- **BL-010 · Immediate payment restored** (2026-06-07) — Tally submit → `/cc/pay` redirector → exact
  Stripe link (prefilled email); `cc-fulfil` mailbox-fallback; full pay-on-submit chain proven.
- **Phase 1 — build engine** — 10/12 gate-verified (2 deferred → BL-008/009).
- **Phase 2 — front door + money (core loop)** — Tally → parse → exact Stripe → webhook →
  `cc-fulfil` → O/C.
- **Build ownership → O/C** — client builds done by the Code&Craft AI team, not deterministic scripts.
- **JOB0006** — first O/C-agent-built client job; 3 real bespoke pages, gate-verified, then closed-out.
- **Image wiring + EDM merge-back** — real Pexels images merged into both rails' manifests.
