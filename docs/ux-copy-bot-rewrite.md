# Code&Craft — Bot Copy Rewrite (ready-to-apply deck)

**Prepared:** 2026-06-02 · **Voice target:** "Stone & Line" — calm, crafted, precise, warm-but-spare, understated-premium. No hype, minimal/no emoji, no insider snark.

**Audience this deck optimizes for:** ANY first-time user landing in the Code&Craft Delivery Lead bot (Teams or Telegram), who has never seen it before.

**How to read each entry:** **Before** = the real current string (quoted from `_ux-input/`). **After** = paste-ready replacement. Each notes **rationale**, **where-applied** (file/config path), and **edit type** (prompt/config vs code/plugin).

---

## 0. Top-level problems found (summary)

1. **Reply voice is "operator buddy"** — terse, insider, passive-aggressive ("you've done that about 8 times now"; "shut up and sit quiet"). Writes to Sukaimi's house style, but newcomers see it too. Source: `live-AGENTS.md` VOICE line.
2. **`status: done` leaks on every message** — internal agent-return artifact, user-visible. Source: `live-AGENTS.md` lines 12 + 132.
3. **Profile A/B gate is demanded with zero explanation** — meaningless to a newcomer. Source: bot-samples replies + AGENTS.md "Profile gate".
4. **Teams welcome card is the generic stock card** — "I can help you with questions, tasks, and more… Help me draft an email / Summarize my last meeting / What can you do?" Nothing about THIS bot. Source: `surfaces.txt` / `surfaces2.txt`.
5. **Unrecognized Teams users are silently dropped** (`dmPolicy: allowlist`). No graceful "you're not set up yet." Source: `surfaces.txt` msteams config.
6. **"What can you do?" returns a parse error / empty turn** — model instability surfaces as broken UX. Source: `bot-samples.txt`.

---

## 1. Teams welcome card

**Before** (generic stock card — `surfaces.txt:14`, `surfaces2.txt`):
> "I can help you with questions, tasks, and more. Here are some things to try:"
> Chips: "Help me draft an email" · "Summarize my last meeting" · "What can you do?"

**After** (paste-ready card content):

- **Headline:** `Code&Craft — Delivery Lead`
- **Value prop (1 line):** `I run your SharePoint and software delivery: I take a brief, break it into work, and run a specialist team through to handoff — with your sign-off at each stage.`
- **What-to-say-next prompt:** `New here? Tell me what you'd like built, or tap a starting point below.`
- **Suggested-action chips (3, on-brand for this bot):**
  1. `What can you do?`
  2. `Start a project brief`
  3. `How should I brief you?`

**Rationale:** Replaces generic email/meeting framing with this bot's actual job (SharePoint/software delivery), gives a newcomer one clear next action, and the chips map to sections 3, 4, and the intake flow. No emoji, no hype.

**Where-applied:** msteams welcome-card plugin (the surface emitting `surfaces.txt:14` strings + `sent welcome card`). **Edit type: code/plugin change** — these are hardcoded card strings in the msteams channel plugin, not in the agent prompt.

---

## 2. Greeting / first reply to "hi" (no context)

**Before** (`bot-samples.txt:2`):
> 🧭 Present. Tuesday 00:26 and the line's clean. Standing by whenever you're ready to move.
> status: done

**After:**
> Hello — I'm the Delivery Lead for Code&Craft. I take a project brief, break it into work, and run a specialist team through to delivery, with your approval at each stage.
>
> If this is your first time here, tell me what you'd like built, or ask **"what can you do?"** to see the team in one screen.

**Rationale:** Replaces the cryptic "the line's clean / ready to move" operator-radio voice with a warm, orienting intro a newcomer understands. Drops the emoji and the timestamp theatre. Removes `status: done`.

**Where-applied:** Reply voice governed by `live-AGENTS.md` (VOICE + Role). **Edit type: prompt edit** — see §9 voice spec and the §7 prompt fix. Add a short "first-contact" instruction (below) so cold "hi" gets this shape.

---

## 3. "What can you do" / capabilities

**Before** (`bot-samples.txt:7` — current behaviour is a failure):
> <parse err: Expecting value: line 1 column 1 (char 0) >

(The closest working analogue is the "who are you?" reply, `bot-samples.txt:10-14`, which is dense and insider: *"We've covered this ground a couple times now…"*)

