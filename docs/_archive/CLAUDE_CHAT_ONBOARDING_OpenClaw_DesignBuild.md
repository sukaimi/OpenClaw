# OpenClaw Onboarding & CTO Audit — Reconfiguring into an Industry-Grade Design & Build Team

> **Audience:** Claude Chat (claude.ai), acting as the reconfiguration co-pilot.
> **Author:** CTO audit, OpenClaw + agentic-AI specialist.
> **Date:** 2026-05-31. **Subject system:** OpenClaw on Hostinger `srv1330842`.
> **Goal:** Take you (Claude Chat) from zero context to fully able to help Sukaimi
> re-architect this OpenClaw install from a *creative content agency* ("Code&Craft")
> into a *full end-to-end software Design → Build → Deploy team*.

---

## ⚡ CURRENT STATE (updated 2026-05-31) — read before §1

**The migration described below has largely been EXECUTED.** This doc began as a plan; most of
Phases 0–2 are now live on `srv1330842`. Current reality:

- **Runtime:** upgraded to OpenClaw **2026.5.28**, under systemd (`openclaw-gateway.service`).
- **Build team LIVE (6 agents):** 🧭 delivery-lead (hub) · 📋 product-manager · 🏛️ architect ·
  💻 full-stack-engineer · 🔍 code-reviewer · 🚀 devops-deploy. Original 5 agents kept intact.
- **Coding engine:** OpenCode installed + `coding-agent` skill enabled.
- **Model routing via OpenRouter** (one key, switchable) — *balanced cost profile*:
  orchestration (lead/PM/engineer/devops) = `openrouter/google/gemini-2.5-flash`;
  reasoning (architect/code-reviewer) = `openrouter/anthropic/claude-sonnet-4.5`;
  OpenCode default = `claude-sonnet-4-6` (A/B pending vs a cheap coder). See the config repo's
  `MODEL_ROUTING.md`.
- **Config is version-controlled:** `github.com/sukaimi/openclaw-config` (private, sanitized).

**STILL OPEN:**
1. **Agent prompts are baseline v1.** Sukaimi is customizing each agent with HIS OWN PROCESS
   (being planned in Claude Chat). The current `AGENTS.md` files are a generic SDLC starting point —
   expect to revise each one. **This is the next major task.**
2. OpenCode code-engine **A/B** (cheap coder vs Sonnet) — not yet run.
3. Exec-approval gate formalization (Phase 3) — currently prompt-level only.
4. **Key rotation** (Anthropic/Google/Brave + the OpenRouter key, which was pasted in a chat) — pending.

> Claude Chat: when helping Sukaimi customize agents, your job is to turn his process into precise
> `AGENTS.md` rewrites (one per agent). Use the live prompts in the config repo as the baseline to edit.

---

## 0. How to use this document (read first)

You, Claude Chat, **do not have shell access** to the server. Sukaimi is your hands.
Your job is to: (a) hold the accurate mental model below, (b) reason about the target
architecture, and (c) emit **exact CLI commands and file contents** that Sukaimi copy-pastes
into an SSH session on the server. Always:

1. Output commands in fenced ```bash``` blocks, one logical step at a time.
2. When editing a config file, give the **full new file** or a precise `jq`/`python` patch —
   never a vague "add this somewhere."
3. After any change that touches agents/channels/gateway, remind Sukaimi to
   `openclaw gateway restart` (or `openclaw doctor`) and verify.
4. **Never print or ask Sukaimi to paste raw secrets** (API keys, tokens) into chat.
   Reference them by location only. Secrets currently live in plaintext on the box (see §6).
5. Make reasonable assumptions; confirm only the irreversible/expensive ones.

---

## 1. Executive summary — CTO verdict

**What this is today:** A working but *outdated* single-node OpenClaw gateway running a
**hub-and-spoke creative agency** ("Code&Craft"): one orchestrator (`main` = Account Director)
that delegates to four content specialists (content-writer, creative-director, strategist,
cybersecurity) over **Telegram only**. It is solid as a *content/marketing* org. It is **not**
structured to design, build, and ship software.

**Headline gaps for a design-&-build team:**

