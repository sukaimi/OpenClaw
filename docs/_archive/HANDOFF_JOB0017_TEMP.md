> **ARCHIVED 2026-06-14 — JOB0017 CLOSED (all cards); themes/layouts library complete. JOB0019 (immersive builder) #95 decided: build LOCALLY first, harness into O/C later (see [[project_sharepoint_team_deployed]]).** Content below preserved for history.

# TEMP HANDOFF — JOB0017 · 12×12 Themes/Layouts Library

_Continuity doc for the in-flight build. Delete when JOB0017 closes. Last updated 2026-06-10._

> **✅ JOB0017 COMPLETE 2026-06-10.** Full 12×12 library: themes, layouts, canonical `--cc-` contract, 144-cell fit-map, matcher, gallery (168 screenshots + repo generator), git-installable npm package, OpenClaw skill (enabled on 3 agents), visual-QA capability (M365 seed), and the **Command Center gallery PAGE** (`SitePages/Themes-Layouts-Gallery.aspx` — 12×12 fit-map matrix + 168 thumbnails in Documents/Themes-Layouts Gallery, nav-linked under Library, render-verified). **No open cards** (all Closed/Internal QA). Library fully consumable → handoff to JOB0019 met. **Next: JOB0019 (immersive builder)** — needs its runtime-host decision + Profile-B per-project auto-apply + the generalized dispatch supervisor.

## Role & mode
Claude **observes / orchestrates / audits** the O/C team — does NOT build. Mode = **hands-on**: controlled manual dispatches via `openclaw agent --agent <id> --message "$(cat brief)"` (background), audit output, Claude assembles + pushes (server `gh` is NOT authed). Live model profile = **A / Standard (deepseek)** — JOB0017 is internal/non-FC.

## Repo (single source of truth)
- `github.com/sukaimi/codecraft-themes-layouts` (private) + local clone `~/Workspace2/codecraft-themes-layouts`
- Canonical contract = **77-token `--cc-` set** (`themes/_reference/tokens.css`; spec `/srv/projects/JOB0017/themes-spec.md`)
- Latest commit `4b6337d`

## DONE ✅ (the full library is built)
- **12/12 themes** (editorial-luxury, brutalist, soft-minimal, dark-cinematic, vibrant-energetic, organic-warm, techno-futuristic, retro-analog, corporate-trust, playful-handmade, monochrome-architectural, maximal-expressive) + `_reference` — each = full 77-token `--cc-` contract, reduced-motion, AA per spec
- **12/12 layouts** (single-scroll-narrative, magazine-grid, full-bleed-hero, split-screen, anchored-sidebar, horizontal-scroll, card-driven, long-form-story, bento-grid, showcase-gallery, landing-conversion, immersive-3d-stage) + `_reference` — structure-only, `--cc-` tokens, responsive 360/768/1280/1920, keyboard-nav, slots, reduced-motion
- `library.json` registers all; **green** (token-leak-scan 13 files, tsc, match, JSON)
- Themes spec + layouts spec both written + audited PASS. Cards 75 + 76 → Internal QA.

## REMAINING (JOB0017 open cards)
- ✅ **fit-map + match() calibration** (cards 77,100) DONE (commit 93feadc) — 144 cells rated (strong43/good52/neutral23/weak16/avoid10), goals+rationale; match() returns curated pairings, never 'avoid'
- ◑ **144-combo gallery** (cards 78,99) — screenshots generated (168 renders, 26MB, validated) + `npm run gallery` → combos/index.html DONE; combos/*.png + index.html gitignored (CI artifacts). The Command Center SharePoint gallery PAGE still needs Sukaimi's one-time **M365 login seed**.
- ✅ **distribution** DONE — package git-installable (`npm i github:sukaimi/codecraft-themes-layouts`, commit 8e5f4f3; registry publish deferred, needs npm token) + OpenClaw skill `themes-layouts` deployed & enabled on delivery-lead/architect/full-stack-engineer (commit d318881, ✓ Ready, pick.mjs functional)
- ✅ **M365 seed DONE** — session at `~/.codecraft/sp-storage-state.json` (chmod 600, local). Visual-QA capability (card 93) WORKING via `~/Workspace2/cc-visual-qa/qa.mjs` (headless authed screenshots; verified Command Center home render). Runs locally; server-side autonomous use TBD (state transfer + Conditional Access).
- ◑ **Command Center gallery PAGE (card 99)** — NOT actually gated on the seed; buildable via the app cert (upload the 168 combo PNGs to SiteAssets + create page with an img grid, same pattern as the homepage). PNGs at `~/Workspace2/codecraft-themes-layouts/combos/`.
- **Library-ready handoff to JOB0019** (card 94): npm + skill ✓; effectively consumable now (gallery page is cosmetic).
- Card 101 (neutral reference theme + layout) DONE.
- **Refinement (minor):** matcher tone-overlap is exact-word; theme.json toneWords may not match a user's vocabulary (e.g. "techno/futuristic" didn't surface techno-futuristic theme since fit-map+goal score dominated). Consider synonym/keyword expansion in pick.mjs / theme toneWords. Not blocking.

## Dispatch pattern (repeatable) + KEY LEARNING
1. write brief → scp to `/srv/projects/JOB0017/` → `openclaw agent --agent <id> --timeout 900 --message "$(cat brief)"` (background, wrap in `timeout 1000`). **Do NOT add `&`/`sleep`** — it orphans the run + loses the completion signal.
2. **BATCH SIZE ≤2 complex deliverables/turn.** deepseek-v4 via OpenRouter intermittently times out (`FailoverError: LLM request timed out`) at 4 layouts/turn; 2/turn is reliable. Themes (simpler) did 8/turn fine.
3. pull → audit (python vs `build-v2/themes/_reference/tokens.css`; for layouts also check raw-spacing-px + reduced-motion) → assemble into local repo → `npm run token-leak-scan && build && test:match` → `git commit` + `push` → `cc-board move`.

## Audit criteria
- themes: 77-token `--cc-` set exact (0 missing/0 extra), `:root` + reduced-motion, values from spec
- layouts: every `var()` → canonical `--cc-` (local runtime vars like `--tilt-x` OK), no raw hex/rgb/font-px/cubic-bezier, no raw spacing px (token fallbacks + structural widths OK), slots, breakpoints, keyboard-nav, reduced-motion

## Key paths / tooling (VPS root@76.13.179.220; sshpass pw in ~/.claude/settings.local.json)
- `/srv/projects/JOB0017/` — themes-spec.md, layouts-spec.md, build-v2/ (canonical), build-themes-rest/, build-layouts/, briefs, run logs, `.model-profile`=Standard
- SP client: `PYTHONPATH=/root/.openclaw/sp-provision /root/.openclaw/venv/bin/python` → `from spclient import SP`; board `cc-board read|move`; profiles `cc-model-profile <A|B|status>`

## Config / calibration state
Agents execute well; failures were config/coordination. 7 findings logged; 3 AGENTS.md rule-sets added; Profile B wired. Pending enablers: server gh-auth (needs Sukaimi token), JOB0017 autonomous dispatch+verify (deferred to JOB0019). See memory `project_oc_team_calibration`.
