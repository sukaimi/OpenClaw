"""
spclient.py - reusable SharePoint provisioning toolkit for the
Code&Craft AI Command Center site.

Consolidates the auth + Microsoft Graph boilerplate that the ad-hoc
/root/.openclaw/provision-*.py scripts copy-paste. Authenticates as the
SharePoint app registration via the certificate referenced in
/root/.openclaw/config.json (sharepoint.{tenantId,clientId,certPath,
certThumbprint}) and talks to Microsoft Graph v1.0.

Usage (run with the openclaw venv):

    PYTHONPATH=/root/.openclaw/sp-provision \
      /root/.openclaw/venv/bin/python -c \
      "from spclient import SP; sp=SP(); print(sp.site_id())"

Secrets are never printed or hardcoded - everything is read from
config.json by reference.
"""
import json
import requests
from pathlib import Path

import msal
from cryptography.hazmat.primitives.serialization import (
    pkcs12, Encoding, PrivateFormat, NoEncryption,
)

CONFIG_PATH = "/root/.openclaw/config.json"
GRAPH = "https://graph.microsoft.com/v1.0"
# Default site: contoso.sharepoint.com/sites/CodeCraftAICommandCenter
SITE_HOST = "contoso.sharepoint.com"
SITE_PATH = "/sites/CodeCraftAICommandCenter"


def _load_sp_config(config_path=CONFIG_PATH):
    """Read the sharepoint block from config.json (by reference, never logged)."""
    return json.load(open(config_path))["sharepoint"]


def graph_token(config_path=CONFIG_PATH):
    """Load config.json and return a Microsoft Graph bearer access token,
    authenticating as the app registration via its .pfx certificate.

    Mirrors the exact pattern used by the existing provision-*.py scripts:
    empty-password PFX (password=None, fallback b""), MSAL confidential
    client with .default scope.
    """
    cfg = _load_sp_config(config_path)
    data = Path(cfg["certPath"]).read_bytes()
    try:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=None)
    except Exception:
        key, cert, _ = pkcs12.load_key_and_certificates(data, password=b"")
    app = msal.ConfidentialClientApplication(
        cfg["clientId"],
        authority=f"https://login.microsoftonline.com/{cfg['tenantId']}",
        client_credential={
            "private_key": key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            ).decode(),
            "thumbprint": cfg["certThumbprint"],
            "public_certificate": cert.public_bytes(Encoding.PEM).decode(),
        },
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        # Never echo secrets; surface only the auth error fields.
        raise RuntimeError(
            "Graph token request failed: "
            f"{result.get('error')} / {result.get('error_description', '')[:200]}"
        )
    return result["access_token"]


