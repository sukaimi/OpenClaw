# Feature request: `deniedMessage` for gated channels (graceful reply instead of silent drop)

**Project:** OpenClaw gateway · **Area:** channels / DM access-control
**Filed by:** Code&Canvas (Code&Craft division) · 2026-06-02

## Problem
When a channel uses `dmPolicy: "allowlist"` (or `pairing`), a message from a non-allowlisted
sender is **silently dropped** — the gateway logs `dropping dm (not allowlisted)` and sends
nothing back. To the person messaging, the bot looks **broken/dead**: no reply, no reason, no
path to get access. This is a poor first-contact experience for any gated deployment (e.g. a
Microsoft Teams bot rolled out to an org before everyone is allowlisted).

## Current behavior
The drop is decided in the core channel access layer (route resolution; reason
`channel_not_allowlisted`). It is logged but produces no outbound activity. There is **no config
option** to emit a courtesy reply, so the only workarounds today are hand-patching minified core
(fragile, security-sensitive, wiped on upgrade) or leaving users in the dark.

## Proposal
Add an **optional** per-channel string config: `channels.<id>.deniedMessage`.

- **Unset / empty (default):** current behavior — silent drop. *No change for existing installs.*
- **Set:** on the **first** inbound from a non-allowlisted sender, send this one message, then drop
  as usual. Subsequent messages from the same sender are dropped silently (no repeat).

### Example
```jsonc
{
  "channels": {
    "msteams": {
      "dmPolicy": "allowlist",
      "allowFrom": ["<aadObjectId>", "<upn>"],
      "deniedMessage": "Thanks for reaching out. This assistant is currently limited to approved team members, so I can't start a project from this account yet. If you should have access, contact your point of contact to be added."
    }
  }
}
```

## Behavior / safety requirements
- **Opt-in:** default unset = today's silent drop. Zero behavior change unless configured.
- **Rate-limited per sender:** send at most once per sender (or once per N hours) to prevent the
  bot becoming a reflective spam/amplification vector. Reuse the existing per-sender state used by
  pairing/allowlist tracking.
- **No information leak:** the message must NOT reveal allowlist contents, who is allowed, or
  internal policy details — just "you're not set up yet, here's the next step."
- **Still drops:** the sender is never admitted; `deniedMessage` only adds one courtesy reply
  before the existing drop. The security gate is unchanged.
- **Channel-agnostic:** define on the shared channel-access layer so any channel with
  `dmPolicy` (Teams, Telegram, Discord, Slack, …) can use it; Telegram's pairing gate should
  carry the same copy.

## Where it plugs in
At the access-decision point where the reason resolves to `channel_not_allowlisted` (route
resolution / channel runtime): if `config.deniedMessage` is set and this sender hasn't been
notified, enqueue one outbound reply via the channel's existing send path, mark the sender
notified, then proceed with the existing drop.

## Why it matters
Turns a "the bot is broken" experience into a clear, branded "you're not set up yet — here's how
to get access," **without weakening the allowlist**. It's the durable, upgrade-safe alternative to
hand-patching core for every gated deployment.
