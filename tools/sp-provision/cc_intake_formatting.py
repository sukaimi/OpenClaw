#!/usr/bin/env python3
"""Apply SharePoint column-formatting to the Intake Briefs list so the native
form/view gives the operator the verify-at-intake affordances:

  VerifyRequested -> a "Verify access" BUTTON (customRowAction setValue=true);
                     once requested it shows a "requested" pill instead.
  AccessVerified  -> a coloured STATUS PILL (Pending=amber, Verified=green,
                     Failed=red, blank="Not verified").

Set via SP REST CustomFormatter (Graph does not expose it). Reuses the app-cert
SP token + form digest from cc_provision_intake. Idempotent (MERGE overwrite)."""
import json
import sys

import requests

sys.path.insert(0, "/root/.openclaw/sp-provision")
from cc_provision_intake import _sp_rest_token, _form_digest, SITE_WEB  # noqa: E402

LIST = "Intake Briefs"

VERIFY_BUTTON = {
    "$schema": "https://developer.microsoft.com/json-schemas/sp/v2/column-formatting.schema.json",
    "elmType": "div",
    "children": [
        {
            "elmType": "button",
            "customRowAction": {"action": "setValue", "actionInput": {"VerifyRequested": "true"}},
            "txtContent": "Verify access",
            "style": {
                "display": "=if([$VerifyRequested] == true, 'none', 'inline-flex')",
                "border": "none", "background-color": "#0078d4", "color": "white",
                "padding": "4px 12px", "border-radius": "4px", "cursor": "pointer",
                "font-weight": "600",
            },
        },
        {
            "elmType": "span",
            "txtContent": "↻ verify requested",
            "style": {
                "display": "=if([$VerifyRequested] == true, 'inline', 'none')",
                "color": "#605e5c", "font-style": "italic",
            },
        },
    ],
}

STATUS_PILL = {
    "$schema": "https://developer.microsoft.com/json-schemas/sp/v2/column-formatting.schema.json",
    "elmType": "div",
    "txtContent": "=if(@currentField == '', 'Not verified', @currentField)",
    "style": {
        "padding": "2px 12px", "border-radius": "12px", "font-weight": "600",
        "text-align": "center", "display": "inline-block",
        "background-color": "=if(@currentField == 'Verified','#dff6dd', if(@currentField == 'Failed','#fde7e9', if(@currentField == 'Pending','#fff4ce','#f3f2f1')))",
        "color": "=if(@currentField == 'Verified','#107c10', if(@currentField == 'Failed','#a4262c', if(@currentField == 'Pending','#8a6d0b','#605e5c')))",
    },
}


def set_formatter(tok, digest, field, formatter):
    url = "%s/_api/web/lists/getbytitle('%s')/fields/getbytitle('%s')" % (
        SITE_WEB, LIST.replace(" ", "%20"), field)
    h = {
        "Authorization": "Bearer " + tok,
        "X-RequestDigest": digest,
        "X-HTTP-Method": "MERGE",
        "IF-MATCH": "*",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose",
    }
    body = {"__metadata": {"type": "SP.Field"},
            "CustomFormatter": json.dumps(formatter, separators=(",", ":"))}
    r = requests.post(url, headers=h, data=json.dumps(body))
    print("  %-16s -> %d %s" % (field, r.status_code,
          "ok" if r.status_code < 300 else r.text[:200]))
    return r.status_code < 300


def main():
    tok = _sp_rest_token()
    digest = _form_digest(tok)
    ok = True
    ok &= set_formatter(tok, digest, "VerifyRequested", VERIFY_BUTTON)
    ok &= set_formatter(tok, digest, "AccessVerified", STATUS_PILL)
    print("formatting:", "OK" if ok else "PARTIAL/FAILED")


if __name__ == "__main__":
    main()