| # | Gap | Severity |
|---|-----|----------|
| 1 | **No engineering roles** — no PM, architect, UX/UI, frontend, backend, QA, code-reviewer, devops/deploy agents. | Blocker |
| 2 | **No coding-agent capability** — the `coding-agent` skill (Codex/Claude Code/OpenCode/Pi) is *missing*; agents can't actually write/run code in a repo. | Blocker |
| 3 | **No git/repo/CI/CD workflow** — `github` skill is ready but unused; no per-project workspace or deploy path. | High |
| 4 | **Runtime 3 months stale** — installed `2026.2.9`, latest `2026.5.28`. | High |
| 5 | **Secrets in plaintext + one shared key** — same Anthropic key in all agents' `auth-profiles.json`. | High (security) |
| 6 | **Model routing is content-tuned** — default `gemini-2.0-flash`; wrong default for code reasoning. | Medium |
| 7 | **"NEVER ask for clarification" prompt rule** — good for content, *dangerous* for engineering (silent wrong assumptions ship bugs). | Medium |
| 8 | **No observability/eval/approval gates** beyond a command-logger hook. | Medium |

**Recommendation:** Treat this as a *re-platform*, not a tweak. Keep the gateway + hub-and-spoke
pattern (it's the right shape), upgrade the runtime, swap the agent roster + prompts + models for
engineering, add coding-agent + github + per-project repos, and put approval/QA gates in the loop.
Full playbook in §7–§9.

---

## 2. Infrastructure & access

| Item | Value |
|------|-------|
| Host | Hostinger VPS `srv1330842`, Ubuntu 24.04 LTS, KVM 2 |
| Public IP | `76.13.179.220` (PTR `srv1330842.hstgr.cloud`) |
| Resources | 2 vCPU, 7.8 GiB RAM (3.6 free), 96 GB disk (47 GB free) |
| SSH | `ssh root@76.13.179.220` (key-based). Host key rotated 2026-05-31 — already re-trusted. |
| Node / npm | Node `v22.22.0`, npm `10.9.4` |
| OpenClaw | installed CLI `2026.2.9` at `/usr/lib/node_modules/openclaw/openclaw.mjs`; repo at `/root/openclaw` (v2026.2.3) |
| Gateway proc | `openclaw-gateway`, **not** PM2-managed, up since May 22, localhost-only |
| Other dirs | `/root/openclaw-enterprise`, `/root/telegram-bot` (out of scope) |

**Resource note:** 2 vCPU / 8 GB is fine for orchestration + delegating builds to coding-agents,
but heavy local builds (large `npm install`, Docker) will be tight. Plan to either bump the VPS or
push actual builds to ephemeral CI / a build host. Disk at 52% used — watch it.

---

## 3. OpenClaw mental model (how the platform works)

OpenClaw is a self-hosted, multi-agent gateway ("like tmux for agents"). Core concepts:

- **Gateway** — a long-running local service (ports `18789` control / `18792`), bound to
  **loopback only**, token-authed. All agent turns route through it. Also exposes an
  **OpenAI-compatible `/chat/completions` HTTP endpoint** (currently enabled).
- **Agents** — named personas. Each has:
  - an **identity** (name + emoji),
  - a **workspace** dir (`~/.openclaw/workspace[-<name>]`) — the agent's CWD + memory + files,
  - an **agent dir** (`~/.openclaw/agents/<name>/agent`) — holds `auth-profiles.json` (API keys)
    and session state,
  - a **model** (per-agent override, else the global default + fallbacks),
  - optional **routing rules** (map channel/account/peer → agent).
- **`AGENTS.md`** — the agent's **system prompt / operating manual**, stored at the workspace
  root. This is where persona, responsibilities, delegation rules, and output format live.
  (Other workspace files: `IDENTITY.md`, `SOUL.md`, `USER.md`, `BOOTSTRAP.md`, `TOOLS.md`,
  `HEARTBEAT.md` — supporting context the agent reads.)
- **Delegation** — the orchestrator spawns sub-agents with the **`sessions_spawn`** tool
  (NOT the `message` tool). `agentToAgent` + `subagents.allowAgents` gate who can call whom.
- **Channels** — messaging frontends (telegram | whatsapp | discord | slack | signal | imessage |
  msteams | line | matrix | …). Each channel/account can route to a specific agent.
- **Skills** — installable CLI capabilities the agents can invoke (think: tool packs). Sourced from
  `openclaw-bundled`, `openclaw-workspace`, or ClawHub (`clawhub.com`). 16/50 ready today (§5).
- **Plugins** — channel/integration plugins (telegram enabled).
- **Hooks** — lifecycle interceptors (internal: `command-logger`, `session-memory`).
- **Cron** — scheduled agent runs (none configured).
- **Config** — single source of truth at `~/.openclaw/openclaw.json` (keys: meta, wizard, auth,
  agents, tools, messages, commands, hooks, channels, gateway, skills, plugins). Edit via
  `openclaw config get/set/unset` or carefully by hand (back it up first — there are several
  `.bak` copies already).

**Key CLI surface** (run `openclaw <cmd> --help`):
`agent`, `agents list`, `message send`, `channels list|status|add|login`, `config get|set`,
`skills list`, `cron`, `gateway`, `health`, `doctor`, `logs`, `devices`, `hooks`, `dashboard`.

---

## 4. Current state — the "as-is" agency

**Org shape:** hub-and-spoke. `main` is the front door; it triages and delegates via `sessions_spawn`.

| Agent | Emoji | Model | Role (from its `AGENTS.md`) |
|-------|-------|-------|------------------------------|
| **main** (*Account Director*) | 👔 | `google/gemini-2.0-flash` | Hub. 3 modes: Personal Assistant, **CEO Advisor** ("wartime CEO of a $500M co", ends with *Commit to X / Kill Y*), Agency CEO (delegates client work). Can spawn all 4. Heartbeat 30m. |
| **content-writer** | ✍️ | `gemini-2.0-flash` | SEO blogs, web copy, captions, newsletters, proofing. |
| **creative-director** | 🎨 | `anthropic/claude-sonnet-4-5` | Graphics, mood boards, AI image gen (Gemini/Nano-Banana), brand direction. |
| **strategist** | 🧠 | `claude-sonnet-4-5` | SEO research, competitor analysis, content calendars, market research (web search). |
| **cybersecurity** (*SecBot*) | 🔒 | `gemini-2.0-flash` | Passive-only audits: SSL/TLS, DNS, headers, SPF/DKIM/DMARC, phishing. |

(`default` agent dir exists but `main` is the live default identity.)

**Shared prompt DNA (all specialists):** "report to Account Director" framing + a hard
**"CRITICAL: No Loops — NEVER ask for clarification, make reasonable assumptions and deliver"** +
"deliver first, refine on feedback." `main`'s prompt also mandates a strict final-delivery format
(verbatim agent output, single combined message).

**Config highlights (sanitised):**
- **Models:** default primary `google/gemini-2.0-flash`, fallback `anthropic/claude-sonnet-4-5`.
  Aliases: `sonnet`→claude-sonnet-4-5, `flash`→gemini-2.0-flash-exp, `gemini`→gemini-3-pro-preview.
  `maxConcurrent` agents = 4, subagents = 8. Compaction = `safeguard`.
- **Tools:** web search = **Brave** (key set), web fetch enabled. `agentToAgent` enabled for all 5.
- **Channels:** **Telegram only** — bot `@sukaimi_ai_bot`, `dmPolicy: pairing`, allowlist =
  one chat (`936727148`). Status: `ok`. (WhatsApp described in the project name but **not linked**.)
- **Gateway:** port 18789, `mode: local`, `bind: loopback`, token auth, Tailscale off,
  HTTP `chatCompletions` endpoint enabled. Node `denyCommands`: camera/screen/calendar/contacts/reminders.
- **Hooks:** `command-logger`, `session-memory` (both on).
- **Cron:** none. **Plugins:** telegram. **Skills install manager:** npm.

---

## 5. Skills inventory (tooling the agents can actually use)

**Ready (16/50)** — the relevant ones for a build team are bolded:
`clawhub`, `gemini`, **`github`** (`gh` CLI: issues/PRs/CI/api), `healthcheck`, `himalaya` (email),
**`mcporter`** (list/auth/call MCP servers), `nano-banana-*` (image gen), `nano-pdf`, `oracle`,
**`skill-creator`**, `summarize`, `telegram-send-file`, **`tmux`** (drive interactive CLIs),
`video-frames`, `wacli` (WhatsApp send to others), `weather`.

**Missing but critical for build/deploy** — must be installed:
- **`coding-agent`** — *the* enabler. "Run Codex CLI, **Claude Code**, OpenCode, or Pi Coding Agent
  via background process for programmatic control." Without it, engineering agents cannot edit/run
  real code. **Top install priority.**
- `gog` (Google Workspace) — optional, only if the team needs Docs/Sheets.
- (Browse `clawhub.com` for a `docker`, `playwright`/e2e, or cloud-deploy skill; install via
  `clawhub install <name>` or `openclaw skills install <name>`.)

> Inference: a build team's power = `coding-agent` (writes code) + `github` (PRs/CI) + `tmux`
> (runs dev servers/builds) + an MCP/deploy skill (ships it). Wire these to the engineering agents.

---

## 6. Audit findings (prioritised)

### 🔴 Critical / Blockers
- **C1 — No engineering org.** The five roles are all content/marketing. A design-&-build team
  needs (at minimum): Product Manager, Solution Architect, UX/UI Designer, Frontend Engineer,
  Backend Engineer, QA/Test Engineer, Code Reviewer, DevOps/Deploy. (§7 roster.)
- **C2 — No build capability.** `coding-agent` skill missing ⇒ agents can describe code but can't
  create a repo, run tests, or iterate. Install + wire it before anything else.

### 🟠 High
- **H1 — Secrets hygiene.** Anthropic + Google keys sit in plaintext in **every** agent's
  `~/.openclaw/agents/<name>/agent/auth-profiles.json`, and the **same Anthropic key is reused
  across all agents**. Brave + gateway token also on disk. Anyone with `/root` read access or a
  leaked backup owns them. **Action:** rotate all keys, move to env-var/`auth` injection, consider
  per-agent keys for cost attribution. (Do NOT paste keys into Claude Chat.)
- **H2 — Stale runtime.** `2026.2.9` → `2026.5.28` (3 months, many releases). Upgrade + restart.
- **H3 — No git/CI/CD/deploy path.** `github` ready but unused; no per-project workspace; no
  deploy target defined. Decide: deploy to Vercel? this VPS? client infra?

### 🟡 Medium
- **M1 — Model routing.** `gemini-2.0-flash` as global default is cost-optimised for chat, not code.
  Engineering agents should default to a strong reasoning/coding model (e.g. Claude Sonnet/Opus
  class) with a cheaper model only for trivial sub-tasks. Define a routing matrix (§7).
- **M2 — "Never ask for clarification."** Correct for one-shot marketing copy; **a liability for
  software** — silent wrong assumptions become shipped defects. Engineering agents need a
  *bounded* clarification rule (ask once, batched, only on spec-blocking ambiguity; else proceed
  with stated assumptions logged).
- **M3 — Observability/quality gates.** Only `command-logger` + `session-memory`. No eval harness,
  no mandatory code-review gate, no exec-approval policy for risky commands (deploys, `rm`, infra).
- **M4 — Single node, no process supervision.** Gateway not under systemd/PM2; a crash = silent
  outage. Put it under systemd with restart-on-failure.

### 🟢 Low / Watch
- Disk 52% used; heartbeat every 30m on `main`; one stale Telegram group session (~9 days);
  HTTP `chatCompletions` endpoint is enabled (fine on loopback — keep it off the public iface).

---

## 7. Target architecture — industry-grade Design → Build → Deploy team

Keep the **hub-and-spoke** shape; replace the roster, prompts, models, and tooling.

### 7.1 Proposed agent roster

| Agent (id) | Emoji | Suggested model | Mandate |
|------------|-------|-----------------|---------|
| **delivery-lead** (hub, replaces `main`) | 🧭 | Sonnet (reasoning) | Intake, scope, decompose, route, track, integrate, deliver. Owns the SDLC loop and quality gate. |
| **product-manager** | 📋 | Sonnet | Turn requests into a crisp spec: user stories, acceptance criteria, scope cuts, priorities. |
| **architect** | 🏛️ | Opus/Sonnet (high reasoning) | System design, tech selection, data model, API contracts, ADRs, non-functional reqs. |
| **ux-ui-designer** | 🎨 | Sonnet (+ image skill) | Wireframes, design tokens, component specs, Figma/visual direction, accessibility. |
| **frontend-engineer** | 💻 | Sonnet (coding) | Implement UI via `coding-agent` in a repo; component tests. |
| **backend-engineer** | 🛠️ | Sonnet (coding) | APIs, data layer, integrations via `coding-agent`; unit/integration tests. |
| **qa-engineer** | 🧪 | Sonnet | Test plans, e2e (Playwright), runs the suite via `tmux`, files defects. |
| **code-reviewer** | 🔍 | Opus/Sonnet | Mandatory gate: correctness, security, simplicity. Can block merge. |
| **devops-deploy** | 🚀 | Sonnet | Repo/CI setup (`github`), env/secrets, build, deploy to target, rollback. |
| **cybersecurity** (keep) | 🔒 | Sonnet | Pre-ship security review (SAST mindset, deps, headers, secrets scan). |

> Start lean if you prefer: **delivery-lead + product-manager + architect + one full-stack-engineer
> + code-reviewer + devops-deploy** covers the loop; split frontend/backend/QA as volume grows.

### 7.2 Model routing matrix (principle, not dogma)
- **Reasoning-heavy** (architect, code-reviewer, PM specs): strongest model (Opus-class for
  architecture/review; Sonnet elsewhere).
- **Coding** (frontend/backend/devops): a strong coding model; rely on `coding-agent`'s own model
  where it shells out to Claude Code/Codex.
- **Cheap/triage** (status pings, formatting): a flash/haiku-class model.
- Always set a **fallback** so a provider outage degrades gracefully.
- Verify exact available model IDs on the box with `openclaw config get agents.defaults.models`
  and the provider; pin the latest GA Claude models.

### 7.3 Delegation & SDLC loop (delivery-lead's playbook)
```
intake → PM(spec) → architect(design+contracts) → [ux-ui ∥ (frontend ∥ backend)]
       → qa(tests) → code-reviewer(gate) → devops(deploy) → delivery-lead(verify+report)
```
- Each handoff = a `sessions_spawn` with a structured brief (goal, inputs, acceptance criteria,
  repo path, branch). Sub-agents return artifacts + a status (done/blocked/needs-decision).
- Gate rule: **nothing deploys without a passing code-review + green tests.**

### 7.4 Repo & workspace strategy
- One **git repo per project**, cloned into a per-project workspace (e.g.
  `~/.openclaw/workspace-<project>` or `/srv/projects/<project>`). Engineering agents operate
  there via `coding-agent` + `tmux`.
- Use `github` skill for branch/PR/CI. Branch-per-feature, PR → code-reviewer → merge.
- Decide deploy target up front (Vercel / Fly / this VPS / client infra) and give `devops-deploy`
  the credentials via env injection — never inline.

### 7.5 Required tooling to install
`coding-agent` (critical), an e2e/Playwright skill, optionally a `docker` and a cloud-deploy skill
(check ClawHub). `github`, `tmux`, `mcporter`, `skill-creator` already ready.

---

## 8. Reconfiguration playbook (phased — relay to server)

> **Always back up first:** `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-$(date +%F-%H%M)`
> After agent/channel/gateway changes: `openclaw gateway restart && openclaw doctor`.

### Phase 0 — Safety & upgrade
1. Snapshot config + take a Hostinger backup (already weekly; trigger an on-demand one).
2. **Rotate secrets** (H1): regenerate Anthropic, Google, Brave keys in their consoles; update via
   `openclaw config set auth...` / re-run `openclaw configure`; remove plaintext from
   `auth-profiles.json`. (Sukaimi does the console steps; Claude Chat supplies the `config` commands.)
3. **Upgrade** (H2): `npm i -g openclaw@latest` → `openclaw --version` (expect ≥2026.5.28) →
   `openclaw gateway restart` → `openclaw doctor`. Watch for config migrations.
4. **Supervise** (M4): create a systemd unit for `openclaw-gateway` with `Restart=always`.

### Phase 1 — Capability
5. Install build tooling: `openclaw skills install coding-agent` (and Playwright/docker/deploy
   skills as chosen). Confirm with `openclaw skills list | grep ready`.
6. Configure `coding-agent` backend (Claude Code/Codex) + its model and auth.

### Phase 2 — Roster (do per agent; keep `cybersecurity`, retire/repurpose content agents)
7. For each new agent: `openclaw agents add <id>` (or the create flow) → set identity, workspace,
   model. Then write its `AGENTS.md` (Claude Chat drafts; Sukaimi saves to the workspace root).
8. Update the hub: rewrite `~/.openclaw/workspace/AGENTS.md` for **delivery-lead** with the SDLC
   loop (§7.3), the new team roster, the *bounded* clarification rule (replace M2), and a
   structured-brief delegation template.
9. Set `subagents.allowAgents` + `tools.agentToAgent.allow` to the new agent ids.
10. Set per-agent models + the global default/fallback per the routing matrix (§7.2).

### Phase 3 — Workflow & gates
11. Initialise the first project repo + workspace; wire `github` (auth `gh`).
12. Add a **mandatory code-review gate** in delivery-lead's prompt + an **exec-approval** policy
    for risky commands (`openclaw approvals` / gateway `denyCommands`).
13. Optional: add cron heartbeats (standup summary) and an eval/QA check before deploy.

### Phase 4 — Verify
14. Run a small end-to-end pilot ("build & deploy a one-page app") through the full loop; inspect
    `openclaw logs` + session stores; tune prompts; document runbook.

---

## 9. Security remediation checklist (do early)
- [ ] Rotate Anthropic, Google, Brave API keys + gateway token (assume current ones are burned).
- [ ] Stop storing keys in plaintext per-agent; use env injection / central `auth`; per-agent keys
      for attribution where useful.
- [ ] `chmod 600` all credential files; confirm `/root/.openclaw` is `700`.
- [ ] Keep gateway `bind: loopback` (don't expose 18789/18792 or the HTTP endpoint publicly;
      use Tailscale/SSH tunnel for remote).
- [ ] Tighten Telegram: keep `dmPolicy: pairing`, prune the allowlist, clear stale pairing requests
      (already done 2026-05-31).
- [ ] Exec-approval gate before any deploy / destructive command run by `devops-deploy`.
- [ ] Add a secrets-scan step (cybersecurity agent) to the pre-ship gate.

---

## 10. Open decisions for Sukaimi (Claude Chat: ask these up front)
1. **Lean vs full roster?** (6-agent minimal loop vs 10-agent full team.)
2. **Primary stack?** (e.g. Next.js + Vercel, or Node API + Postgres, etc.) — drives architect/devops defaults.
3. **Deploy target?** (Vercel / Fly / this VPS / client infra.)
4. **`coding-agent` backend?** (Claude Code vs Codex vs OpenCode.)
5. **Keep the content agents** (content-writer/creative-director/strategist) alongside, or retire?
6. **Budget posture?** (governs how aggressively to default to Opus-class models.)
7. **VPS sizing** — bump this box, or offload heavy builds to CI/a build host?

---

## 11. Quick reference

**Config file:** `~/.openclaw/openclaw.json` (back up before edits).
**Workspaces:** `~/.openclaw/workspace[-<agent>]/` → `AGENTS.md` is the system prompt.
**Agent auth:** `~/.openclaw/agents/<agent>/agent/auth-profiles.json` (secrets — handle with care).
**Common commands:**
```bash
openclaw agents list                      # roster + models + workspaces
openclaw skills list                      # capability inventory (look for ✓ ready)
openclaw skills install coding-agent      # add build capability
openclaw channels list|status             # messaging frontends
openclaw config get agents                # full agents config block
openclaw config set <path> <value>        # edit config safely
openclaw message send --channel telegram --target <chatid> --message "..."
openclaw gateway restart && openclaw doctor && openclaw health
openclaw logs                             # gateway logs
```
**Current default channel target (Sukaimi's Telegram):** chat id `936727148` (`@sukaimi_ai_bot`).

---

*End of onboarding. Claude Chat: confirm the §10 decisions, then drive Phases 0→4 in §8,
emitting exact commands/files for Sukaimi to run. Prioritise C1/C2 (roster + coding-agent) and
H1/H2 (secrets + upgrade) first.*
