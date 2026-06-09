# UX Audit — Code&Craft "Delivery Lead" Bot (First-Time-User Experience)

**Auditor view:** brand-new user, not the operator. **Date:** 2026-06-02.
**Surfaces audited:** Microsoft Teams + Telegram. **Persona source:** `live-AGENTS.md` / `live-IDENTITY.md`.
**Brand voice target ("Stone & Line"):** calm, crafted, precise, understated-premium; no hype, minimal emoji.

---

## 1. First-time-user journey (what actually happens)

### Teams

1. **User is added / opens the bot.** If the user's AAD id or UPN is **not** in the allowlist, they are **silently dropped — no reply at all.**
   - Evidence: `dmPolicy='allowlist'`, `allowFrom: ['2fd30256-…', 'sukaimi@codeandcanvas.io']` (`surfaces.txt`). `_INDEX.md`: "New Teams users who aren't allowlisted are SILENTLY DROPPED (no reply at all)."
   - Newcomer's read: the bot is broken / dead. No error, no "request access," nothing.

2. **Allowlisted user sees the welcome card.** It is the **generic stock assistant card**, not Code&Craft's:
   - `"I can help you with questions, tasks, and more. Here are some things to try:"`
   - Chips: `"Help me draft an email"`, `"Summarize my last meeting"`, `"What can you do?"` (`surfaces.txt`/`surfaces2.txt`).
   - Newcomer's read: this is a generic email/meeting assistant. **Wrong mental model** — nothing signals SharePoint delivery, gates, or a 10-seat team.

