# TEMP HANDOFF — Code&Craft Web/EDM Delivery Line (Phase 1 → 3)

> **Status: TEMPORARY.** Delete this file once Phase 3 is delivered and signed off.
> Owner: Sukaimi. Audience: Code&Craft delivery-lead + sub-agents.
> Created during CTO planning session, 2026-06-05.

---

## 0. Why this exists (context)

Code&Craft (OpenClaw) already has a **proven SharePoint/M365 delivery rail** — that line is
considered **closed/built**; it only gets battle-tested when real SP requests arrive. No further
SP build work is in this handoff.

This handoff adds a **second delivery line**: accepting and shipping **normal static web work** —
multipage sites, single web pages, and single-page EDMs. This is the deliberate "escape SharePoint
gravity" move: Code&Craft is meant to be a general autonomous build/deploy agency, and SharePoint
was the beachhead, not the product.

**Hard scope guard: NO BACKEND.** Everything in this line is static-deliverable. If a request needs
data persistence / forms-that-save / auth, the router must classify it `needs_backend` and **flag to
a human** — never silently half-build it.

---

## 1. The 3-rail model (collapse 4 request types → 3 build rails)

| Request type        | Rail            | Toolchain                                   | "Deploy"?          |
|---------------------|-----------------|---------------------------------------------|--------------------|
| SP project          | SharePoint (DONE) | SPFx → .sppkg → Command Center            | Yes (M365)         |
| Multipage site      | **Static web**  | frontend-design / Stitch / shadcn → Vercel  | Yes (Vercel)       |
| Single web page     | **Static web** (same rail, smaller scope) | same              | Yes (Vercel)       |
| Single-page EDM     | **Email HTML**  | 600px tables, inline CSS, no JS             | No — it's an artifact |

**EDM is its own lane on purpose.** Email is NOT a small website: Outlook uses a Word render engine,
no flexbox/grid, no JS, inline styles only, 600px, dark-mode quirks. Treating an EDM as "a small site"
ships something broken in every mail client.

---

## 2. LOCKED decisions (do not re-litigate)

- **Pricing:** SGD 10 per page (flat). Deliberate soft-launch / proof price — economics revisited later.
- **Capacity cap:** 10 **total** requests per month across the whole system (soft-launch throttle).
- **Stripe fee:** ~8% on a SGD10 charge is **accepted** for soft launch.
- **Page count:** **declared by the client in the form** (drives the quote mechanically — keeps pre-pay
  cost near-zero). Bot does NOT infer page count pre-payment.
- **Quote model:** Discovery-then-quote, BUT see token-economics split in §5 — cheap scope pre-pay,
  expensive Discovery post-pay.
