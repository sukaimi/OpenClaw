#!/usr/bin/env python3
"""cc-archive-purge [--dry] — enforce the 3-month archive retention. Scans /srv/cc-archive/*/archived.json
and deletes any archive whose purgeAfter timestamp has passed. Intended to run daily via cron.
--dry lists what would be purged without deleting."""
import os, json, time, shutil, sys

ARCHIVE = "/srv/cc-archive"


def main():
    dry = "--dry" in sys.argv
    if not os.path.isdir(ARCHIVE):
        print("no archive dir"); return
    now = time.time()
    purged = kept = 0
    for name in sorted(os.listdir(ARCHIVE)):
        d = os.path.join(ARCHIVE, name)
        stamp = os.path.join(d, "archived.json")
        if not os.path.isdir(d) or not os.path.exists(stamp):
            continue
        try:
            pa = json.load(open(stamp)).get("purgeAfter", 0)
        except Exception:
            pa = 0
        if pa and now >= pa:
            days = int((now - pa) / 86400)
            if dry:
                print("WOULD PURGE", name, "(expired %dd ago)" % days)
            else:
                shutil.rmtree(d, ignore_errors=True)
                print("PURGED", name, "(expired %dd ago)" % days)
            purged += 1
        else:
            kept += 1
    print("%s: %d purged, %d retained" % ("DRY" if dry else "purge", purged, kept))


if __name__ == "__main__":
    main()