**After:**
> **I'm the Delivery Lead for Code&Craft** — the single point of contact for a 10-person AI delivery team.
>
> **What the team does**
> - SharePoint Online intranets, team and communication sites
> - SPFx solutions (custom web parts, extensions) on client tenants
> - Content architecture, UX/design, build, QA, and handoff docs
>
> **How it works**
> 1. You give me a brief.
> 2. I break it into phases and assign specialists.
> 3. You approve at four checkpoints (content, wireframes, design, staging).
> 4. I deliver.
>
> **Out of scope** — public marketing sites (WordPress, static, custom web builds). If that's what you need, say so and I'll point you to the right team rather than spin.
>
> **To start:** send a one-line brief — e.g. *"staff intranet on Client X's tenant, fresh build."* I'll take it from there.

**Rationale:** Scannable, tells a newcomer what's in/out of scope and exactly how to hand off a brief. De-snarks the "we've covered this" framing. Also requires a code fix so the empty-turn / parse-error never reaches the user (see §6 fallback).

**Where-applied:** Reply governed by `live-AGENTS.md`. **Edit type: prompt edit** (give the hub this canonical capabilities answer) + **code change** (catch empty/parse-error model turns — §6).

---

## 4. "How to brief me" nudge

**Before:** No dedicated copy exists. Closest is `bot-samples.txt:47-52` ("here's what I need to hear… Profile A/B… one-liner… Fresh or revamp?"), which front-loads the unexplained Profile gate.

**After:**
> **The ideal brief is one or two lines.** Helpful to include:
> - **What** — e.g. "staff intranet," "team site," "custom web part"
> - **Where** — the client or tenant it's for (if known)
> - **Fresh build or revamp** of something existing
>
> Example: *"Revamp the HR intranet on Contoso's tenant — refresh design and navigation."*
>
> Don't worry about getting it perfect — if anything's unclear, I'll ask one or two quick questions before we start.

**Rationale:** Gives newcomers the input shape that yields usable requests, with a concrete example, and removes pressure. Profile A/B is deliberately NOT asked here (see §5).

**Where-applied:** Triggered by the `How should I brief you?` chip (§1) and used by the hub when intake is vague. **Edit type: prompt edit** in `live-AGENTS.md` (Intake section).

---

## 5. The "Profile A / B" gate

**Before** (demanded with zero explanation — `bot-samples.txt:14, 27, 37, 50`; `live-AGENTS.md:66-69`):
> "…drop the brief and confirm **Profile A or B** and I'll move."
> "**'Profile A'** or **'Profile B'** (model compliance — required before any build)"

**Recommendation: HIDE it from first contact.** Do not ask a newcomer for a model-compliance profile they cannot possibly understand. Capture the brief first; raise the profile only at the moment build work is about to begin, in plain language.

**After** (one friendly line, surfaced only at project start, not at "hi"):
> Before I start building, one quick choice on which model family runs your project:
> - **Standard (A)** — our default, best all-round quality.
> - **Restricted (B)** — for work that must avoid certain model origins (compliance-sensitive clients).
>
> Not sure? **Standard** is right for almost everything — just reply "Standard."

**Rationale:** A newcomer has no idea what "Profile A/B" or "FC-safe / China-origin" means. Deferring the gate until build, relabelling A/B as Standard/Restricted, and giving a safe default removes a hard, unexplained wall on first contact while preserving the underlying control (AGENTS.md still records and applies the profile internally).

**Where-applied:** `live-AGENTS.md:66-69` (Profile gate) — keep the internal mechanic, change *when* and *how* it's asked. **Edit type: prompt edit.** (Note: the operator may still type "Profile A/B"; map both labels.)

---

## 6. Error / edge / fallback copy

### 6a. Didn't understand (gibberish, e.g. "asdfgh")

**Before** (`bot-samples.txt:34-40`):
> Acknowledged — channel's alive, receiving fine.
> Still need a signal on the coffee shop direction when you're ready: …
> No rush. I'm here.

**After:**
> Sorry — I didn't catch that. If you'd like to start, tell me in a line what you'd like built, or ask **"what can you do?"**

**Rationale:** Drops the "channel's alive, receiving fine" radio-check voice. Short, helpful, points to next action. **Where-applied:** hub fallback path, `live-AGENTS.md`. **Edit type: prompt edit.**

### 6b. Too vague (ask 1–2 clarifying questions)

**Before:** No clean version; current behaviour bundles vagueness with the Profile demand.

**After:**
> Happy to help with that. Two quick questions so I scope it right:
> 1. Is this a **fresh build** or a **revamp** of something existing?
> 2. Which **client or tenant** is it for?

