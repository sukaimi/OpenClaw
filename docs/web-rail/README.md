# Web/EDM Rail — DEPRIORITISED 2026-06-11

This rail (static web + EDM funnel: CRO landing page → Tally form → Stripe → O/C build → delivery)
was **deprioritised on 2026-06-11** in favour of the live **SharePoint autonomous-rebuild rail**
(`docs/engine/`). Nothing here is an active build target.

The files below are **local mirrors of live assets**, kept for reference:

- `landing/index.html` — source-of-truth copy of the CRO landing page deployed to
  `request.codeandcraft.ai` (`/var/www/request`). Funnel is TEST-mode — not promoted until
  BL-005 (Stripe LIVE) lands, which is itself frozen with this rail.
- `legal/terms.html`, `legal/privacy.html` — local mirror of the live legal pages at
  `teams.codeandcraft.ai/legal/*`. Brand = **Code&Craft**, legal entity = **Code&Canvas Pte. Ltd.**
  (correct usage — the service brand vs the registered company).

Frozen backlog items for this rail (BL-005 Stripe LIVE, BL-007 EDM depth, BL-016 DKIM) are tracked
in `docs/BACKLOG.md` under the P3 web/EDM section. The rail's ops code snapshots are under
`tools/ops/`. Full history: `docs/_archive/HISTORY.md`.
