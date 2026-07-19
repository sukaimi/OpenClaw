# SPARK v1 — Feature Backlog

Single source of truth for **feature/platform builds** (NOT client jobs — those live in `JOBS_REGISTRY.md` / the Kanban).

**How this stays current:** every time Sukaimi asks for something, it gets added here and the whole list is re-sorted by priority *before* work starts. Shipped items move to **Done**.

Tiers: **P0 now · P1 next · P2 soon · P3 later · Done**

_Last updated: 2026-06-15 — SP Phases 1–4 autonomous batch management DONE. SP client-tenant redeploy BUILT (Graph-native). BL-004 DONE (live Telegram test passed)._

---

## P0 — now
_(clear)_

## P1 — next
- **JOB0019 · Immersive site builder** — #95 DECIDED 2026-06-14: build **LOCALLY first**, integrate/harness into O/C later. Unblocked (pending build-scope confirmation). Consumes the 12×12 themes/layouts library (JOB0017, now closed).
- **SP production-hardening forward backlog** (see memory `project_sp_level2_access_model`): (1) ✅ Verify-at-intake automation DONE (operator-assisted); (2) client-tenant redeploy — **human dev handoff** (pages stay in C&C build tenant; client reviews via screenshare; approved → C&C dev deploys manually into client env); `docs/engine/SP_CLIENT_TENANT.md` = dev reference; (3) content-type coverage (built/unit-tested, needs live calibration on reference site); (4) ✅ large-site guardrails DONE (live-proven); (5) ✅ autonomous batch management DONE 2026-06-15 (Phases 1–4: scoring, notify, tier-ordered batch runner, handover).

## Done (recent)
- **SP autonomous batch management (Phases 1–4)** ✅ DONE 2026-06-15 — scoring/tiering, Teams notify, tier-ordered batch runner, handover report (17-stage pipeline).
- **SharePoint builder hardening + first end-to-end run** ✅ DONE 2026-06-14 (pivot 2026-06-11 → delivered). SP classic→modern pipeline codified + wired into O/C (Phases A–C) and **proven live on RDQ (JOB0023)**. **Level 2 closed at proof-of-capability.**
- **JOB0017 · 12×12 themes/layouts library** ✅ CLOSED — feeds JOB0019; the SP builder does NOT use it.

> Full historical Done log (all early SP + web/EDM builds, BL-001…BL-015) → `_archive/backlog-history.md`.

## P2 — soon
_(SP-rail items land here as the hardening run surfaces them)_

## P3 — later (web/EDM rail — deprioritised 2026-06-11)
- **BL-005 · Stripe LIVE activation** — was the sole web-funnel launch gate; deferred with the whole web/EDM rail.
- **BL-016 · Email deliverability (M365 DKIM for codeandcraft.ai)** — _downgraded 2026-06-08 (Sukaimi: not a hard blocker — mail still delivers; only strict M365 receivers quarantined). DNS is DONE + verified; finishing = the one Defender toggle whenever Microsoft's cache clears, no rush._ — client deliveries from `hello@codeandcraft.ai` (via Graph) currently pass **SPF** but have **no M365 DKIM** (`selector1/2._domainkey` absent) and DMARC `p=none`. New-domain + zip attachment + link → lands in **Junk/Quarantine** at strict receivers (surfaced by JOB0010 to a nowthatsfresh.com M365 mailbox — accepted, no bounce, but not in inbox). Affects EVERY client delivery → **pre-launch blocker.** Fix: add the 2 DKIM selector CNAMEs (Hostinger API) + enable DKIM signing in M365 Defender (user admin action); consider DMARC `p=quarantine` later + a sender-reputation warm-up. _status (2026-06-08): **DKIM CNAMEs CORRECTED to M365's exact values + live on authoritative NS** — selector1/2._domainkey → `...codeandcanvas.n-v1.dkim.mail.microsoft` (NOT the old `.onmicrosoft.com` format; Defender's error gave the exact targets). Gotchas: M365 now uses the newer `n-v1.dkim.mail.microsoft` DKIM target; Hostinger `overwrite:false` CONFLICTS (422) on an existing record — must DELETE+add to UPDATE. **PENDING: Sukaimi retries the Defender DKIM toggle after DNS cache clears (~15-60 min)** → then re-test deliverability. DMARC p=quarantine = later._
- **BL-007 · EDM build path depth** — web rail is solid; the EDM build path is basic. _status: not started; deprioritised with the web/EDM rail 2026-06-11._

## P3 — later (pre-existing)
- **BL-008 · Vision pass** — multimodal Discovery on client images (deferred for soft launch; enable when real clients supply images). _status: deferred._
- **BL-009 · Higgsfield generated images** — server can't currently reach Higgsfield; future feature. _status: deferred._

_Full historical Done log moved to `_archive/backlog-history.md` (2026-07-19 consolidation)._
