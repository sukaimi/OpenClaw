# Handoff → Claude Chat: author a Claude Cowork prompt to set up M365 / SharePoint access

**For:** Claude Chat (planning). **You produce:** one self-contained, copy-pasteable prompt for **Claude Cowork**, whose job is to help Sukaimi stand up Microsoft 365 / SharePoint access for the live OpenClaw "Code & Canvas SharePoint" dev team.

**Your only job here:** turn the context + requirements below into that Cowork prompt. Do not perform the setup yourself; write the prompt that drives it. **Phase 0 is already fully resolved** — so the Cowork prompt must NOT re-ask those questions. Instead, write it so Cowork's first move is to **play back the confirmed prerequisites and the full plan, then wait for Sukaimi's "go" before touching anything.** That preserves "pause before acting" without re-asking answered questions.

---

## System context (accurate as of deployment — use, don't re-derive)

- A 10-seat OpenClaw multi-agent team is **already live** on a Hostinger VPS (`srv1330842`, 76.13.179.220), fronted by a Telegram bot. Hub = `main` (displayed "Delivery Lead 🧭"); 9 specialists. Models: Profile A DeepSeek V4 (hub/engineer/qa/devops/writer → `deepseek-v4-flash`; PM/architect/ux/reviewer/security → `deepseek-v4-pro`).
- Reference design: `SharePoint_Team_Design_Pack_v5_DEPLOYED.md` (and the v5.1 update in progress).
- The team is **built to deliver SharePoint sites but has ZERO M365 access provisioned.** This workstream fixes that.
- **Already decided (do not reopen):**
  - SPFx **toolchain = GitHub Actions (CI)** — compiles off-tenant to `.sppkg` in CI, *not* on the VPS; engineer hands `.sppkg` to devops-deploy.
  - **Kanban = a SharePoint list rendered as a board view** (NOT Planner), sharing the Project Log's data model + Graph write path.
- **Two distinct access scopes** (the prompt must keep these separate):
  - **Command center = the Code & Canvas (C&C) tenant** — internal cross-project records: Project Log (list), Kanban (list/board), Learnings Wiki (site pages).
  - **Client site = the client's own tenant** — builds happen here, via a scoped, per-site app-registration grant.

## Goal of the Cowork prompt
Drive M365 access setup end-to-end, **in order, pausing at every human-only gate**, ending with a working command center on the C&C tenant and a repeatable per-client access pattern.

## Phases the Cowork prompt must lay out

**Resolved prerequisites (confirmed 2026-06-01 — Cowork can take these as given):**
- **Tenant exists:** `codeandcanvas.sharepoint.com` (domain `codeandcanvas.io`).
- **Scope for now:** stand up the **C&C command center only**. Client-site targets are deferred — do NOT pick one yet.
- **Existing tenant facts (from a Claude.ai M365 discovery pass):**
  - Sites already present: the **C&C Intranet** root site; an **`InternalDevelopmentSite`** (already holds "SharePoint Project Setup" guidance, an *Automated SPFx Setup with PowerShell* doc, a Copilot chatbot, timesheet); per-project sites like `FC-951-InnovationInternalDev`.
  - The existing "Automated SharePoint Project Setup with PowerShell" doc was read: it's a **local dev-machine SPFx scaffolder** (yo/gulp/Tailwind/PnPjs/React, trusts the local dev cert) — **NOT** an auth/app-registration recipe. Confirms there is **no existing app registration** for headless access; the foundation is net-new.

**Decisions locked (2026-06-01 — bake these into the Cowork prompt, do not re-ask):**
- **Command center = a NEW dedicated site, "Code&Craft AI Command Center"** on the C&C tenant (clean single-site `Sites.Selected` grant; do not reuse InternalDevelopmentSite or the Intranet root).
- **Project numbering = the org's existing conventions: `FC####` for Fresh Communication projects, `JOB####` for all others.** Drop the pack's `AI-2026-####`. The Project Log's project-number column uses these.
- **Credential = certificate** (not a client secret).
- **App registration:** `OpenClaw-SharePoint-Agent`, Graph application permission **`Sites.Selected`**, granted per-site (command center first).
- **Critical access distinction:** Claude.ai's own M365 connection (delegated) ≠ the VPS agents' access. The agents need their **own** Entra app registration + certificate in their secret store. Provisioning the agents is the whole point; an existing human/delegated login does NOT cover them.

