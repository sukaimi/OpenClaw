# CLIENT-BUILD — build a paid client job (Code&Craft Delivery Lead)

You (the Delivery Lead) are delivering a **paid client job**. You OWN this build — orchestrate the
specialist team via `sessions_spawn`; do not just run a template. Full autonomous exec is granted.
Build in `/srv/projects/<JOB####>`, never in `~/.openclaw`.

## Inputs
- `/srv/projects/<JOB####>/brief.json` and `…/discovery/manifest-assembler/output/asset-manifest.json`
  — the client's name, email, brand, **type** (multipage_site | single_page | edm), **pages**, copy, image(s).

## Procedure
1. `cc-board move <JOB####> Build "started client build <date>"`.
2. Read the brief. Decide the real structure: for an N-page site, design N genuine pages (e.g. Home +
   About / Services / Contact) with **real copy per page written from the client's brand + brief** — not
   placeholder.
   **Call-to-action:** point the **primary CTA button** (hero CTA, and the nav/header CTA if any) at the
   brief's **`ctaUrl`** (also in the manifest). If `ctaUrl` is blank, link the CTA to the on-page contact
   section/anchor — never leave it as `#` or a dead link.
   **Images (self-contained):** the real images are **local files** at `/srv/projects/<JOB####>/assets/`
   (`img-01` = hero = the client's upload; the rest are Pexels fills), and the manifest's `images[]` give
   their **relative** paths (`assets/img-0N.jpg`). Build a `assets/` folder inside your site output and copy
   those files into it, then reference images **relatively** as `assets/img-0N.jpg` — never an external URL,
   so the site is portable. **Every page needs ≥1 real image** and the homepage hero MUST load (gate checks).
   `cc-deploy` also bundles `assets/` as a safety net. If `images[]` is empty, run `cc-assets <JOB####>` first.
3. **Spawn specialists** (sessions_spawn):
   - web → **full-stack-engineer**: produce a real, on-brand multi-page (or single-page) site. You may
     use the builder at `/srv/projects/JOB0003/build/static-web` as a base, but make it genuinely reflect
     THIS client (brand colours, real per-page copy, working nav, loading images). **Build the FULL paid
     page count** — for an N-page job there must be N genuine pages (Home + others), each with real copy.
     Write the built site into `/srv/projects/<JOB####>/build/static-web/` (NOT the engine dir).
   - edm → **full-stack-engineer**: email HTML (600px centred, tables, inline CSS, 0 scripts) written to
     `/srv/projects/<JOB####>/build/edm/output/email.html`, referencing images **relatively** as
     `assets/img-0N.jpg` (copy the job's `assets/` in alongside). `cc-deploy` then publishes a browser
     **preview** of the email (email.html served as the index); the gate verifies that preview.
     **Prefer the engine** at `/srv/projects/JOB0003/build/edm` (`tsx run.ts --manifest <asset-manifest.json>`)
     — it already emits a robust, Outlook-safe base. If you hand-build instead, follow the **Email-HTML rules** below.

   **Email-HTML rules (every EDM must follow — Outlook is the hard target):**
   - **600px centred, table-based.** Outer `<table role="presentation" width="100%">` with an inner
     `max-width:600px;margin:0 auto` container. **No** flexbox, CSS grid, `position`, or JavaScript.
   - **Inline all CSS** on the elements themselves (`style="…"`). A `<style>` block may carry media-query
     responsiveness only — never rely on it for core layout. Set explicit `width`/`height` (and `bgcolor`)
     attributes on tables, cells and images, plus `border-collapse:collapse` and `mso-table-lspace/rspace:0`.
   - **Bulletproof VML CTA** → the CTA must work in Outlook. Wrap a `<!--[if mso]> <v:roundrect …
     href="<ctaUrl>" fillcolor="…" strokecolor="…"><w:anchorlock/><center>…</center></v:roundrect>
     <![endif]-->` for Outlook, and a normal padded `<a href="<ctaUrl>">` inside `<!--[if !mso]><!-- -->
     … <!--<![endif]-->` for everyone else. **Both hrefs = the brief's `ctaUrl`.** Add the VML namespaces to
     `<html xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">` and
     the `[if mso]` OfficeDocumentSettings (AllowPNG) block in `<head>`.
   - **MSO 600px wrapper:** bracket the centred container with
     `<!--[if mso]><table … width="600" align="center"><tr><td><![endif]-->` … `<!--[if mso]></td></tr></table><![endif]-->`.
   - **Images:** keep **relative** (`assets/img-0N.jpg`) — never switch to absolute hosting. Every `<img>` needs
     `alt`, explicit `width`+`height`, and `display:block;border:0;outline:none;text-decoration:none`.
   - **Web-safe fonts** (e.g. `Helvetica,Arial,sans-serif`; serif headings via `Georgia,'Times New Roman',serif`),
     a hidden **preheader** (`display:none;mso-hide:all`), sensible padding, and a **light background** that
     stays readable (don't depend on dark-mode). Spacers use a cell with `mso-line-height-rule:exactly`.
4. **Deploy (per-job isolation — BL-002):** run **`cc-deploy <JOB####>`**. This deploys the job's built
   site to its OWN Vercel project (`cc-<job>`) and writes `/srv/projects/<JOB####>/deploy-url.txt`. Do NOT
   run raw `vercel deploy` from a shared folder — a shared alias makes verification check the wrong site.
5. **GATE — you CANNOT close the card yourself.** Run **`cc-verify-client <JOB####>`**. It deterministically
   checks the live per-job URL (200, **real page count vs paid**, no placeholder, images load) and is the
   ONLY thing that may close the card + email the client.
   - **PASS** → the gate emails the client, moves the card to Closed, and pings Sukaimi. You're done.
   - **FAIL** → the gate bounces the card to Build and pings Sukaimi with the exact reasons. FIX the real
     problem (e.g. build the missing pages, fix images), re-run `cc-deploy`, then `cc-verify-client` again.
   Never claim "verified" yourself and never `cc-board move … Closed` — the board will refuse it without the
   gate's `.verified` marker.
6. If genuinely blocked on a missing secret/decision → `cc-board move <JOB####> Build "BLOCKED: <reason>"` + ping Sukaimi.
7. **Wind down cleanly.** Once the gate has PASSed and closed the card, you are DONE: **kill any background
   processes/shell sessions you started** (e.g. via the process tool) and **end your turn**. Do NOT keep
   polling, re-checking, or leaving long-running commands alive after delivery.

Quality bar: this is a paying client. Ship something real and on-brand. The gate — not your word — decides done.
