# UX audit raw material (pre-gathered — DO NOT re-fetch from the VPS)
All evidence was captured live from the production bot on 2026-06-02. Analyze these; do not SSH or call the bot.

- `live-AGENTS.md` — the Delivery Lead hub agent's live system prompt (governs voice/behavior of every reply).
- `live-IDENTITY.md` — the hub's identity line ("🧭 Delivery Lead").
- `surfaces.txt` — Teams welcome-card strings (it's the GENERIC stock msteams card), live `channels.msteams` config (dmPolicy=allowlist → unknown users are silently dropped).
- `surfaces2.txt` — full welcome-card chips ("Help me draft an email" / "Summarize my last meeting" / "What can you do?") + the ~70 `openclaw` CLI commands (Telegram surfaces ~66 of these to end users).
- `bot-samples.txt` — SIX real replies from the live bot to: "hi", "what can you do?" (returned empty/parse-error), "who are you?", "I need a website for my coffee shop", "asdfgh", "help". These show real voice + the issues.

## Known facts (cite as needed)
- Channels: Microsoft Teams (just live) + Telegram. Hub agent id = `main`, runs `openrouter/deepseek/deepseek-v4-flash` (occasionally returns "incomplete turn" / empty — see the "what can you do?" sample).
- Every reply leaks a trailing `status: done` / `status: needs-decision` line (internal artifact, user-visible — confirmed in Teams too).
- New Teams users who aren't allowlisted are SILENTLY DROPPED (no reply at all); Telegram uses a "pairing" gate.
- Brand: "Code&Craft" = autonomous AI software-delivery unit of agency "Code&Canvas". Voice target = "Stone & Line": calm, crafted, precise, understated-premium; no hype, minimal emoji.
