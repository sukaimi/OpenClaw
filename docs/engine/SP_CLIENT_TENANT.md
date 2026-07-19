# SP Client-Tenant Deployment — Dev Handover Guide

## Delivery model

Completed SharePoint migrations live in the **C&C build tenant** (`CCBuild-JOB####.sharepoint.com`). The client reviews pages via **screenshare during cadence calls**. Once approved, a C&C developer manually deploys the site into the client's own Microsoft 365 tenant.

This guide is for the **developer doing that manual deployment**. It is not an automated pipeline step.

---

## What gets deployed

- All modern pages built and gate-verified in `CCBuild-JOB####`
- Page canvas layout + web parts (Hero, Text, Image, Quick Links)
- Branding: site theme + wallpaper (applied via `cc-sp-styler-attach.py` on the target)
- Images: uploaded from the C&C build site's Site Assets into the client's Site Assets

---

## Step 1: Understand what was built

Before starting, review the job deliverables in the build tenant:

- `/srv/projects/JOB####/sp-handover-summary.json` — migrated pages, exceptions, tier breakdown
- `/srv/projects/JOB####/sp-expect.json` — source content per page
- `/srv/projects/JOB####/image-map.json` — image src → built URL mapping
- `/srv/projects/JOB####/sp-scored.json` — tier + priority per page

The xlsx tracker (`cc-sp-tracker.py`) output is the client-facing deliverable checklist.

---

## Step 2: Get access to the client tenant

The client's SharePoint or Global admin must grant the deploying developer (or a service principal) appropriate access to the target site. Options:

- **Developer personal account** — admin adds developer as Site Collection Admin on the target site (quickest for a one-off)
- **Service principal** — register an app in the client's Azure AD, grant Sites.Selected Write to the target site via PnP PowerShell:

```powershell
Connect-PnPOnline -Url "https://<client>.sharepoint.com/sites/<site>" -Interactive
Grant-PnPAzureADAppSitePermission `
    -AppId "<service-principal-clientId>" `
    -DisplayName "C&C Deploy" `
    -Site "https://<client>.sharepoint.com/sites/<site>" `
    -Permissions Write
```

---

## Step 3: Recreate pages in the client tenant

For each page in `sp-handover-summary.json → migrated`:

1. Read `sp-export-package/pages/<name>.json` (canvasLayout exported from the build site via Graph beta)
2. Strip any `@odata.*` keys recursively before POSTing (Graph rejects them with 400)
3. POST to `/_api/v2.0/sites/<clientSiteId>/pages` with the canvas JSON
4. Publish: `POST /_api/v2.0/sites/<clientSiteId>/pages/<pageId>/publish`

**Key gotcha:** `@odata.context` and similar metadata keys embedded in `canvasLayout` must be stripped before re-POST — use a recursive strip before any Graph write.

---

## Step 4: Migrate images

1. Download images from the C&C build site's Site Assets (`/sites/CCBuild-JOB####/SiteAssets/...`)
2. Upload to the client's Site Assets under `/Migrated/JOB####/`
3. Rewrite image URLs in the canvas JSON (use `image-map.json` for targeted swaps, then bulk prefix replace for any remaining build-site URLs)

---

## Step 5: Apply branding

Run `cc-sp-styler-attach.py --config <clientConfig>` against the client target site, with a config pointing at the client tenant. Requires an authenticated Graph token for the client tenant.

---

## Step 6: Verify

Walk each delivered page in the client site and confirm:
- Content renders correctly
- Images load
- Navigation links resolve

Cross-reference against `qa-verdict-*.json` files from the build run to know exactly what was gate-verified.

---

## Reference: canvasLayout export (manual)

To manually export a built page's canvasLayout from the C&C build tenant for reference:

```python
# Requires spclient with build-tenant credentials
import json
from spclient import SPClient

client = SPClient()
token = client.graph_token()
site_id = client.site_id()

page_name = "Innovation is the Key to Success.aspx"
resp = requests.get(
    f"https://graph.microsoft.com/beta/sites/{site_id}/pages?$filter=name eq '{page_name}'&$expand=canvasLayout",
    headers={"Authorization": f"Bearer {token}"}
)
page = resp.json()["value"][0]
# Strip @odata.* before saving
print(json.dumps(page["canvasLayout"], indent=2))
```
