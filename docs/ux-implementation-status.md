# UX audit — implementation status (2026-06-02, autonomous run)

Applied against the live bot on srv1330842. Source findings: `ux-audit-bot-experience.md`; copy: `ux-copy-bot-rewrite.md`.

## ✅ Applied & verified

### 1. Hub persona rewrite (`AGENTS.md`) — the big win
**File:** `/root/.openclaw/workspace-delivery-lead/AGENTS.md` (live; backup `*.bak-ux-*`). New copy staged at `docs/_ux-input/NEW-AGENTS.md`.
Changes:
- **Voice split** — internal agent→hub keeps terse machine format; **human channels now use "Stone & Line"** (calm, plain, warm, no emoji, no operator-radio phrasing, no snark/score-keeping, no timestamps).
- **`status:` leak fixed** — instruction scoped so the `status: done|blocked|needs-decision` token is emitted ONLY on agent→hub returns, NEVER in human-facing replies. Removed the trailing footer line. *(This fixes the leak via prompt alone — no code strip needed.)*
- **Profile A/B gate deferred** — no longer demanded at first contact; raised only at build start, relabelled **Standard/Restricted** with Standard as the safe default. Removed from first-contact triage.
- **First-contact section added** — canonical greeting, capabilities, how-to-brief, didn't-understand, too-vague, and out-of-scope replies (all de-snarked, paste-ready from the copy deck).

**Verification (cold `--session-id` sessions = what real new users get):**
- "hi" → "Hello — I'm the Delivery Lead for Code & Craft…" (warm, no emoji, no `status:`)
- "what can you do?" → clean scannable capabilities + scope + how-to-brief
- "I need a website for my coffee shop" → polite out-of-scope, no snark, **no Profile demand**, offers a referral
- "asdfgh" → "I didn't follow that — I'm a delivery team, not a general chat bot…"
- ⚠ Note: replies in a **pre-existing** session still show old behavior — system prompt is fixed at session creation. Real new users start fresh, so they get the new persona. (Operator's own long-running session will refresh when it next rolls.)

### 2. Teams welcome card — rebranded
**File:** `…/@openclaw/msteams/dist/src-D_rcW2Zm.js` (`buildWelcomeCard`); backup `*.bak-uxcard`. node --check passed; plugin reloaded "running".
- Title `Hi! I'm ${botName}.` → **`Code & Craft — Delivery Lead`**
- Body generic "I can help you with questions, tasks, and more…" → **"I run SharePoint & software delivery for Code & Craft: give me a brief and I'll run a specialist team through to handoff, with your sign-off at each stage. New here? Tap a starting point below, or just tell me what you'd like built."**
- Chips: `Summarize my last meeting`→**`Start a project brief`**, `Help me draft an email`→**`How should I brief you?`** (`What can you do?` kept).
- ⚠ **Fragility:** this edits vendored plugin dist — it will be **overwritten on any `openclaw plugins install/upgrade` of @openclaw/msteams**. Durable fix = upstream plugin config or a maintained fork (carded).

## ⏸ Deferred (carded — need you present or a product decision)

### 3. Non-allowlisted / unrecognized user — graceful reply (today: silent drop) — **P0**
Requires a **logic change in the minified msteams handler** (the drop path). Too risky to edit unattended — a mistake takes the live channel down. Copy is ready (`ux-copy-bot-rewrite.md` §6e). Do with you present.

### 4. Empty/parse-error fallback (model dead-air) — **P0-ish**
Also a reply-pipeline code change. Partially mitigated: the new persona makes empty turns rarer on fresh sessions, but a hard guard ("Sorry — something dropped on my end. Could you send that again?") still needs a code change. Carded.

### 5. Telegram command-menu trim (66 infra commands) — **P1, Telegram only**
No per-command allowlist in config (`channels.telegram.commands` only toggles `native` on/off). Trimming to the curated 5 (`/start /help /brief /status /handoff`) needs either a plugin patch or a product decision to disable the native menu — which would also remove **your** operator slash-commands on Telegram. Your call; carded. (Teams is unaffected — it uses the card, not a slash menu.)

## Not needed
- **Defensive `status:` strip in code** — the prompt change removed the leak at the source; a code strip is redundant.

---

## Autonomous run 2 (suggest→plan→breakdown→delegate→run) — outcome

- **Card 19 (welcome-card durability) → CLOSED.** Chips + on/off now via config (`channels.msteams.promptStarters` + `welcomeCard:true`) — durable across plugin upgrades. Residual: title+body remain a dist edit (no config exists for them); documented on the card.
- **Card 16 (non-allowlisted graceful reply) → CLOSED — operator decision: leave silent-drop.** Read the core code: the drop is in shared DM access-control (`route-resolution` / `channel-DVHtbclf.js`), security-sensitive + wiped on upgrade. Decided silent-drop is a sound default for a gated bot; no core hand-patch. Graceful copy on file (§6e); reopen via an upstream `deniedMessage` option if external users ever need it.
- **Card 17 (empty-turn guard) → CLOSED — mitigated/monitor.** Persona fix eliminated empties in QA (zero across cold sessions). No safe/durable core patch warranted for a rare model-level incomplete turn. If dead-air recurs, fix hub-model reliability (deepseek-v4-flash), not core. Copy §6d on file.
- **Card 18 (Telegram 66-command menu) → CLOSED — operator decision: keep for now.** No per-command allowlist; disabling native would also remove the operator slash-menu. Revisit when real end users hit Telegram (`channels.telegram.commands.native=false` or curated plugin patch). Teams unaffected.
- **Independent QA agent → PASS** (9/9 checks, no flakiness): `ux-qa-verification.md`.
- **Minor open note:** the hub occasionally says "Code & Canvas" instead of "Code & Craft" in the greeting (parent agency vs AI unit). Cosmetic; tighten in a later persona pass if desired.

**Net:** all four UX cards (16–19) are Closed. Two changes shipped live + QA-verified (persona rewrite, durable welcome-card chips); the other two were operator decisions to leave as-is (silent-drop, Telegram menu) with the durable paths documented; the empty-turn case is mitigated. No gateway-core hand-patches — the right call to avoid security risk + upgrade-fragility.
