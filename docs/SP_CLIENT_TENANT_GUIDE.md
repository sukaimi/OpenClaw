# SP Client-Tenant Deployment Guide

## Overview

After Code&Craft completes a SharePoint classic-to-modern migration in the C&C build tenant (e.g. CCBuild-JOB0023), the finished site is exported and imported into the client's own Microsoft 365 tenant. This guide covers the two parties' actions: a one-time access grant by the client admin, followed by the import run by the C&C operator.

---

## Prerequisites

- A modern SharePoint site already provisioned in the client's tenant (the target site)
- Client's Microsoft 365 global admin or SharePoint admin credentials
- Job number (e.g. JOB0023) and confirmation from C&C that the export package is ready

---

## Step 1: Grant app access — client admin action (~5 min)

The C&C app registration ("OpenClaw SP Provision") needs **Sites.Selected Write** permission scoped to the client's target site. No tenant-wide admin consent is required — Sites.Selected is per-site only.

The client admin runs the following PowerShell once:

```powershell
# Install PnP.PowerShell if not already present
Install-Module PnP.PowerShell -Scope CurrentUser

# Connect interactively to the target site
Connect-PnPOnline -Url "https://<client>.sharepoint.com/sites/<their-site>" -Interactive

# Grant the C&C app registration write access to this site only
Grant-PnPAzureADAppSitePermission `
    -AppId "<C&C clientId>" `
    -DisplayName "Code&Craft SP Provision" `
    -Site "https://<client>.sharepoint.com/sites/<their-site>" `
    -Permissions Write
```

**Replacements:**
- `<client>` — the client's SharePoint domain prefix (e.g. `contoso`)
- `<their-site>` — the target site name (e.g. `intranet`)
- `<C&C clientId>` — provided by C&C (the `sharepoint.clientId` from the OpenClaw config)

---

## Step 2: Provide C&C with tenant details

Once access is granted, the client provides C&C with:

- **Tenant ID** — found in Azure Active Directory → Overview → Tenant ID
- **Target site URL** — the full URL of the site access was granted on

---

## Step 3: C&C runs the import — operator action

With the export package ready and client tenant details in hand, the C&C operator runs:

```bash
# Export from the C&C build site
python3 cc_sp_export.py --job JOB####

# Import into the client's tenant
python3 cc_sp_import.py \
    --package /srv/projects/JOB####/sp-export-package/ \
    --target-site https://<client>.sharepoint.com/sites/<their-site> \
    --tenant <client-tenant-id>
```

Both scripts are idempotent — safe to re-run if interrupted.

---

## Step 4: Verify

- Visit the target site and confirm all pages appear and render correctly
- Check that images load (Site Assets upload succeeded)
- If a delegated SharePoint session is available for the client tenant, run the C&C verify gate for a structured diff check

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `403` on page POST | Sites.Selected grant not applied, or wrong site URL | Re-run PowerShell grant with the exact target site URL |
| Images returning `404` | Site Assets upload failed mid-run | Re-run `cc_sp_import.py` (idempotent) |
| Page already exists warning | Script found an existing page | Expected — script PATCHes in place, no action needed |
| `401 Unauthorized` | Certificate mismatch or wrong tenant ID | Verify `--tenant` value matches the tenant where the grant was made |
