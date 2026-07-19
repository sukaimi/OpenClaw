"""
cc_sp_scorer.py — Phase 1 page scoring for the SP Classic→Modern pipeline.
Reads sp-expect.json, scores each page, writes sp-scored.json.

Usage:
    python3 cc_sp_scorer.py --job <job_dir> --out <path/to/sp-scored.json>
"""
import argparse, json, math, os, sys
from datetime import datetime, timezone

TIER1_HOMEPAGE_NAMES = {"home.aspx", "default.aspx"}
INBOUND_LINK_TIER1 = 2
INBOUND_LINK_TIER2 = 1
RECENCY_TIER1_DAYS = 180
RECENCY_TIER2_DAYS = 365


def days_since(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


def recency_score(days):
    """0–100 recency score. 0 days = 100, 730+ days = 0."""
    if days is None:
        return 0
    # Upper clamp guards against future lastModified timestamps (negative days)
    # producing scores above 100 and distorting priority ordering.
    return min(100, max(0, round(100 * (1 - days / 730))))


def content_length_score(src_len):
    """0–100 score based on sourceTextLen. 0=0, 5000+=100."""
    if not src_len:
        return 0
    return min(100, round(src_len / 50))


def count_inbound(page_name, all_pages):
    """Count how many other pages reference this page name in their content."""
    target = page_name.lower().replace(".aspx", "")
    count = 0
    for p in all_pages:
        if p["name"].lower() == page_name.lower():
            continue
        text = (p.get("sourceText") or "").lower()
        if target in text:
            count += 1
    return count


def score_page(page, all_pages):
    name_lower = page["name"].lower()
    is_homepage = name_lower in TIER1_HOMEPAGE_NAMES

    days = days_since(page.get("lastModified"))
    inbound = count_inbound(page["name"], all_pages)
    src_len = page.get("sourceTextLen", 0)
    webparts = page.get("webparts", [])

    # Complexity: flag pages with many web parts or long content
    complexity_flag = len(webparts) > 5 or src_len > 8000

    # Tier logic
    if is_homepage or (inbound >= INBOUND_LINK_TIER1 and (days is None or days <= RECENCY_TIER1_DAYS)):
        tier = 1
    elif inbound >= INBOUND_LINK_TIER2 or (days is not None and days <= RECENCY_TIER2_DAYS):
        tier = 2
    else:
        tier = 3

    # Priority score 0–100
    rec_score = recency_score(days)
    len_score = content_length_score(src_len)
    inbound_norm = min(100, inbound * 30)
    priority_score = round(inbound_norm * 0.30 + rec_score * 0.40 + len_score * 0.30)
    # Homepage always gets max priority
    if is_homepage:
        priority_score = 100

    return {
        "name": page["name"],
        "title": page.get("title", ""),
        "tier": tier,
        "priority_score": priority_score,
        "complexity_flag": complexity_flag,
        "signals": {
            "is_homepage": is_homepage,
            "inbound_links": inbound,
            "days_since_modified": days,
            "source_text_len": src_len,
            "webpart_count": len(webparts),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="Job directory containing sp-expect.json")
    ap.add_argument("--out", required=True, help="Output path for sp-scored.json")
    args = ap.parse_args()

    expect_path = os.path.join(args.job, "sp-expect.json")
    if not os.path.exists(expect_path):
        print("[scorer] ERROR: %s not found" % expect_path)
        sys.exit(1)

    expect = json.load(open(expect_path, encoding="utf-8"))
    pages = expect.get("pages", [])

    if not pages:
        # Fail-closed: an empty page manifest is invalid input (likely an incomplete
        # or failed audit) and must not silently succeed with an empty score set.
        print("[scorer] ERROR: no pages in sp-expect.json — refusing to write empty score set")
        sys.exit(1)

    scored = [score_page(p, pages) for p in pages]
    scored.sort(key=lambda x: (x["tier"], -x["priority_score"]))

    out = {"scored": scored}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2, ensure_ascii=False)

    tier_counts = {1: 0, 2: 0, 3: 0}
    for s in scored:
        tier_counts[s["tier"]] += 1
    print("[scorer] wrote %s — %d pages: T1=%d T2=%d T3=%d" % (
        args.out, len(scored), tier_counts[1], tier_counts[2], tier_counts[3]))


if __name__ == "__main__":
    main()
