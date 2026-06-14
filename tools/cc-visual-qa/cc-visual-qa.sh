#!/usr/bin/env bash
# cc-visual-qa — thin wrapper the qa-engineer agent invokes for a visual-QA step.
# SPEC ONLY: do NOT install on the server yet. Parent reviews, then copies to
# /usr/local/bin/cc-visual-qa and `chmod +x` it.
#
# Usage: cc-visual-qa <url> [--auth]
#   <url>     any target (public web/EDM, or M365 SharePoint with --auth)
#   --auth    replay the seeded M365 storageState (SharePoint behind login)
#
# Writes a timestamped PNG under $CC_VQA_OUT (default /root/.openclaw/vqa-shots)
# and prints the qa.mjs JSON line (so the agent can parse {ok,authed,...}).
set -euo pipefail

REPO="${CC_VQA_REPO:-/root/.openclaw/cc-visual-qa}"   # where qa.mjs lives on the VPS
OUTDIR="${CC_VQA_OUT:-/root/.openclaw/vqa-shots}"
mkdir -p "$OUTDIR"

URL="${1:-}"
if [ -z "$URL" ]; then
  echo '{"ok":false,"error":"usage: cc-visual-qa <url> [--auth]"}'
  exit 2
fi
shift || true

AUTH=""
for a in "$@"; do
  [ "$a" = "--auth" ] && AUTH="--auth"
done

SLUG=$(echo "$URL" | sed -E 's#https?://##; s#[^a-zA-Z0-9]+#-#g' | cut -c1-60)
OUT="$OUTDIR/$(date +%Y%m%d-%H%M%S)-${SLUG}.png"

cd "$REPO"
exec node qa.mjs "$URL" "$OUT" $AUTH