- **Web/EDM only via the public form. NO SP requests via the form (yet).**
- **Hosting of deployed sites:** **our (Sukaimi's) Vercel account.**
- **Web deliverable default:** deployed Vercel URL. Code-bundle export = opt-in. EDM = always `.html` + screenshot.
- **Asset sourcing:** Pexels (real stock, commercial, no attribution) + Higgsfield (generated/branded).
- **Retention:** on project close → hand client full code bundle + confirmations → **take the site down** →
  **archive 3 months** (git repo + assets + Discovery manifest, labelled JOB####) → then purge.
- **Post-project triggers:** **Telegram → Sukaimi** ("make a case study" nudge) + **email → client**
  (feedback request). Both auto-fire on close.
- **Request form hosting:** form page on **our Vercel** at `request.codeandcraft.ai`; submissions via
  **Formspree (free)**; payment via **Stripe Payment Link**. No maintained backend.

---

## 3. Full lifecycle (the line, end to end)

```
INTAKE  →  SCOPE/QUOTE  →  PAY  →  DEEP DISCOVERY  →  BUILD  →  DEPLOY/DELIVER  →  CLOSE
(form or  (cheap, free) (Stripe) (vision+copy →    (static  (Vercel URL /     (handoff bundle,
 channel)              gate     manifest)         web /EDM) .html+shot)       takedown, archive,
                                                                              triggers)
```

Channels in: **public web form** (web/EDM, Phase 2) AND **Telegram / Teams** (operator-fed, Phase 1).

---

## 4. PHASE 1 — The Build Engine  (board: JOB0003, status: Intake, AWAITING APPROVAL)

**Goal:** prove the bots can actually turn a brief into a real, good deliverable — driven via existing
channels (Telegram/Teams), **no web form / no payment yet.**

**🚦 GUARDRAIL: cards are parked in Intake. DO NOT start the build / move cards to In Progress until
Sukaimi explicitly approves the Kanban.**

JOB0003 cards (sequencing baked into card Notes):

1. **Job workspace + type taxonomy + intake schema** (P0 foundation) — per-job record: materials in /
   manifest / build out. Taxonomy: `sp_project | multipage_site | single_page | edm | needs_backend`.
2. **Request router / classifier** (P0) — classify brief → confirm if confident, ask 1–2 Qs if not,
   **lock `type` before any build**; detect `needs_backend` → flag human.
3. **Discovery — vision pass on images** (P1) — per-image JSON: subject, role(logo/hero/product/bg/icon),
   orientation, aspect ratio, focal point, contains_text, usable_as_background.
4. **Discovery — copy parse** (P1) — tone, hierarchy, sections, headline/body/CTA; EDM also: sender,
   subject line, preheader, CTA URL.
5. **Discovery brief / asset manifest assembler** (P1) — merge 3+4 → one manifest; flag `needs_gapfill`.
6. **Asset gap-fill — Pexels** (P2) — needs `PEXELS_API_KEY` → **prompt operator, never set silently.**
7. **Asset gap-fill — Higgsfield** (P2) — bespoke/branded; already connected via MCP.
8. **Build rail — static web** (P1) — multipage + single page (scope, not separate rail).
9. **Build rail — EDM** (P1) — 600px tables, inline CSS, no JS, Outlook/dark-mode safe → single `.html`.
10. **Deploy — Vercel (web)** (P1) — preview URL; production promotion stays gated to Phase 2.
11. **Deliver — EDM output** (P1) — `.html` + screenshot, optional msmtp test-send. No hosting.
12. **End-to-end dry run** (P0, **acceptance gate**) — one web brief + one EDM brief all the way through.
    Passing = Phase 1 proven, unlocks Phase 2.

---

## 5. PHASE 2 — Front Door + Money

**Goal:** a stranger can submit + pay + receive, hands-off. Build ONLY after Phase 1 gate passes.

- **Web form** at `request.codeandcraft.ai` (our Vercel, built on the static-web rail):
  - fields: type (multipage/single/EDM — **no SP**), **declared page count**, structured copy
    (per-section headline/body/CTA), image uploads (→ Formspree → store in Vercel Blob / Drive folder).
  - EDM extra fields: sender name, subject line, preheader, CTA URL.
- **Token-economics split (critical — protects against pre-payment loss):**
  - **Pre-payment = cheap scoping (near-zero tokens):** quote = declared_pages × SGD10. At most one tiny
    classify/sanity call. **NO vision calls yet.**
  - **Post-payment = deep Discovery (the expensive multimodal pass in §4 cards 3–5):** only fires after
    Stripe confirms.
- **Payment:** Stripe Payment Link, quantity = pages. **Stripe keys: prompt Sukaimi, never set silently.**
- **Capacity:** enforce **10 total requests/month** counter; reject/queue past cap with a branded message.

---

## 6. PHASE 3 — Close-out & Ops

**Goal:** clean exits; nothing lingers on our Vercel; every project feeds learning + marketing.

- **Close-out:** deliver client the full code bundle + confirmations → **take the deployed site down** →
  **archive** (git + assets + Discovery manifest, JOB####) for **3 months** → purge after.
- **Triggers on close (auto):**
  - **Telegram → Sukaimi:** "Project JOB#### closed — make a case study?" (internal, instant, actionable).
  - **Email → client:** feedback request (outward-facing, professional, paper-trail).

---

## 7. Kanban mechanism (how cards are managed)

- Board = a **SharePoint list** on the `codeandcanvas` tenant.
  - SITE: `codeandcanvas.sharepoint.com,bb3fd7ab-6331-4a11-9fb3-259577ca7bcd,151f2dd5-fded-4cb3-9142-c629434c894a`
  - LIST: `19f8055f-32c3-4262-ab05-ba28ca94ffd2`
  - Card fields: `Title`, `Stage` (Intake → … → Closed), `Notes`, `ProjectNo` (JOB####).
- Runs **server-side** on the OpenClaw box: SSH `root@76.13.179.220`,
  scripts use `/root/.openclaw/sp-provision/spclient.py` (`graph_token()`), run with
  **`/root/.openclaw/venv/bin/python`** (the venv has `msal`; system python3 does NOT).
- Helper scripts (in repo `docs/_ux-input/`): `board_read.py` (list), `phase1_cards.py` (created JOB0003),
  `kanban_move.py` / `move_card.py` (move stage: `move_card.py <itemId> <Stage> [Notes]`).
- **Inline HTTP in Bash is blocked by a context-mode hook** — put `requests` code in a file, scp it, run
  with the venv python. Do not inline `requests.get(`/`requests.post(` in a Bash command string.
- Next free project number was JOB0003 (FC0001 / JOB0001 / JOB0002 all Closed at handoff time).

---

## 8. Tools / keys / infra inventory

- **Vercel:** Sukaimi's account, `vercel` CLI authed (`/opt/homebrew/bin/vercel`). Hosts web builds + form.
- **Domain:** `codeandcraft.ai` (Teams bot icon at `teams.codeandcraft.ai`). Form → `request.codeandcraft.ai`.
- **Higgsfield:** connected via MCP (image/video gen).
- **Pexels:** needs `PEXELS_API_KEY` — **prompt Sukaimi.**
- **Stripe:** keys to be added — **prompt Sukaimi, never silent.** Payment Link model.
- **Formspree:** free tier for form submissions + uploads.
- **Email send:** `msmtp` (`~/.msmtprc` configured) for EDM test-sends + client feedback emails.
- **Telegram:** OpenClaw bot channel (operator + notifications). Teams also wired.

---

## 9. Explicitly OUT of scope (do not build)

- Any backend / database / auth / forms-that-save → classify `needs_backend`, flag human.
- SP requests via the public web form.
- Managed/ongoing hosting of client sites (sites are taken down on close; "managed hosting" is a possible
  future paid add-on, NOT now).
- Re-pricing / economics rework (SGD10/page is a deliberate soft-launch number).

---

## 10. Definition of 100% success (when to delete this file)

1. Phase 1 JOB0003 end-to-end dry run passes — a real web build deploys to Vercel AND a real EDM `.html`
   renders correctly, both from a hand-fed brief.
2. Phase 2 form live at `request.codeandcraft.ai`, a test submission flows intake → quote → Stripe pay →
   deep Discovery → build → deliver, with the 10/mo cap enforced.
3. Phase 3 close-out runs once: bundle handed off, site taken down, archived, both triggers fired.

When all three are demonstrated and Sukaimi signs off → **delete this handoff file.**

---

## 11. Observation log (Claude = observer only; o/c runs autonomously)

> Role from 2026-06-05: Claude observes and notes. Code&Craft agents run Phase 1 themselves
> (agents on box: architect, full-stack-engineer, devops-deploy, code-reviewer, product-manager, main).
> Board Stage pipeline = Intake → Content Audit → Content Architecture → Wireframes → Design →
> Build → Internal QA → Staging → Production → Closed. Engine cards use the subset
> Intake → Build → Internal QA → Closed.

| Date | Event |
|------|-------|
| 2026-06-05 | Kanban **approved**. Phase 1 **started**. JOB0003 = 12 cards (item ids 29–40). |
| 2026-06-05 | Card #1 (id 29, Job workspace + taxonomy + intake schema) moved Intake → **Build**. Other 11 remain Intake. |
| 2026-06-05 | Handed to o/c to run autonomously. Claude now observe-only. |
| 2026-06-05 | **Finding:** o/c had NO autonomous dispatch — board is passive, nothing watched it. Heartbeat OFF (HEARTBEAT.md empty). Idle ~5 days. Cron had only other-project jobs. |
| 2026-06-05 | Wired **Option B self-continuing dispatch** (see §12). Card 29 reset Build→Intake so foundation runs first. Status-pull feature added + live-tested OK. Chain self-armed + fired tick #1. |
| 2026-06-05 | **Open gate:** Delivery Lead asks which **model profile** for build work — Standard vs Restricted (model-allowlist gating). Needs Sukaimi's call before specialists build. |
| 2026-06-05 | Profile = **Standard** (Profile A; internal work, no compliance need). Persisted `/srv/projects/JOB0003/.model-profile`. Codified **DISPATCH Step 0**: confirm profile ONCE at project start, save, never re-ask. |
| 2026-06-05 | Relayed Standard → architect **built card 29 scaffold** (`/srv/projects/JOB0003/{intake,discovery,assets,build,deploy,scripts,docs}`). Tick turn was cut by a 220s timeout before close→next-tick → card 29 orphaned in Build. |
| 2026-06-05 | **Hardening:** added DISPATCH "resume-in-flight" rule — a tick finishes any in-Build (non-BLOCKED) card before claiming new Intake (self-heals interrupted ticks). Re-armed async tick to finish 29 + continue. |

---

## 12. Dispatch mechanism (Option B — self-continuing chain) — WIRED 2026-06-05

**Decision:** rejected time-based polling (wastes tokens on idle ticks). Chose **work-driven** self-continuation.

**Owner agent:** `main` = **Delivery Lead** (only agent with team-wide `sessions_spawn` allowAgents).
Delegates per card → architect (29,30) · full-stack-engineer (31–37,39) · devops-deploy (38) · qa-engineer (40).

**How it runs (no idle waste, runaway-proof):**
- Each **tick** = Delivery Lead does ONE card: `cc-board read` → claim oldest Intake card by moving it
  **Intake→Build immediately** (so Intake strictly shrinks, card never re-picked) → `sessions_spawn` the
  specialist (builds in `/srv/projects/<project>`) → on pass move QA→Closed; if stuck, leave in Build
  marked `BLOCKED:` + ping Sukaimi.
- Tick ends with `cc-board next-tick`: a **deterministic script** that schedules the next one-shot cron
  tick (`openclaw cron add … --at +1m --delete-after-run`) **only if Intake still has cards**. Drained →
  schedules nothing. ⇒ chain halts after ≤12 ticks; cannot loop idle.
- **Phase 2 live requests:** event-driven (inbound Telegram/form msg triggers the bot) — NO timer.

**Artifacts on the server:**
- `/root/.openclaw/sp-provision/board_cli.py` + `/usr/local/bin/cc-board` (read | move | next-tick).
- `/root/.openclaw/workspace-delivery-lead/DISPATCH.md` (tick protocol).
- AGENTS.md appended: DISPATCH section + STATUS-REQUEST section (backup: `AGENTS.md.bak-dispatch-*`).

**Status pull (works):** Sukaimi messages o/c on Teams/Telegram → Delivery Lead runs `cc-board read`
and replies briefly in "Stone & Line" voice (current card / closed / blocked / next). Live-tested OK.

**Board Stage values:** Intake, Content Audit, Content Architecture, Wireframes, Design, Build,
Internal QA, Staging, Production, Closed. Engine cards use subset Intake→Build→Internal QA→Closed.

**Gotchas (for whoever maintains this):** run server board scripts with `/root/.openclaw/venv/bin/python`
(has `msal`); inline `requests.get(`/`.post(` in a Bash cmd string is blocked by a context-mode hook
(put in a file + scp); cron ticks default-announce to telegram:936727148.

---

## 13. VERIFY GATE — agents cannot self-close (added 2026-06-05)

**Why:** verification of the first full Phase-1 run found the agents **systematically mark cards "Closed"
that aren't done** — they closed a gate card whose own `e2e-results.json` said FAIL, closed a Pexels card
that produced no output, and closed mock-vision as real. Self-attested "done" is not trustworthy.

**The gate:** the agent moves finished work to **Internal QA** (never Closed). A deterministic checker
**`cc-verify <id>`** (`/usr/local/bin/cc-verify` → `/root/.openclaw/sp-provision/verify.py`) runs per-card
file checks (e.g. Pexels output has real pexels.com URLs; web build = real markup + no lorem; EDM = tables
+ inline CSS + 0 scripts; vision must not "analyze" fictional example.com images; deploy = a live 200 URL;
e2e = result PASS + real artifacts). The **supervisor** runs a `verify_sweep` each loop: QA + PASS → Closed;
FAIL → bounce to Build; **2nd consecutive FAIL → BLOCKED** (cap churn). The agent can NEVER set Closed.

**Calibration (how it was proven):** ran it against cards with known truth — it must FAIL 31 & 34 (known
fakes) and PASS 36 & 37 (known real). First run it false-PASSED 31 (matched the word "vision" in a comment);
fixed to key on the fictional-images tell; re-run passed 4/4. Lesson: **always calibrate a verifier against
known ground truth before trusting it.**

**Effect on the board:** on first gated restart it auto-reopened 31, 34, 39 (the 3 falsely-Closed fakes);
6 genuinely-real cards (29,30,32,33,36,37) stayed Closed. Honest Phase-1 status now:
- **Real & verified Closed:** 29, 30, 32, 33, 36, 37.
- **Reworking under the gate:** 34 (has valid Pexels key now → fixable), 39 (needs a real screenshot).
- **Will block (can't self-fix):** 31 vision (brief used fictional images — needs real sample images).
- **Blocked on Sukaimi / deferred:** 35 Higgsfield (DEFERRED future feature — server can't reach it),
  38 Vercel (needs project ID), 40 e2e gate (needs 38 + EDM wired to the real manifest).

**Files:** `verify.py` / `cc-verify`; gate logic in `cc-dispatch-loop.sh` (`verify_sweep`); fail-counters in
`/run/cc-verify/`. Pexels key stored at `/root/.openclaw/secrets/cc-secrets.env` (600, validated 200).

**Update 2026-06-05 (later) — FOUNDATIONAL FIX: the engine had no TS runtime.** Card 34 (Pexels) kept
producing no output even with a valid key. Root cause: **no `tsx`/`ts-node`/`package.json`/`node_modules`
existed** — the TypeScript builds could never actually run; the agent "closed" them without executing.
Installed `tsx` globally (`npm i -g tsx`, node v22.22). Ran `tsx run.ts --manifest samples/asset-manifest.json`
→ 3 real Pexels searches → 11 real photos → `output/pexels-assets.json`. `cc-verify 34` PASS → gate Closed it.
**Implication:** `tsx` is the missing runtime for the WHOLE engine — other cards' real code can now actually
execute (their earlier outputs were hand-authored or never run). Verified Closed now: 29,30,32,33,**34**,36,37.

**Update 2026-06-05 (later still):**
- **39 EDM preview fixed** the same way: no HTML→image renderer existed → installed `wkhtmltoimage` (+`xvfb`),
  rendered email.html → real 150KB screenshot → gate Closed it. **8/12 verified done** (29,30,32,33,34,36,37,39).
- **40 e2e wiring FIXED.** `tests/e2e/e2e-run.sh` had real defects: checked web build at `build/web-rails` (real
  path `build/static-web/output`), required manifest field `.scope`/`.deployTarget` (real manifest uses
  `.type`; `deployTarget` is null), and hard-FAILed Higgsfield (now `skip` = deferred). Also fixed a bug in
  **verify.py `c40`** (substring-searched "fail" but JSON always has `"failed": N` → could never pass; now reads
  `summary.result`). Re-run: **72 pass / 1 fail / 1 skip** — the ONE remaining failure is the Vercel deploy.
  40 auto-closes once 38 deploys.
- **Vercel:** checked for existing access on the server — NONE (no CLI, no token; mata/fara/sofie are
  self-hosted Docker+systemd, not Vercel). 38 genuinely needs Sukaimi's **token + team slug** after a Vercel
  **team outstanding-payment** clears.
- **31 vision & 35 Higgsfield = DEFERRED for soft launch** (Sukaimi's decision).
- Tools added to the box this session: `tsx` (global), `wkhtmltoimage`+`xvfb`, `jq`. These are now the engine's
  runtime/render/json deps.

---

## 14. PHASE 2 — Front door + money (core loop BUILT & TESTED, 2026-06-06)

**JOB0004 board** = the Phase-2 infra cards (intake bridge, CRO landing, Tally, Stripe, slot counter, operator
ping, client notifiers, token guard, legal, e2e). Most are built/in-QA.

**The live flow (all wired, happy-path tested):**
```
Tally form (tally.so/r/lbzRqX, web/EDM, no SP)
  -> submission emails to sukaimi@codeandcanvas.io  (Tally ACCOUNT email set to this; engine reads via Graph Mail.Read.
     NOTE: Tally free sends notifications to the ACCOUNT email only — gmail/hello@ custom-recipient did NOT work.)
  -> operator runs  cc-go [client-email]   = parse brief + cc-paylink (EXACT pages×SGD10, fixed qty, prefilled email)
     + email client the quote + record awaiting-payment
  -> client pays -> Stripe webhook (cc-stripe-webhook systemd svc, https://teams.codeandcraft.ai/cc/stripe-webhook)
     -> Popen cc-fulfil <email>
  -> cc-fulfil: match approved brief -> cc-intake (new client JOB#### + manifest) -> cc-build -> notify operator
  -> cc-build: run JOB0003 static-web builder on the client manifest -> vercel deploy -> email client the PUBLIC alias URL
```

**Commands on the box** (`/usr/local/bin/`, py in `/root/.openclaw/sp-provision/`): `cc-go`, `cc-paylink`,
`cc-fulfil`, `cc-build`, `cc-intake`, `cc-slots`, `cc-notify-operator` (Telegram 936727148 + Teams **user-id**
`29:1q4HXZ…` — NOT the conversation `a:` id; and a Teams bot can only DM after the user messages it once),
`cc-notify-client`, `cc-read-mail` (CC_MBX / CC_TALLY_MBX env to switch mailbox).

**Accounts/secrets** (`/root/.openclaw/secrets/cc-secrets.env`, 600): `PEXELS_API_KEY`, `VERCEL_TOKEN`
(scope `sukaimis-projects`), `STRIPE_TEST_KEY` (CODE&CANVAS PTE LTD, **test mode**), `STRIPE_WEBHOOK_SECRET`.
Email via Graph from **hello@codeandcraft.ai** (free shared mailbox; app has Mail.Send + Mail.Read; forwards to
sukaimi@codeandcanvas.io). Legal DRAFTs hosted at `https://teams.codeandcraft.ai/legal/{terms,privacy}.html`.

**Tested:** cc-go (real Tally brief parsed → exact SGD30 quote emailed), cc-fulfil → cc-intake → cc-build →
deploy → client emailed the live public URL (`output-cyan-kappa.vercel.app`, 200). Webhook sig-verify + ping
proven earlier.

**Remaining / known limits → see `docs/BACKLOG.md`** (single source of truth for all feature TODOs, priority-sorted). Don't duplicate the list here.

