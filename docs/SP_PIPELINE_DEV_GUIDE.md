# SharePoint Classic → Modern Pipeline — Developer Guide

**Audience:** human developers maintaining, deploying, or extending the Code&Craft SharePoint conversion pipeline. (The OpenClaw *agents* are driven by the runbooks in `workspace-full-stack-engineer/` — see References. This guide is the human-facing companion: how to deploy it, how it works, and where every piece lives.)

Last updated 2026-06-14.

---

## 1. What it does

Converts an existing **classic** SharePoint site into an equivalent **modern** SharePoint site, page by page, with a deterministic completeness gate so nothing is silently dropped.

- **Level 1 (built + proven):** source classic site **and** the modern build site both live in **our** `codeandcanvas` tenant. The operator supplies the source URL; the pipeline audits it and rebuilds an equivalent modern site in an isolated `CCBuild-<JOB>` site via Microsoft Graph.
- **Level 2 (access model):** the source lives in a **client** tenant. It is read over an **interactive delegated browser session** (a human logs in once via a popup) — nothing is provisioned in the client tenant. Redeploying the finished build *into* the client tenant (PnP) is **not yet built** (see Backlog).
- **There is no build host, no CI, no Vercel** on this rail. The deploy target is always the isolated build site.

---

## 2. Source-code & web-part location index

> The **repo is the source of truth**; the VPS holds the *live runtime* copy. After editing in the repo you must **deploy** Python changes to the VPS (§4). The `.mjs` tools run from the **repo on the operator's Mac**.

