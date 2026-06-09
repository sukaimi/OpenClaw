#!/usr/bin/env python3
"""Wire real Pexels image URLs into the asset-manifest's image slots (the missing
discovery->build step). After this, the static-web build emits real <img src> URLs."""
import json

MANI = "/srv/projects/JOB0003/discovery/manifest-assembler/output/asset-manifest.json"
PEX = "/srv/projects/JOB0003/assets/pexels/output/pexels-assets.json"

m = json.load(open(MANI))
p = json.load(open(PEX))

# Group real Pexels download links by the search's intent (mood/query), else flat.
links = [r["downloadLink"] for s in p.get("searches", []) for r in s.get("results", [])]
if not links:
    raise SystemExit("no Pexels links available")

imgs = m.get("images", [])
for i, img in enumerate(imgs):
    img["path"] = links[i % len(links)]          # real remote URL -> becomes the <img src>
    img["sourceUrl"] = links[i % len(links)]     # overwrite the fake cdn.example.com
json.dump(m, open(MANI, "w"), indent=2)
print("wired %d manifest images to real Pexels URLs" % len(imgs))
for img in imgs[:3]:
    print("  %s -> %s" % (img.get("id"), img.get("path")))
