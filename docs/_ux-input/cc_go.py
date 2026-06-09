#!/usr/bin/env python3
"""cc-go [client-email] — operator approves a request:
read the latest Tally brief, parse it, generate the EXACT Stripe pay link, email it to the
client, and record awaiting-payment. No arg = latest Tally submission.
Tally briefs are read from CC_TALLY_MBX (default sukaimi@codeandcanvas.io), filtered to notifications@tally.so."""
import sys, os, re, json, subprocess, html as htmllib
sys.path.insert(0, "/root/.openclaw/sp-provision")
from spclient import graph_token
import requests

MBX = os.environ.get("CC_TALLY_MBX", "sukaimi@codeandcanvas.io")
PENDING = "/root/.openclaw/phase2/awaiting-payment.jsonl"
LABELS = ["Your name", "Your email", "What do you need?", "How many pages?", "Brand / business name",
          "Headline / main message", "Body copy", "Call-to-action text", "Upload images",
          "Email subject line", "Sender name", "CTA link (URL)", "Anything else?", "Agreement"]
def map_type(s):
    # tolerant: works even if the option label carries a price suffix etc.
    s = (s or "").lower()
    if "multi" in s:
        return "multipage_site"
    if "edm" in s or "email" in s:
        return "edm"
    if "single" in s or "page" in s or "landing" in s:
        return "single_page"
    return "multipage_site"


def tok():
    return graph_token()


def latest_tally(match_email=None):
    r = requests.get("https://graph.microsoft.com/v1.0/users/%s/messages?$top=25&$select=from,body,receivedDateTime" % MBX,
                     headers={"Authorization": "Bearer " + tok()})
    for m in r.json().get("value", []):
        frm = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
        if "notifications@tally.so" not in frm:
            continue
        body = (m.get("body") or {}).get("content", "")
        if match_email and match_email.lower() not in body.lower():
            continue
        return body
    return None


def strip_tags(h):
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|div|h[1-6]|tr|td)>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    return htmllib.unescape(h)


def parse_brief(htmlbody):
    imgs = re.findall(r'href="(https://[^"]*(?:tally|storage)[^"]*)"', htmlbody)
    text = re.sub(r"[ \t]+", " ", strip_tags(htmlbody))
    pos = sorted((text.find(l), l) for l in LABELS if text.find(l) >= 0)
    f = {}
    for idx, (i, lab) in enumerate(pos):
        s = i + len(lab)
        e = pos[idx + 1][0] if idx + 1 < len(pos) else len(text)
        f[lab] = text[s:e].strip()
    typ = map_type(f.get("What do you need?", ""))
    pm = re.search(r"\d+", f.get("How many pages?", "1"))
    pages = int(pm.group()) if pm else 1
    sections = []
    if f.get("Headline / main message") or f.get("Body copy"):
        sections.append({"type": "hero", "headline": f.get("Headline / main message", ""),
                         "body": f.get("Body copy", ""), "cta": f.get("Call-to-action text", "")})
    return {"clientName": f.get("Your name", ""), "clientEmail": f.get("Your email", ""),
            "brand": f.get("Brand / business name", ""), "type": typ, "pages": pages,
            "sections": sections, "imageUrls": imgs,
            "ctaUrl": f.get("CTA link (URL)", "").strip()}


def email_client(to, url, brief):
    total = brief["pages"] * 10
    inner = ("<div style='font-family:system-ui,Segoe UI,Arial;max-width:520px;color:#1a202c'>"
             "<p>Hi %s,</p><p>Thanks for your request — a <b>%s</b> (%d page%s). To get started, "
             "please complete payment:</p><p><a href='%s' style='background:#1a202c;color:#fff;"
             "padding:10px 18px;border-radius:6px;text-decoration:none'>Pay SGD %d</a></p>"
             "<p style='color:#718096;font-size:13px'>— Code&Craft</p></div>"
             % (brief["clientName"] or "there", brief["type"].replace("_", " "), brief["pages"],
                "" if brief["pages"] == 1 else "s", url, total))
    body = {"message": {"subject": "Your Code&Craft quote — pay to start",
                        "body": {"contentType": "HTML", "content": inner},
                        "toRecipients": [{"emailAddress": {"address": to}}]}, "saveToSentItems": True}
    r = requests.post("https://graph.microsoft.com/v1.0/users/hello@codeandcraft.ai/sendMail",
                      headers={"Authorization": "Bearer " + tok(), "Content-Type": "application/json"},
                      data=json.dumps(body))
    return r.status_code


def main():
    match = sys.argv[1] if len(sys.argv) > 1 else None
    body = latest_tally(match)
    if not body:
        print("no Tally brief found" + ((" for " + match) if match else "") + " in " + MBX); sys.exit(1)
    brief = parse_brief(body)
    print("BRIEF:", json.dumps({k: brief[k] for k in ("clientName", "clientEmail", "brand", "type", "pages")}))
    print("images:", len(brief["imageUrls"]), "| sections:", len(brief["sections"]))
    url = subprocess.run(["cc-paylink", str(brief["pages"]), brief["clientEmail"]],
                         capture_output=True, text=True).stdout.strip()
    print("paylink:", url)
    code = email_client(brief["clientEmail"], url, brief)
    print("client emailed:", code, "(<300 = sent)")
    os.makedirs(os.path.dirname(PENDING), exist_ok=True)
    with open(PENDING, "a") as fh:
        fh.write(json.dumps({"brief": brief, "paylink": url, "status": "awaiting-payment"}) + "\n")
    print("recorded awaiting-payment.")


if __name__ == "__main__":
    main()
