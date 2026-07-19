# sp-content-tracker — Content Tracker generator (FARA absorbed)

Produces FARA's 3-sheet `.xlsx` **Content Tracker** as a deliverable of the OpenClaw
SharePoint classic→modern conversion pipeline — fed by `sp-audit.py`'s `sp-expect.json`
(Graph + app-cert, unattended), NOT FARA's Playwright scanner.

## Files
| File | What it is | Verified |
|---|---|---|
| `sp-tracker.js` | Node/exceljs CLI + library: normalize `sp-expect.json` → assets, apply the migration-status ruleset, emit the 3-sheet workbook (Content Tracker / Image Index / Migration Summary, **derived** pain-points). | ✅ self-test + real JOB0022 data |
| `sp_audit_http.py` | stdlib-only helper for `sp-audit.py`: broken-link HEAD checks + image natural-dimension parsing (PNG/JPEG/GIF via `struct`, no Pillow). In a file because the context-mode hook blocks inline `requests.get(`/`curl`/`wget`. | ✅ image-dim parser; ⚠️ HEAD logic sound but untested here (no sandbox egress) — validate on server |
| `selftest.js` | Synthetic `sp-expect.json` + enrichment → asserts every ruleset branch and that exactly the 3 sheets generate. | ✅ ALL PASS |
| `package.json` / lock | `exceljs@^4.4.0`. | — |

## Migration-status ruleset (ADVISORY ONLY — build always migrates verbatim)
- **Migrate** *(default)* — intact content, links 200, images adequate-res.
- **Review** — broken link (HEAD ≠ 200), low-res image (natural width < 400px), or empty/garbled block.
- **Archive** — stale: newest in-content date older than the freshness cutoff (default 12 months, `--stale-months`).
- **Rewrite** — undated time-sensitive content (news/events/announcement with no parseable date), or a past-dated event.

Statuses never gate the build and never drop content — they are reviewer flags only.

## Usage
```
node sp-tracker.js <sp-expect.json> <out.xlsx> \
  --site "Crestfield Foods International" \
  --url  "https://contoso.sharepoint.com/sites/CrestfieldClassic" \
  --today 2026-06-12 [--stale-months 12] [--enrich enrich.json]
```
`--enrich enrich.json` = `{ brokenLinks:[{url,status}], imageDims:{"<src>":{w,h}} }`, produced by
`sp_audit_http.py`. Without it, links/images default to Migrate (no false flags).

## Validated result on real JOB0022 (Crestfield)
31 assets → **26 Migrate / 5 Rewrite / 0 Review / 0 Archive**. News items Migrate (dates in html
parsed); the "Upcoming Events" block flags Rewrite because the events carry no year ("APR 3") and are
past-dated — a correct, useful reviewer flag, not noise. 3 sheets generate; derived pain-point: PP Comms.

## Known deviation from FARA (intentional)
FARA computed image DPI from **rendered** display size (Playwright DOM). The pipeline is REST-based, so
there is no rendered size — `sp_audit_http.py` measures **natural pixel width from the image bytes** and
flags low-res by an absolute threshold (`LOWRES_MIN_PX = 400`) instead of a DPI ratio. Same intent
(flag images too small to reuse), different signal.

## To finish on the server (`/root/.openclaw/`)
1. **Enrichers into `sp-audit.py`** — when it already downloads source images with the app token, feed
   the bytes to `sp_audit_http.image_dims_from_bytes()`; collect real hrefs (skip `#`/mailto/tel) and run
   `sp_audit_http.head_check()`. Emit `enrich.json` next to `sp-expect.json`. (Crestfield's links are all
   `#` placeholders, so broken-link/Review needs a real site to exercise.)
2. **Field-mapping check** — `normalizeAssets()` matches the current schema (`kind/heading/text/html/
   items[]/images[]`). Re-confirm if `sp-audit.py` changes its output shape.
3. **Splice** — at delivery-lead `AGENTS.md:~269`, after `sp-expect.json` is written and the
   technical-writer makes `content-audit.md`, run `node sp-tracker.js … --enrich enrich.json` to emit
   `docs/content-tracker.xlsx`. Update `runbook-sp-convert.md` + the `## DISPATCH-SP` block. Back up edited
   prompts (`.bak-*`). The deterministic gate stays on `sp-expect.json` (tracker is non-gating in phase 1).
4. **Surface** — upload `content-tracker.xlsx` to the build-site Documents library (via the existing
   app-cert Graph/SP-REST tooling) + link from the board card; copy to the Command Center Project Archive
   at closeout. Not client-facing by default.
5. **Validate on JOB0022** end-to-end and eyeball the workbook.

## Then: decommission standalone FARA (Track 2, only after the above is proven)
`docker compose -f /opt/fara/docker-compose.yml down`; remove the `*/5` git-poll redeploy cron; remove the
nginx `fara.codeandcraft.ai` vhost (release cert/DNS); archive the repo. 🔴 Rotate/scrub the live GitHub
PAT embedded in the `/opt/fara` git remote.
