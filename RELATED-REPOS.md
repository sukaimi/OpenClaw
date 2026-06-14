# Related repos & tools

OpenClaw is the project home. A few things live in **separate Git repositories** (siblings in `~/Workspace2/`, not subfolders) because they're independently versioned or deliberately kept apart. This file makes them discoverable.

## Separate repositories (siblings — own GitHub remotes)

| Repo | Location | Remote | Why separate |
|---|---|---|---|
| **codecraft-themes-layouts** | `~/Workspace2/codecraft-themes-layouts` | `github.com/sukaimi/codecraft-themes-layouts` | Distributable npm package `@codecraft/themes-layouts` (the 12×12 themes/layouts library). Its own repo so other projects can install it. Currently **parked** (consumer = the immersive builder JOB0019, also parked). |
| **openclaw-config** | `~/Workspace2/openclaw-config` | `github.com/sukaimi/openclaw-config` | Sanitized, secret-redacted mirror of the OpenClaw server config + agent `AGENTS.md`/`IDENTITY.md`. Kept separate for security (never holds live secrets). |

> Separate repos stay siblings on purpose — nesting one Git repo inside another (OpenClaw) needs submodules and causes more trouble than it's worth.

## Internal tools (inside this repo)

| Tool | Location | Purpose |
|---|---|---|
| **cc-visual-qa** | `OpenClaw/tools/cc-visual-qa` | Domain-agnostic Playwright screenshot tool for the O/C `qa-engineer` (public URLs + authed M365 SharePoint via a seeded session). Deployed to the server at `/root/.openclaw/cc-visual-qa`. Local source rsyncs from here. |