class SP:
    """Helper around Microsoft Graph for provisioning the command-center site.

    Each instance acquires one token on construction and reuses it.

        sp = SP()
        sp.site_id()
        sp.lists()
        sp.create_list("My List", [{"name": "Foo", "text": {}}])
        sp.create_item("My List", {"Title": "row 1", "Foo": "bar"})
        sp.upload_file("Site Assets", "CommandCenter/x.jpg", data, "image/jpeg")
        sp.create_page("My-Page.aspx", "My Page", "<h2>Hi</h2>")
    """

    def __init__(self, config_path=CONFIG_PATH, site_host=SITE_HOST,
                 site_path=SITE_PATH):
        self.config_path = config_path
        self.site_host = site_host
        self.site_path = site_path
        self.graph = GRAPH
        self.token = graph_token(config_path)
        self.H = {"Authorization": "Bearer " + self.token}
        self.HJ = {**self.H, "Content-Type": "application/json"}
        self._site_id = None

    # -- low-level helpers ---------------------------------------------------
    def _get(self, url):
        return requests.get(url, headers=self.H)

    def _post(self, url, json_body=None, headers=None, data=None,
              content_type=None):
        h = headers if headers is not None else (
            self.HJ if json_body is not None else self.H)
        if content_type:
            h = {**self.H, "Content-Type": content_type}
        return requests.post(url, headers=h, json=json_body, data=data)

    # -- site / lists --------------------------------------------------------
    def site_id(self):
        """Resolve and cache the command-center site id."""
        if self._site_id is None:
            url = f"{self.graph}/sites/{self.site_host}:{self.site_path}"
            self._site_id = self._get(url).json()["id"]
        return self._site_id

    def lists(self):
        """Return {displayName: list_resource} for all lists on the site."""
        sid = self.site_id()
        r = self._get(f"{self.graph}/sites/{sid}/lists?$top=100")
        return {l["displayName"]: l for l in r.json().get("value", [])}

    def list_id(self, list_name):
        """Resolve a list's id by display name."""
        lst = self.lists().get(list_name)
        if not lst:
            raise KeyError(f"list not found: {list_name!r}")
        return lst["id"]

    def create_list(self, display_name, columns, template="genericList"):
        """Create a list. `columns` is a list of Graph columnDefinition dicts,
        e.g. [{"name": "Status", "displayName": "Status",
               "choice": {"choices": [...], "displayAs": "dropDownMenu"}}].

        Idempotent: returns the existing list resource if one already exists.
        Returns the created/existing list JSON (raises on a real failure).
        """
        sid = self.site_id()
        existing = self.lists()
        if display_name in existing:
            return existing[display_name]
        body = {
            "displayName": display_name,
            "list": {"template": template},
            "columns": columns,
        }
        r = self._post(f"{self.graph}/sites/{sid}/lists", json_body=body)
        if r.status_code != 201:
            raise RuntimeError(
                f"create_list {display_name!r} failed "
                f"{r.status_code}: {r.text[:400]}"
            )
        return r.json()

    def rename_title_column(self, list_name, new_display_name):
        """Rename the built-in 'Title' column of a list (matches the
        provision-*.py convention of renaming Title to a domain label)."""
        sid = self.site_id()
        lid = self.list_id(list_name)
        cols = self._get(
            f"{self.graph}/sites/{sid}/lists/{lid}/columns"
        ).json()["value"]
        title = next((c for c in cols if c.get("name") == "Title"), None)
        if not title:
            return None
        return requests.patch(
            f"{self.graph}/sites/{sid}/lists/{lid}/columns/{title['id']}",
            headers=self.HJ,
            json={"displayName": new_display_name},
        )

    def list_columns(self, list_name, writable_only=False):
        """Return the column definitions for a list."""
        sid = self.site_id()
        lid = self.list_id(list_name)
        cols = self._get(
            f"{self.graph}/sites/{sid}/lists/{lid}/columns"
        ).json()["value"]
        if writable_only:
            cols = [c for c in cols if not c.get("readOnly")]
        return cols

    # -- items ---------------------------------------------------------------
    def items(self, list_name, top=500):
        """Return list items with $expand=fields."""
        sid = self.site_id()
        lid = self.list_id(list_name)
        r = self._get(
            f"{self.graph}/sites/{sid}/lists/{lid}/items"
            f"?$expand=fields&$top={top}"
        )
        return r.json().get("value", [])

    def create_item(self, list_name, fields):
        """Create a list item. `fields` is a dict of column internal-name ->
        value, e.g. {"Title": "Project No 1", "Status": "Intake"}.
        Returns the created item JSON (raises on failure)."""
        sid = self.site_id()
        lid = self.list_id(list_name)
        r = self._post(
            f"{self.graph}/sites/{sid}/lists/{lid}/items",
            json_body={"fields": fields},
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"create_item in {list_name!r} failed "
                f"{r.status_code}: {r.text[:400]}"
            )
        return r.json()

    # -- drives / files ------------------------------------------------------
    def drives(self):
        """Return the document libraries (drives) on the site."""
        sid = self.site_id()
        return self._get(f"{self.graph}/sites/{sid}/drives").json()["value"]

    def drive_id(self, drive_name):
        """Resolve a drive id by name. Accepts 'Site Assets'/'SiteAssets'
        aliasing as the existing scripts do; falls back to the first drive."""
        drives = self.drives()
        aliases = {drive_name}
        if drive_name in ("Site Assets", "SiteAssets"):
            aliases = {"Site Assets", "SiteAssets"}
        d = next((d for d in drives if d["name"] in aliases), None)
        if not d:
            raise KeyError(f"drive not found: {drive_name!r}")
        return d["id"]

    def upload_file(self, drive_name, server_path, content_bytes,
                    content_type):
        """Upload bytes to a drive via the simple PUT content API.
        `server_path` is the path relative to the drive root, e.g.
        'CommandCenter/hero.jpg'. Returns the created drive item JSON."""
        did = self.drive_id(drive_name)
        path = server_path.lstrip("/")
        url = f"{self.graph}/drives/{did}/root:/{path}:/content"
        r = requests.put(
            url,
            headers={**self.H, "Content-Type": content_type},
            data=content_bytes,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"upload_file {server_path!r} failed "
                f"{r.status_code}: {r.text[:400]}"
            )
        return r.json()

    # -- pages ---------------------------------------------------------------
    def _text_canvas(self, inner_html):
        """One-column canvas with a single text web part (the layout the
        existing provision pages use)."""
        return {
            "horizontalSections": [{
                "layout": "oneColumn", "id": "1",
                "columns": [{
                    "id": "1", "width": 12,
                    "webparts": [{
                        "@odata.type": "#microsoft.graph.textWebPart",
                        "innerHtml": inner_html,
                    }],
                }],
            }]
        }

    def create_page(self, name, title, inner_html, page_layout="article",
                    publish=True):
        """Create a SharePoint site page with a single text web part holding
        `inner_html`, then publish it. Mirrors provision-share-page.py
        (POST /sites/{sid}/pages, then .../microsoft.graph.sitePage/publish),
        including the v1.0 -> beta fallback. Returns the created page JSON."""
        sid = self.site_id()
        page = {
            "@odata.type": "#microsoft.graph.sitePage",
            "name": name,
            "title": title,
            "pageLayout": page_layout,
            "canvasLayout": self._text_canvas(inner_html),
        }
        last = None
        for api in ("v1.0", "beta"):
            r = requests.post(
                f"https://graph.microsoft.com/{api}/sites/{sid}/pages",
                headers=self.HJ, json=page,
            )
            last = r
            if r.status_code in (200, 201):
                created = r.json()
                if publish:
                    pid = created["id"]
                    requests.post(
                        f"https://graph.microsoft.com/{api}/sites/{sid}/pages/"
                        f"{pid}/microsoft.graph.sitePage/publish",
                        headers=self.H,
                    )
                return created
        raise RuntimeError(
            f"create_page {name!r} failed "
            f"{last.status_code}: {last.text[:400]}"
        )


if __name__ == "__main__":
    # Read-only smoke test: resolve the site id and list the lists.
    sp = SP()
    print("site_id:", sp.site_id())
    print("lists:", sorted(sp.lists().keys()))
