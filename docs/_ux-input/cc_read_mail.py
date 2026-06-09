#!/usr/bin/env python3
"""cc-read-mail — read the hello@codeandcraft.ai inbox via Graph (needs Mail.Read).
Usage: cc-read-mail list [n] | find <from-email>"""
import sys, os
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

MBX = os.environ.get("CC_MBX", "hello@codeandcraft.ai")
BASE = "https://graph.microsoft.com/v1.0/users/%s" % MBX


def get(path):
    return requests.get(BASE + "/" + path, headers={"Authorization": "Bearer " + graph_token()})


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        n = sys.argv[2] if len(sys.argv) > 2 else "5"
        r = get("messages?$top=%s&$select=subject,from,receivedDateTime,bodyPreview" % n)
        print("Mail.Read status:", r.status_code)
        if r.status_code < 300:
            for m in r.json().get("value", []):
                frm = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "?")
                print("  -", (m.get("receivedDateTime") or "")[:19], "|", frm, "|", (m.get("subject") or "")[:55])
        else:
            print("  ", r.text[:300])
    elif cmd == "find":
        email = sys.argv[2].lower()
        r = get("messages?$top=25&$select=subject,from,receivedDateTime,body")
        if r.status_code >= 300:
            print("status", r.status_code, r.text[:200]); return
        for m in r.json().get("value", []):
            frm = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
            body = (m.get("body") or {}).get("content", "")
            if email in frm or email in body.lower():
                print("MATCH:", (m.get("subject") or "")[:60])
                print(body[:1500])
                return
        print("no message matching", email)


if __name__ == "__main__":
    main()
