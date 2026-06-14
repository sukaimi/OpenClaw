# cc-visual-qa — Wiring Plan (PROPOSAL — review before applying)

Domain-agnostic visual QA for the OpenClaw `qa-engineer` agent. Screenshots ANY
URL headless. Loads the seeded M365 session ONLY when `--auth` is passed; public
web/EDM URLs need no session.

## Components (this repo)

- `qa.mjs` — CLI: `node qa.mjs <url> <outPng> [--auth]`. Emits one JSON line
  `{authed,title,finalUrl,out,ok}`. Without `--auth` it never touches storageState.
- `seed.mjs` — one-time interactive M365 login (headed browser). Saves
  `~/.codecraft/sp-storage-state.json` (chmod 600).
- `cc-visual-qa.sh` — wrapper SPEC for `/usr/local/bin/cc-visual-qa` (do NOT install
  yet). Picks an output path, runs `qa.mjs`, prints its JSON.

## Seed → ship → consume flow

1. **Seed (operator, on the Mac):** `node seed.mjs` → sign in + MFA in the real
   browser → writes `~/.codecraft/sp-storage-state.json`. This file holds the
   authenticated SharePoint cookies/tokens.
2. **Ship to the server:** copy the repo + state to the VPS. The state file must
   land at `$HOME/.codecraft/sp-storage-state.json` on the server (qa.mjs reads
   `process.env.HOME`). For `root`, that's `/root/.codecraft/sp-storage-state.json`.
   ```
   # run FROM the Mac (not in this agent):
   rsync -a --exclude node_modules /Users/sukaimisukri/Workspace2/cc-visual-qa/ \
     root@76.13.179.220:/root/.openclaw/cc-visual-qa/
   ssh root@76.13.179.220 'mkdir -p /root/.codecraft && chmod 700 /root/.codecraft'
   scp ~/.codecraft/sp-storage-state.json \
     root@76.13.179.220:/root/.codecraft/sp-storage-state.json
   ssh root@76.13.179.220 'chmod 600 /root/.codecraft/sp-storage-state.json && \
     cd /root/.openclaw/cc-visual-qa && npm install && npx playwright install chromium'
   ```
3. **Consume:** the agent calls `cc-visual-qa <url> [--auth]`. PNG lands in
   `/root/.openclaw/vqa-shots/`; the JSON line tells the agent if it worked
   (`ok`) and, for `--auth` runs, whether the session was still valid (`authed`).

## Expiry / refresh

- M365 access tokens are short-lived but the storageState carries refresh tokens
  / persistent cookies, so it typically replays for **days to a few weeks** before
  re-auth is forced (driven by tenant token lifetime + sign-in frequency policy).
- There is **no headless refresh** — refreshing requires the interactive login.
- **Detection:** any `--auth` run that returns `authed:false` (final URL bounced to
  `login.microsoftonline.com` / `/_forms/` / `/signin`) means the session is dead.
  Operator re-runs `seed.mjs` on the Mac and re-ships the state file (step 1–2).
- Public-URL QA (no `--auth`) never expires — it has no session dependency.

## Conditional-Access verdict (the known risk)

**Verdict: replaying a Mac-seeded storageState from the server's IP is at real risk
of rejection, and we should NOT depend on it for authed SharePoint shots.**

Why: M365 Conditional Access commonly enforces one or more of:
- **Named-location / IP policies** — a session minted from the Mac's IP can be
  challenged or blocked when the same cookies arrive from the VPS IP.
- **Token Protection / token binding** — newer policies cryptographically bind the
  refresh token to the originating device/session; replay from another host is
  rejected outright (you'll see a login redirect, so qa.mjs reports `authed:false`).
- **Device-compliance / managed-device grants** — the VPS is not an enrolled device,
  so a compliance-gated app will refuse the replayed session.

If the tenant has none of these for this app, the replay may simply work. We can't
know without testing, and it can change silently when an admin tightens policy.

**Fallback (recommended default split):**
- **Public web / EDM URLs → run server-side** on the VPS via `cc-visual-qa <url>`
  (no `--auth`). This is the common case and has zero session risk.
- **Authed SharePoint shots → run on the Mac** with `node qa.mjs <spUrl> <out> --auth`
  (same IP that seeded the session — no CA mismatch), then **ship only the PNGs** to
  the server / job artifacts. The server never needs the M365 session at all.
- Optional middle ground: still ship the state and *try* `--auth` server-side; if a
  run returns `authed:false`, fall back to the Mac-side capture. Treat
  `authed:false` as "needs Mac capture", not as a hard failure.

This keeps the server fully functional for the majority (public) case while never
relying on a CA-fragile cross-IP session for the authed minority.

## Proposed lines to ADD to `qa-engineer/AGENTS.md` (NOT applied)

Add a "Visual QA" capability section. Suggested text:

```
## Visual QA (cc-visual-qa)

You can capture a screenshot of any URL for visual verification.

- Command: `cc-visual-qa <url> [--auth]`
- Use NO flag for public sites (standalone web pages, EDM/email preview URLs).
- Add `--auth` ONLY for M365 SharePoint pages that sit behind login.
- The command prints one JSON line: {ok,authed,title,finalUrl,out}.
  - `ok:true`  → screenshot saved at `out` (under /root/.openclaw/vqa-shots/).
  - `ok:false` → read `error`; do not claim a visual pass.
  - For `--auth` runs, `authed:false` means the M365 session expired or was
    rejected (Conditional Access). Do NOT retry blindly — report
    "M365 session needs re-seed / capture on operator machine" and attach the
    public-URL shots you CAN take. The operator re-seeds; you cannot.
- Always include the saved PNG path in your QA report so it can be reviewed.
```

## One-time operator action required (Sukaimi)

1. On the Mac, run `node seed.mjs` and complete the M365 sign-in + MFA in the
   browser window. Confirm it prints `SEED_OK -> .../sp-storage-state.json`.
2. Ship repo + state to the VPS and install Playwright there (commands in
   "Seed → ship → consume", step 2).
3. Install the wrapper on the VPS once reviewed:
   `cp cc-visual-qa.sh /usr/local/bin/cc-visual-qa && chmod +x /usr/local/bin/cc-visual-qa`.
4. Add the AGENTS.md block above to `/root/.openclaw/workspace-qa-engineer/AGENTS.md`.
5. Re-run step 1–2's state copy whenever an `--auth` run reports `authed:false`.

Nothing on the server has been changed by this preparation work.