### Repo — `github.com/sukaimi/OpenClaw`
| Path | What |
|---|---|
| `tools/sp-provision/*.py` | The build engine (runs on the VPS). Key files below. |
| `tools/cc-visual-qa/*.mjs` | Capture + gate + rollup (run on the operator's **Mac**, Playwright + Graph). |
| `tools/sp-content-tracker/` | 3-sheet xlsx content tracker (Node). |
| `docs/handoffs/HANDOFF_*` | Project handoffs (the comprehensive SP record + the guardrails build log). |

**Engine (`tools/sp-provision/`):**
- `spclient.py` — app-cert Graph/SP client (`from spclient import SP`). Reads auth from `config.json` (§4).
- `cc_sp_config.py` (`cc-sp-config`) — derives `job.config.json` from brief + site + sp-expect.
- `cc-sp-mirror.py` (`cc-sp-mirror`) — **Mac-side** operator orchestrator (all stages, `--from`/`--only`/`--dry-run`).
- `cc_sp_build.py` (`cc-sp-build`) — **server-side** build runner (image-migrate → compose → style). Has the large-site guardrails wired in.
- `sp-audit.py` — source → `sp-expect.json` (markers/content/images; reads WikiField/CanvasContent1 **and** publishing `PublishingPageContent`).
- `image_migrate.py` — builds `image-map.json`, migrates source images.
- `canvas_compose.py` — the modern-page composer (`apply_page`, web-part builders, marker/content/image safety nets, **backup-before-overwrite**).
- `cc_sp_triage.py` — large-site **triage** → `scope-sheet`, `--approve`, `--worklist` (§6).
- `cc_sp_restore.py` — restore a page from a pre-overwrite backup (§6).
- `cc_sp_subsites.py` — subsite enumeration → per-subsite child jobs (109; dry-run).
- `cc-sp-tracker.py` (`cc-sp-tracker`), `cc-sp-styler-attach.py` — xlsx tracker; SPFx styler attach.

**Capture/QA (`tools/cc-visual-qa/`, run on the Mac):**
- `cc-sp-capture.mjs` — interactive/delegated source capture (Playwright) → `capture/` bundle + `site-inventory.json` (enriched with complexity signals).
- `cc-completeness-gate.mjs` — deterministic per-page completeness gate (canvasContent diff; the agent can never self-close).
- `cc-sp-rollup.mjs` — aggregate gate verdicts → `exceptions.md`.
- `sp-complexity.mjs` (+ `.test.mjs`) — shared triage flag-detection heuristics.

### VPS — Hostinger `srv1330842` (`76.13.179.220`)
| Path | What |
|---|---|
| `/root/.openclaw/sp-provision/` | **Live runtime** copy of the engine `.py` (deploy target). |
| `/root/.openclaw/venv/bin/python` | The Python the engine runs under. |
| `/root/.openclaw/config.json` | Auth config (`sharepoint`: `certPath`, `certThumbprint`, `clientId`, `tenantId`, `certExpiry`). The cert **`.pfx` itself** is at `certPath` — **never commit it**. |
| `/srv/projects/<JOB>/` | Per-job runtime: `capture/`, `sp-expect.json`, `site-inventory.json`, `scope-sheet.*`, `worklist.json`, `image-map.json`, `job.config.json`, `backups/`, `exceptions.md`, `.sp-verified`. |
| `/root/.openclaw/workspace-full-stack-engineer/runbook-sp-convert.md`, `runbook-sp-build.md` | Agent-facing runbooks (the per-job instructions). |

### SPFx web part (site styler / carousel)
- **Deployed** solution component id `a1b2c3d4-e5f6-7890-abcd-ef1234567890`, lives in the **SharePoint App Catalog** (attached per-site by `cc-sp-styler-attach.py`).
- ⚠️ **The SPFx _source_ is NOT on the VPS** (`/root/spfx/cc-site-styler` is empty; no `.sppkg` on the box) and the server SPFx (yo/gulp) toolchain is **broken**. **Action item:** locate/recover the SPFx project source (likely a separate machine/repo) before any SPFx rebuild. Until then, the carousel/styler are reuse-only (no rebuild).

---

## 3. Architecture (how a conversion flows)

```
SOURCE (classic)                         BUILD SITE (modern, CCBuild-<JOB>)
   │
   ▼  cc-sp-capture.mjs (Mac, delegated/app session)
capture/ bundle + site-inventory.json
   │
   ▼  sp-audit.py --from-capture
sp-expect.json  (pages: markers[] + content[] + images[])
   │
   ▼  cc_sp_triage.py        ── large-site guardrail (§6): scope-sheet → operator approves → worklist
   │
   ▼  image_migrate.py → image-map.json
   │
   ▼  canvas_compose.py (apply_page)   ── 3 safety nets + source-of-truth merges + backup-before-overwrite
modern pages published to the build site
   │
   ▼  cc-verify-sp  (Graph read-back; the authoritative close-gate — agent can NEVER self-close)
   │
   ▼  cc-sp-rollup.mjs → exceptions.md   (operator reviews only failures + flagged-skipped)
```

**Auth:** app-cert (`Sites.Selected`) for reads/writes in **our** tenant (build site + own-tenant source). Cross-tenant client sources use a **delegated browser session** (`~/.codecraft/verify-<host>.json`), captured at intake — never app-consent into a client tenant.

**Two driver paths:** `cc-sp-mirror` is the **Mac operator** full-run orchestrator (it also drives capture + the per-page gate). `cc-sp-build` is the **autonomous server** build runner the O/C harness calls. Both compose via `canvas_compose.py`.

**Guarantees built into compose:** (a) source-of-truth reconciliation (images + text merged from the live-capture manifest), (b) three safety nets (marker / content / image — nothing silently dropped), (c) the per-page completeness gate is deterministic and fail-closed.

---

## 4. Deployment

### Engine (Python) — repo → VPS
The VPS runs `/root/.openclaw/sp-provision/*.py`. After editing in the repo:
```bash
# from the repo root, deploy a changed engine file (uses sshpass; creds in ~/.codecraft/verify-watch.json)
scp tools/sp-provision/<file>.py root@76.13.179.220:/root/.openclaw/sp-provision/
# verify it compiles on the box
ssh root@76.13.179.220 '/root/.openclaw/venv/bin/python -c "import py_compile; py_compile.compile(\"/root/.openclaw/sp-provision/<file>.py\", doraise=True)"'
```
> **Always confirm the VPS file matches the repo baseline apart from your change before overwriting** (diff first) so you don't regress an out-of-band server edit.

### Capture/QA (`.mjs`) — run on the Mac
`cc-sp-capture.mjs` / `cc-completeness-gate.mjs` / `cc-sp-rollup.mjs` run from the **repo checkout on the operator's Mac** (Playwright). No deploy step — the repo *is* the runtime. `npm install` once in `tools/cc-visual-qa/`.

### Credentials (never commit)
- **App-cert:** `config.json.sharepoint.certPath` → the `.pfx` on the VPS. Rotate via the cert + `certThumbprint`/`certExpiry`.
- **Source sessions:** `~/.codecraft/verify-<host>.json` (delegated, mode 600).
- **SSH/op creds:** `~/.codecraft/verify-watch.json` (host/user/pass, mode 600). **Rotate the `root` SSH password** — it has appeared in plaintext (see backlog).
- **SPFx:** deployed solution in the App Catalog; source must be located before rebuild.

### SPFx web part
The styler/carousel is **already deployed** to the App Catalog. To attach to a build site: `cc-sp-styler-attach.py --config /srv/projects/<JOB>/job.config.json` (only when `styler.wallpaperUrl` is set). Rebuilding the `.sppkg` is **blocked** until the source is recovered + the toolchain fixed.

---

## 5. Running a conversion

**Server (autonomous harness path):**
```bash
cc-sp-config <JOB>     # writes /srv/projects/<JOB>/job.config.json from brief+site+sp-expect
cc-sp-build  <JOB>     # image-migrate → compose → style (LOCAL on the VPS)
cc-verify-sp <JOB>     # the deterministic close-gate (writes .sp-verified on PASS)
node tools/cc-visual-qa/cc-sp-rollup.mjs /srv/projects/<JOB>   # exceptions.md
```

**Operator full-run (Mac):**
```bash
cc-sp-mirror --config /srv/projects/<JOB>/job.config.json [--dry-run] [--from <stage>] [--only <stage>]
```
Stages: `preflight → capture → audit → tracker → image-migrate → compose → style → gate → closeout`.

---

## 6. Large-site guardrails (JOB0024-108)

For sites with hundreds of pages — never convert blind. **Backward-compatible:** with no `worklist.json`/`scope-approved.json`, the build runs the legacy capped path unchanged.

```bash
# 1. triage the captured inventory -> a scope sheet the operator reviews
cc_sp_triage.py /srv/projects/<JOB>            # -> scope-sheet.json + scope-sheet.csv
# 2. operator approves (or edits the csv); 3. generate the wave worklist
cc_sp_triage.py /srv/projects/<JOB> --approve --all-buildable   # -> scope-approved.json
cc_sp_triage.py /srv/projects/<JOB> --worklist --wave-size 10   # -> worklist.json
# 4. cc-sp-build then builds in WAVES (next waveSize pending), backing up each page
#    before overwrite (CC_SP_BACKUP_DIR is set automatically); resumable.
# restore a page from its pre-overwrite snapshot:
cc_sp_restore.py <JOB> <page.aspx> [--at <ts>] [--site-path /sites/CCBuild-<JOB>]
```
- **Triage** classifies keep/archive (by `triageKeepMonths`, default 18) and buildable/flagged (by complexity). Flagged page types are surfaced, **never faked**.
- **Scope gate:** the build refuses pages not in `scope-approved.json`.
- **Backup/restore:** SharePoint here has no version history → pages are snapshotted (canvasLayout) before overwrite, restorable via `cc_sp_restore` (strips `@odata` annotations on re-POST).
- **Exceptions rollup:** the operator reviews only failures + flagged-skipped pages, not every page.

---

## 7. Content-type coverage (JOB0024-109)

Extends what's **buildable** beyond text/image article pages — **opt-in** per job via `buildableTypes` (default `[]`, so existing runs are unchanged):

| Type | `buildableTypes` value | Rebuilt as |
|---|---|---|
| Publishing-layout pages | `publishing` | `PublishingPageContent` → `content[]` (`pub-field`) → same composer + gate |
| List-view web parts | `list` | static snapshot → Quick Links / text |
| HomeTiles | `tiles` | native Quick Links |
| Banner | `banner` | native Hero |
| Subsites | — | enumerate → per-subsite child jobs (`cc_sp_subsites.py`) |
| **Carousel** | — | **stays FLAGGED** (`carousel-spfx`) — needs the SPFx solution; not faked |

⚠️ These converters are **unit-tested (synthetic fixtures) but NOT yet live-calibrated** — they need an own-tenant publishing **reference site** (which can't be created in modern SPO) to validate layout-zone mapping, gate thresholds, live list reads, and nested-web auth. `TODO(JOB0024-109)` markers flag every deferred live dependency. **Not deployed to the VPS yet** for that reason.

---

## 8. Gotchas / known issues

- **`@odata` strip:** a `$expand`'d `canvasLayout` carries `*@odata.context` keys Graph rejects on re-POST — strip recursively before re-applying (done in `cc_sp_restore`).
- **Recycle-not-delete:** no SP version history; deletes go to the recycle bin (~93d). Back up before overwrite; never hard-delete source.
- **Home page:** `Home.aspx` (welcome page) is 423-locked → PATCHed in place, not deleted+recreated. Triage excludes it as a system page.
- **Web-part cap:** Graph rejects >~6 heavy media web parts/page (400) → `heavyWebpartCap` + incremental PATCH batches.
- **Phantom/soft-lock:** a failed POST soft-locks a page name → `apply_page` retries with a fresh name.
- **Client tenants are READ-ONLY** (e.g. MDLZ/RDQ) — never auto-target; calibrate own-tenant only.
- **SPFx toolchain broken** on the VPS; SPFx source missing — reuse-only until recovered.

---

## 9. References
- Agent runbooks: `/root/.openclaw/workspace-full-stack-engineer/runbook-sp-convert.md`, `runbook-sp-build.md`.
- Handoffs: `docs/handoffs/HANDOFF_HOMEPAGE_MIRROR.md` (comprehensive SP record), `docs/handoffs/HANDOFF_JOB0024_GUARDRAILS.md` (guardrails build log).
- Command Center: **SP Conversion Runbook** + **Learnings** pages (left-nav).
- Backlog: client-tenant redeploy (PnP), SPFx source recovery, content-type live calibration, SSH/secret rotation.
