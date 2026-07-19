#!/usr/bin/env python3
"""cc-notify-client — send client emails via Microsoft Graph from hello@codeandcraft.ai.
Usage:
  cc-notify-client test <to>
  cc-notify-client started   <to> <clientName> <type>
  cc-notify-client delivered <to> <clientName> <url>
  cc-notify-client feedback  <to> <clientName>
"""
import sys, json
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

FROM = "hello@codeandcraft.ai"
GRAPH = "https://graph.microsoft.com/v1.0/users/%s/sendMail" % FROM
WRAP = ("<div style='font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:520px;color:#1a202c'>"
        "%s<p style='color:#718096;font-size:13px;margin-top:28px'>— Code&Craft</p></div>")


def send(to, subject, inner):
    tok = graph_token()
    body = {"message": {"subject": subject,
                        "body": {"contentType": "HTML", "content": WRAP % inner},
                        "toRecipients": [{"emailAddress": {"address": to}}]},
            "saveToSentItems": True}
    r = requests.post(GRAPH, headers={"Authorization": "Bearer " + tok,
                                      "Content-Type": "application/json"}, data=json.dumps(body))
    ok = r.status_code < 300
    print("sendMail ->", r.status_code, ("OK from " + FROM) if ok else r.text[:400])
    sys.exit(0 if ok else 1)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    kind, to = a[0], (a[1] if len(a) > 1 else "")
    name = a[2] if len(a) > 2 else "there"
    extra = a[3] if len(a) > 3 else ""
    if kind == "test":
        send(to, "Code&Craft — test email", "<p>This is a test send from <b>hello@codeandcraft.ai</b> via Microsoft Graph. If you're reading this, client email works. ✅</p>")
    elif kind == "started":
        send(to, "We've started building your %s" % extra,
             "<p>Hi %s,</p><p>Thanks — we've <b>started building your %s</b>. We'll email you the moment it's ready.</p>" % (name, extra))
    elif kind == "delivered":
        send(to, "Your project is ready",
             "<p>Hi %s,</p><p>Your project is <b>ready</b>:</p><p><a href='%s'>%s</a></p><p>Have a look and let us know what you think.</p>" % (name, extra, extra))
    elif kind == "feedback":
        send(to, "How did we do?",
             "<p>Hi %s,</p><p>Hope you're happy with the result. We'd love <b>30 seconds of feedback</b> — just reply to this email. Thank you for choosing Code&Craft.</p>" % name)
    else:
        print("unknown kind:", kind); sys.exit(1)


if __name__ == "__main__":
    main()