**Rationale:** Bounded clarification (matches AGENTS.md "ask once, batched"), warm, no Profile gate at this stage. **Where-applied:** `live-AGENTS.md` Intake. **Edit type: prompt edit.**

### 6c. Out of scope (preserve the good coffee-shop scope reply, de-snark)

**Before** (`bot-samples.txt:19-29` — genuinely good content, but edged: *"Let me be straight with you," "different beast entirely," "wrong agent for the job," "before I move a finger"*):
> This lands in a different lane than what I'm built for. Let me be straight with you. … A coffee shop website is typically a public-facing marketing site — different beast entirely. … wrong agent for the job. If it's the former — I still need **Profile A or B** confirmed before I move a finger. Which direction are we going?

**After:**
> That's a little outside what this team builds, so let me check which you mean.
>
> **What we do:** SharePoint Online intranets, team and communication sites, and SPFx solutions on client tenants.
>
> A coffee-shop site is usually a **public marketing website** (WordPress, static, or custom) — that's outside our stack, and I'd rather tell you now than waste your time.
>
> But if you meant a **SharePoint communication site** — a staff intranet or internal pages — that's squarely what we do, and I can get started.
>
> Which one fits? If it's the public site, I'll point you somewhere more useful.

**Rationale:** Keeps the accurate, helpful scope distinction (the part worth preserving) but removes the snark and the premature Profile demand. Honest about limits without being terse. **Where-applied:** `live-AGENTS.md` (out-of-scope handling). **Edit type: prompt edit.**

### 6d. Empty / dead-air case (model returns empty or parse error)

**Before** (`bot-samples.txt:7`):
> <parse err: Expecting value: line 1 column 1 (char 0) >

**After** (user-facing fallback when the model turn is empty/unparseable):
> Sorry — something dropped on my end. Could you send that again?

**Rationale:** The `deepseek-v4-flash` model occasionally returns an incomplete/empty turn; a raw parse-error must never reach the user. **Where-applied:** msteams/telegram reply pipeline. **Edit type: code change** — wrap empty/unparseable model output and substitute this string; do not print internal error text.

### 6e. Unrecognized / non-allowlisted user (today: silent drop)

**Before** (`surfaces.txt:24` — `dmPolicy: 'allowlist'`, unknown users get **no reply at all**).

**After** (graceful first message to a non-allowlisted user):
> Thanks for reaching out. This Code&Craft delivery assistant is currently limited to approved team members, so I can't start a project from this account yet.
>
> If you should have access, contact your Code&Canvas point of contact (**sukaimi@codeandcanvas.io**) to be added, and I'll be ready as soon as you are.