3. **User taps "What can you do?"** (the card's own suggested chip).
   - Bot returns: `<parse err: Expecting value: line 1 column 1 (char 0) >` — i.e. **empty / dead air**.
   - Evidence: `bot-samples.txt` line 7; `_INDEX.md`: model "occasionally returns 'incomplete turn' / empty."
   - Newcomer's read: the one onboarding action the UI invited them to take **fails**.

4. **User says "hi".** → `"🧭 Present. Tuesday 00:26 and the line's clean. Standing by whenever you're ready to move."` then `status: done`.
   - Cryptic ("the line's clean"), gives no purpose, and leaks an internal `status:` line.

5. **User says "help".** → A wall that demands `"Profile A"` / `"Profile B"` ("model compliance — required before any build"), a project one-liner, and "Fresh or revamp?", and scolds: *"you've done that about 8 times now… let me know if you want me to shut up and sit quiet"* (`bot-samples.txt` 44–55).
   - Profile A/B is **never explained**. Tone turns passive-aggressive.

### Telegram

1. **Pairing gate** before use (`_INDEX.md`).
2. **Command menu dumps ~66 admin commands** on the end user: `acp`, `agents`, `approvals`, `backup`, `capability`, `cron`, `daemon`, `dashboard`, `devices`, `exec-policy`, `gateway`, `mcp`, `migrate`, `nodes`, `plugins`… `--- count --- 70` (`surfaces2.txt`). These are operator/infra commands, not user actions.
3. Same replies + same leaked `status:` lines as Teams.

**Net first-time outcome:** a newcomer cannot learn what this bot is, what it can/can't do, or what to say next — and on Teams a non-allowlisted user gets nothing at all.

---

## 2. Prioritized findings

| # | Issue | Sev | Surface | Why it breaks clarity/intuitiveness | Concrete fix |
|---|-------|-----|---------|-------------------------------------|--------------|
| 1 | Non-allowlisted Teams users are **silently dropped** | **P0** | Teams config | `dmPolicy='allowlist'`, `allowFrom:['…','sukaimi@codeandcanvas.io']`. No reply = "bot is dead." Zero recovery path. | Send a polite gated reply: "This workspace is invite-only — ask [owner] for access." Log + notify operator of the attempt. Never return silence. |
| 2 | `"What can you do?"` returns **empty/parse error** | **P0** | Both (model) | `<parse err: Expecting value: line 1 column 1 (char 0)>` on the card's *own* suggested chip. Dead air on first real action. | Add retry + non-empty fallback ("Give me a second — here's what I do meanwhile: …"). Never emit raw parser errors to users. |
| 3 | **Generic stock welcome card** = wrong mental model | **P0** | Teams card | `"I can help you with questions, tasks, and more"` + chips `"Help me draft an email"`/`"Summarize my last meeting"`. Implies a generic email/meeting assistant. | Replace with a Code&Craft card: one-line purpose + chips like "Start a SharePoint project", "What can you build?", "What do you need from me?". |
| 4 | **Leaked `status:` artifact** on every reply | **P1** | Both | `status: done` / `status: needs-decision` ends every sample (`bot-samples.txt` 4,16,31,42,55) and AGENTS.md line 12 mandates it. Internal protocol bleeding to users; breaks "understated-premium." | Strip the `status:` line from any user-facing channel; keep it only on the internal hub↔specialist bus. |
| 5 | **"Profile A or B" gate with no explanation** | **P1** | Both | "drop the brief and confirm **Profile A or B**" (sample 14); "model compliance — required before any build" (sample 50). AGENTS.md (28–30) shows it's an internal China-origin-model toggle. Newcomer has no way to choose. | Don't expose this to users at all — it's an operator decision (AGENTS.md: "the hub confirms it"). Default silently; if ever surfaced, explain in plain language. |
| 6 | **Passive-aggressive / insider tone** | **P1** | Both | "you've done that about 8 times now" / "want me to shut up and sit quiet" (sample 53); "We've covered this ground a couple times now" (sample 10); "the line's clean" (sample 2). | Off-brand for "calm, crafted, understated-premium." Rewrite to patient, neutral guidance. Tone must not assume a returning operator. |
| 7 | **~66 admin commands exposed** to end users | **P1** | Telegram | `acp/agents/approvals/backup/gateway/exec-policy/plugins…` `count: 70` (`surfaces2.txt`). Pure infra noise; overwhelming and dangerous-looking. | Register a tiny user-facing menu (`/start`, `/help`, `/new-project`, `/status`). Hide admin commands behind operator scope. |
| 8 | **No statement of scope/purpose** up front | **P2** | Both | Newcomer learns "what I can't do" only by tripping it — "This lands in a different lane than what I'm built for" (sample 19). Purpose arrives reactively, mid-rejection. | Lead with a one-line scope in the welcome card and in `help`: "I run SharePoint Online delivery projects (intranets, comm sites, SPFx). I don't build public marketing sites." |
| 9 | **Cryptic "hi" reply** gives no next step | **P2** | Both | `"Present. Tuesday 00:26 and the line's clean. Standing by…"` (sample 2). No purpose, no CTA, plus timestamp noise. | First contact should state identity + one CTA: "I'm the Delivery Lead for SharePoint projects. Tell me what you need built, or tap 'What can you build?'." |
| 10 | **Persona authored only for the operator** (root cause) | **P2** | AGENTS.md | "You report to Sukaimi (the operator)… Match Sukaimi's house style" (AGENTS.md 1–14). Explains insider voice + leaked status; no guidance for an unknown first-time user. | Add a "First-contact / unknown user" section to AGENTS.md: plain-language purpose, no internal artifacts, patient tone, no Profile prompt. |

---

## 3. Top 5 highest-impact recommendations

1. **Kill the silence on Teams (config).** Replace `dmPolicy='allowlist'`-with-no-response behavior: any non-allowlisted user gets a friendly gated message + the operator gets notified. *Where: `channels.msteams` config / gating handler.* (Finding 1)

2. **Replace the stock welcome card (card).** Ship a Code&Craft card: one-line purpose + 3 on-brand chips ("Start a SharePoint project", "What can you build?", "What do you need from me?"). Removes the email/meeting mental model. *Where: Teams welcome-card definition.* (Finding 3)

3. **Stop leaking internals (persona + channel layer).** Strip `status: done/needs-decision` from all user-facing output, and remove the user-facing "Profile A/B" prompt entirely (default it server-side). *Where: AGENTS.md line 12 mandate scoped to internal bus; output filter on Teams/Telegram.* (Findings 4, 5)

4. **Make replies fail safe (model layer).** Wrap hub replies: on empty/parse-error, retry once, else return a static fallback that still states purpose. Never surface `<parse err …>`. *Where: hub reply pipeline.* (Finding 2)

5. **Add a first-contact persona block + trim the command menu (AGENTS.md + Telegram config).** New AGENTS.md section governs unknown users: plain purpose, patient neutral tone, no scolding, no Profile gate. Register only `/start /help /new-project /status` for end users; hide the ~66 admin commands. *Where: AGENTS.md persona; Telegram command registry.* (Findings 6, 7, 10)

---

## 4. Quick wins vs. larger changes

**Quick wins (config / copy / prompt edits):**
- Strip the `status:` line from user-facing channels (output filter). *(Finding 4)*
- Gated-access reply instead of silent drop on Teams. *(Finding 1)*
- Reduce Telegram command menu to a handful of user commands. *(Finding 7)*
- Rewrite the stock welcome-card copy + chips for Code&Craft. *(Finding 3)*
- AGENTS.md tone edit: remove "shut up and sit quiet", "8 times now", "the line's clean"; add one-line scope statement. *(Findings 6, 8, 9)*
- Stop prompting users for "Profile A/B"; default it. *(Finding 5)*

**Larger changes (engineering):**
- Reliability wrapper: retry + static fallback so the model never returns empty/parse-error to a user. *(Finding 2)*
- A proper first-time onboarding flow (intent capture → scope check → next step) replacing the reactive "wrong lane" rejection pattern. *(Findings 8, 10)*
- Distinct user-facing persona layer separate from the operator-facing hub prompt. *(Finding 10)*
