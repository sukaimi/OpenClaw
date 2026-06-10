#!/usr/bin/env python3
"""Read (and optionally patch) the Kanban list's views via SharePoint REST.
Usage: sp_view_sort.py            # read views
       sp_view_sort.py --apply    # set every Board view's sort to Modified DESC
"""
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from pathlib import Path
import msal, requests
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from spclient import _load_sp_config, CONFIG_PATH

SP_HOST = "codeandcanvas.sharepoint.com"
SITE_PATH = "/sites/CodeCraftAICommandCenter"
LIST_GUID = "19f8055f-32c3-4262-ab05-ba28ca94ffd2"
ORDERBY = "<OrderBy><FieldRef Name='Modified' Ascending='FALSE' /></OrderBy>"


def sp_token():
    cfg = _load_sp_config(CONFIG_PATH)
    data = Path(cfg["certPath"]).read_bytes()
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=None)
    except Exception:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=b"")
    app = msal.ConfidentialClientApplication(
        cfg["clientId"],
        authority="https://login.microsoftonline.com/%s" % cfg["tenantId"],
        client_credential={
            "private_key": key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode(),
            "thumbprint": cfg["certThumbprint"],
            "public_certificate": cert.public_bytes(Encoding.PEM).decode(),
        },
    )
    r = app.acquire_token_for_client(scopes=["https://%s/.default" % SP_HOST])
    if "access_token" not in r:
        raise RuntimeError("SP token failed: %s / %s" % (r.get("error"), str(r.get("error_description"))[:200]))
    return r["access_token"]


def main():
    apply = "--apply" in sys.argv
    tok = sp_token()
    base = "https://%s%s/_api/web/lists(guid'%s')" % (SP_HOST, SITE_PATH, LIST_GUID)
    h = {"Authorization": "Bearer " + tok, "Accept": "application/json;odata=nometadata"}
    r = requests.get(base + "/views", headers=h)
    print("GET views:", r.status_code)
    if r.status_code >= 300:
        print(r.text[:300]); return
    views = r.json().get("value", [])
    for v in views:
        print("  id=%s | '%s' | type=%s | hidden=%s | default=%s" % (
            v.get("Id"), v.get("Title"), v.get("ViewType2") or v.get("ViewType"),
            v.get("Hidden"), v.get("DefaultView")))
        print("      ViewQuery:", (v.get("ViewQuery") or "")[:120])
    if not apply:
        print("(read-only; pass --apply to set Board views to Modified DESC)")
        return
    # patch board views (ViewType2 == 'TILES' is the modern Board view type)
    for v in views:
        vt = (v.get("ViewType2") or "")
        if "TILE" not in vt.upper() and "BOARD" not in (v.get("Title") or "").upper():
            continue
        vq = v.get("ViewQuery") or ""
        # strip any existing OrderBy then prepend ours
        import re
        vq2 = re.sub(r"<OrderBy>.*?</OrderBy>", "", vq, flags=re.S)
        newq = ORDERBY + vq2
        body = json.dumps({"ViewQuery": newq})
        ph = {"Authorization": "Bearer " + tok, "Content-Type": "application/json;odata=nometadata",
              "Accept": "application/json;odata=nometadata", "X-HTTP-Method": "MERGE", "IF-MATCH": "*"}
        pr = requests.post(base + "/views(guid'%s')" % v.get("Id"), headers=ph, data=body)
        print("  PATCH '%s' -> %s %s" % (v.get("Title"), pr.status_code, "" if pr.status_code < 300 else pr.text[:160]))


if __name__ == "__main__":
    main()