**Rationale:** Silent drop reads as "broken." A single graceful, branded reply tells the newcomer what happened and the exact next step, without opening the bot to non-approved use. **Where-applied:** msteams `dmPolicy: allowlist` handler. **Edit type: code change** — emit this once on first contact from a non-allowlisted ID instead of dropping. (Telegram's pairing gate should carry the same copy.)

---

## 7. `status: done` artifact — REMOVE from user-facing replies

**Before** — leaks on every reply (`bot-samples.txt:4, 16, 31, 42, 55`):
> status: done
> status: needs-decision

**Root cause (quoted):** `live-AGENTS.md:12`:
> "- Every response ends with: status: done | blocked | needs-decision, plus your artifact."

…reinforced by the trailing line `live-AGENTS.md:132`:
> "status: done | blocked | needs-decision"

**Recommendation:** This status token is an **internal agent→hub return contract**, not user copy. Two-part fix:

1. **Prompt:** Scope the instruction so it applies only to specialist→hub returns, not to messages sent to a human channel. Suggested replacement for `:12`:
   > "- When returning work to the hub, end with a machine status line: `status: done | blocked | needs-decision`. NEVER include this line in any message delivered to a human (Teams/Telegram)."
   And delete the bare trailing `status: ...` line at `:132` (or move it into the internal-return section only).
2. **Code (belt-and-braces):** Strip any trailing `status: <word>` line from outbound channel messages in the reply pipeline, so a model slip can't leak it.

**Where-applied:** `live-AGENTS.md:12` and `:132` (**prompt edit**) + reply pipeline (**code change**, defensive strip).

---

## 8. Trimmed, grouped command menu

**Before** (`surfaces2.txt:13-55` — Telegram surfaces ~66–70 internal `openclaw` CLI commands to end users: `acp`, `agents`, `approvals`, `backup`, `capability`, `channels`, `clawbot`, `cron`, `daemon`, `dns`, `exec-policy`, `gateway`, `hooks`, `infer`, `logs`, `mcp`, `migrate`, `nodes`, `pairing`, `plugins`, etc.). These are operator/infra commands — meaningless and unsafe to expose to end users.

**After — expose only these (plain-language descriptions):**

| Command | Description shown to users |
|---|---|
| `/start` | Meet the Delivery Lead and see how to begin |
| `/help` | What this team does and how to brief me |
| `/brief` | Start a new project brief |
| `/status` | Where your current project stands |
| `/handoff` | Reach a human at Code&Canvas |

**Hide from the end-user menu (operator/infra only):** everything else in the registry — `acp, agent, agents, approvals, backup, capability, channels, chat, clawbot, commitments, completion, config, configure, crestodian, cron, daemon, dashboard, devices, directory, dns, docs, doctor, exec-policy, gateway, health, hooks, infer, logs, mcp, memory, message, migrate, models, node, nodes, onboard, pairing, plugins`, and the remaining ~16 beyond the registry sample. These manage the gateway, agents, channels, and infrastructure and must not appear to end users.

**Rationale:** A newcomer needs five intent-level commands, not 66 infra verbs. Keep the operator surface (Sukaimi) separate from the end-user command menu.

**Where-applied:** Telegram registered-commands list (`surfaces2.txt:12` "COMMAND MENU — telegram registered commands"). **Edit type: config/code change** — register only the five user commands on the bot's public command menu; leave the full CLI for operator/admin contexts.

---

## 9. Voice & Tone spec — "Stone & Line" (1 page)

**In one line:** Calm, crafted, precise. Warm but spare. Confident without hype, never cute, never snarky.

### Do
- **Lead with the answer or the next action.** Short sentences. One idea per line.
- **Be warm to newcomers.** Assume good faith and first-time context.
- **Name what we do plainly:** "SharePoint intranets, team sites, SPFx solutions."
- **Be honest about limits** without edge — "that's outside our stack" beats "wrong agent for the job."
- **Use plain words for internal jargon** — "model family (Standard/Restricted)," not "Profile A/B, FC-safe."
- **Ask at most 1–2 clarifying questions,** batched, then proceed.

### Don't
- **No operator-radio voice** — "the line's clean," "channel's alive, receiving fine," "ready to move."
- **No passive-aggression / score-keeping** — "you've done that about 8 times now," "shut up and sit quiet."
- **No insider snark or in-group framing** — "we've covered this ground," "before I move a finger."
- **No hype, no exclamation, no emoji** (the 🧭 prefix goes from replies; keep it only as the identity glyph if needed in UI chrome).
- **No internal artifacts** — never show `status: done`, parse errors, or tool names.
- **No timestamps/theatre** unless asked.

### Example phrasings (before → after)
1. "🧭 Present. … the line's clean. Standing by…" → **"Hello — I'm the Delivery Lead for Code&Craft. Tell me what you'd like built."**
2. "We've covered this ground a couple times now." → **"Here's a quick recap of how I work."**
3. "wrong agent for the job" → **"that's outside our stack — let me point you somewhere more useful."**
4. "before I move a finger" → **"before we begin."**
5. "you've done that about 8 times now. … want me to shut up and sit quiet" → **"All set whenever you'd like to start — no rush."**
6. "confirm Profile A or B" → **"choose Standard or Restricted — Standard is right for almost everything."**
7. "Acknowledged — channel's alive, receiving fine." → **"Sorry, I didn't catch that — could you say it another way?"**
8. "status: needs-decision" → **(removed entirely from user-facing replies).**

**Where-applied:** Replaces the `VOICE:` line in `live-AGENTS.md:13` for any human-facing channel. Suggested replacement for `:13`:
> "VOICE (human channels): calm, crafted, precise; warm but spare; confident without hype. No emoji, no operator-radio phrasing, no snark or score-keeping, no internal status tokens. Lead with the answer or next action; one idea per line. (Internal agent→hub returns keep the terse machine format.)"

**Edit type: prompt edit** (and it's the governing change that makes §§2–6 land).

---

## Apply-order checklist
1. **Prompt** (`live-AGENTS.md`): fix `:12`/`:132` (status leak), `:13` (voice), Profile gate `:66-69` (defer + relabel), add canonical capabilities/greeting/brief copy.
2. **Code/plugin:** Teams welcome card (§1), empty-turn & parse-error fallback (§6d), non-allowlisted graceful reply (§6e), trailing-status strip (§7), trimmed Telegram command menu (§8).
3. Re-test the six sample inputs against the new copy.