**Phase 0 — RESOLVED (all prerequisites confirmed 2026-06-01):**
- **Tenant admin = Sukaimi** (`sukaimi@codeandcanvas.io`, Global Admin). He performs the admin-consent click and the per-site grant.
- **Secret store = root-only file** on the VPS: certificate private key at `/root/.openclaw/secrets/oc-sharepoint.pfx` (create `secrets/` dir), owned by root, `chmod 600`, referenced by path. NOT `/etc/environment`. Sukaimi places the key file himself; never committed to the repo (already gitignored).
- No prerequisites remain — Cowork can proceed from Phase 1, pausing only at the human-gated consent/grant/key-placement steps.

**Phase 1 — Entra ID app registration (C&C tenant):**
- Create an app registration (suggested name `OpenClaw-SharePoint-Agent`).
- **Least-privilege Graph application permissions: `Sites.Selected`** — NOT `Sites.FullControl.All` / not tenant-wide. Add only what's genuinely needed for provisioning + app-catalog deploy.
- **Admin consent** = a human admin action; Cowork guides, never impersonates.
- Credential: **certificate** (decided). Generate the cert, upload the public key to the app registration, keep the private key in the secret store (Phase 3). No client secret.

**Phase 2 — Per-site grant (`Sites.Selected`):**
- Grant the app write access to the **exact** C&C command-center site via Graph; later, repeat per client site. One site per grant. This is the whole point of `Sites.Selected`.

**Phase 3 — Secret store (decided: root-only file):**
- Cert private key at `/root/.openclaw/secrets/oc-sharepoint.pfx`, owned by root, `chmod 600`, referenced **by path** in config — never inlined, never in `/etc/environment`, never committed. **Sukaimi places the key file himself.** Note the cert expiry and set a rotation reminder.

**Phase 4 — Connectivity test (before building anything real):**
- A minimal PnP/Graph script that authenticates **as the app** and reads + writes the command-center site. Must pass before Phase 5.

**Phase 5 — Stand up the command center (C&C tenant):**
- **Project Log** — SharePoint list, schema per pack §12 but with project-number using the org conventions: **`FC####`** (Fresh Communication) / **`JOB####`** (others) — not `AI-2026-####`. Columns: project number, client brand, description, start date, status (phase-level), end date.
- **Kanban** — a SharePoint list rendered as a **board view**, same data model + Graph write path as Project Log; one cross-project board; project number on every card; hub is the only writer.
- **Learnings Wiki** — SharePoint site pages; one entry per closed project.

**Phase 6 — GitHub Actions CI for SPFx:**
- Repo + workflow compiling SPFx → `.sppkg`; deploy creds as **GitHub Actions secrets**; output handed to devops-deploy for app-catalog upload.

## Hard constraints the Cowork prompt MUST embed
- **Least privilege always:** `Sites.Selected`, single-site grants. Never tenant-wide write.
- **Humans own the dangerous steps:** admin consent and credential creation are human actions. Cowork **never asks for, types, or handles a password**, and **never inlines a secret** into code/config/chat — secrets by reference/location only.
- **Stay in scope:** act on the assigned site only; never touch another tenant or site.
- **Plan before doing; pause at each human gate**; one phase at a time.

## What you (Claude Chat) output
A **single, copy-pasteable prompt for Claude Cowork** containing the phases and constraints above, written so Cowork's first move is to **play back the confirmed Phase-0 prerequisites and the full plan, then wait for Sukaimi's "go"** before touching anything — it must NOT re-ask the already-answered Phase-0 questions. Keep it self-contained (Cowork won't have this handoff or the design pack).
