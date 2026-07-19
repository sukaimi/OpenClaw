# SPARK demo fixtures — Crestfield Foods

Canned, static data that drives the SPARK v1 sandbox replay. **Nothing here is fetched at runtime** — the UI imports these JSON files directly.

## Provenance

These fixtures are derived from a **real** OpenClaw SharePoint delivery run (JOB0022: classic → modern SharePoint migration). Every real-client identifier has been **rebranded** to a fictional FMCG company, **Crestfield Foods International** ("Good Food, Every Day"), with invented sub-brands (Veldt Chocolate, Solara Snacks). Source/target site URLs use `contoso.sharepoint.com` placeholders. All data is fictional and safe to publish.

## Files

| File | What it is |
|------|------------|
| `content-tracker.json` | The 3-sheet content audit workbook as arrays (Content Tracker · Image Index · Migration Summary), plus a status → colour map for the in-browser viewer. |
| `pipeline-stages.json` | The 13 real SPARK pipeline stages, each with an agent/tool, a duration, and realistic log lines. The **Verify Gate** stage is the fail-closed climax — the agent cannot self-close. |
| `scored-pages.json` | 16 Crestfield pages scored and bucketed into 3 tiers, with the priority signals behind each score. |
| `job-summary.json` | Run metadata: job id `DEMO-0022`, client, source/target sites, page + asset counts, and the `copy fidelity 1.00` verdict. |
| `source/Crestfield_Content_Tracker_v1.0.xlsx` | The original 3-sheet workbook the tracker JSON was parsed from (safe, rebranded). |

## Status colour map (`content-tracker.json → statusColors`)

- **Migrate** → green `#16a34a`
- **Review** → blue `#2563eb`
- **Rewrite** → amber `#d97706`
- **Archive** → red `#dc2626`

## Related asset

`../public/crestfield/after-home.png` — the rebuilt modern SharePoint homepage screenshot ("after" state) for the before/after view.
