#!/bin/bash
# Code&Craft autonomous dispatch supervisor — self-healing drain loop WITH verify gate.
# - ONE bounded agent turn per card; survives any single turn dying (crash/timeout).
# - WIP=1: finish in-Build cards before claiming new Intake.
# - VERIFY GATE: the agent moves finished work to "Internal QA"; only a deterministic
#   cc-verify PASS promotes a card to Closed. A FAIL bounces it back to Build (and BLOCKS
#   it on the 2nd consecutive fail). The agent CANNOT close its own card.
# - systemd (Restart=on-failure) restarts THIS loop if the loop process itself dies.
# - Exits 0 when every card is Closed or BLOCKED.
set -u
export PATH=/usr/local/bin:/usr/bin:/bin
PROJ="${1:-JOB0003}"
AGENT_TIMEOUT=900
HARD_TIMEOUT=960
MAX_STUCK=3
SRV="/srv/projects/$PROJ"
FAILDIR="/run/cc-verify"; mkdir -p "$FAILDIR"
DISPATCH="/root/.openclaw/workspace-delivery-lead/DISPATCH.md"
PRE="Phase 1 dispatch tick. Follow $DISPATCH exactly. Do exactly ONE card then STOP. Move finished work to Internal QA — do NOT set Closed yourself (the verifier does). Do NOT schedule cron."

board_lines() { cc-board read "$PROJ" 2>/dev/null | grep -E '\[[A-Za-z ]+\]'; }
build_ids()   { board_lines | grep '\[Build\]' | grep -v 'BLOCKED' | awk '{print $1}' | tr '\n' ' '; }
actionable()  { board_lines | grep -v '\[Closed\]' | grep -v 'BLOCKED' | grep -q .; }
qa_closed()   { board_lines | grep -E '\[(Internal QA|Closed)\]' | grep -v 'BLOCKED' | awk '{print $1}'; }
stage_of()    { board_lines | grep -E "^[[:space:]]*$1[[:space:]]" | grep -oE '\[[A-Za-z ]+\]' | head -1; }
board_sig()   { board_lines | md5sum | cut -d' ' -f1; }
file_sig()    { find "$SRV" -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1; }
gw_up()       { openclaw health >/dev/null 2>&1; }

# The gate: promote passing QA->Closed; bounce failing QA/Closed->Build; BLOCK on 2nd fail.
verify_sweep() {
  local id out rc reason cf n
  for id in $(qa_closed); do
    out="$(cc-verify "$id" 2>/dev/null)"; rc=$?
    reason="$(echo "$out" | sed -E 's/^(PASS|FAIL) [0-9]+ — //')"
    cf="$FAILDIR/$id"
    if [ "$rc" -eq 0 ]; then
      rm -f "$cf"
      if stage_of "$id" | grep -q "Internal QA"; then
        cc-board move "$id" Closed "VERIFIED: $reason" >/dev/null 2>&1
        echo "[cc-dispatch] verify PASS -> Closed $id"
      fi
    elif [ "$rc" -eq 1 ]; then
      n=$(( $(cat "$cf" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$cf"
      if [ "$n" -ge 2 ]; then
        cc-board move "$id" Build "BLOCKED: fails verification ($reason). Needs human/input." >/dev/null 2>&1
        echo "[cc-dispatch] verify FAIL x2 -> BLOCKED $id: $reason"
      else
        cc-board move "$id" Build "VERIFY FAILED: $reason. Reworking." >/dev/null 2>&1
        echo "[cc-dispatch] verify FAIL -> Build $id: $reason"
      fi
    fi
  done
}

echo "[cc-dispatch] START proj=$PROJ $(date -u +%FT%TZ)"
stuck=0
while true; do
  verify_sweep
  actionable || { echo "[cc-dispatch] DRAINED proj=$PROJ $(date -u +%FT%TZ) — exiting 0"; exit 0; }
  if ! gw_up; then echo "[cc-dispatch] gateway down — waiting"; sleep 15; continue; fi
  b0="$(board_sig)"; f0="$(file_sig)"
  bids="$(build_ids)"
  if [ -n "$bids" ]; then
    MSG="$PRE WIP LIMIT: cards already in Build (ids: $bids). Do NOT claim a new Intake card. Pick ONE of those, finish it, move it to Internal QA (verifier will Close it), or mark BLOCKED if truly stuck."
  else
    MSG="$PRE No cards in Build. Claim the next Intake card (Intake->Build), do the work, move it to Internal QA (verifier will Close it), or mark BLOCKED."
  fi
  timeout "$HARD_TIMEOUT" openclaw agent --agent main --timeout "$AGENT_TIMEOUT" --message "$MSG" >/dev/null 2>&1
  rc=$?
  b1="$(board_sig)"; f1="$(file_sig)"
  if [ "$b0" = "$b1" ] && [ "$f0" = "$f1" ]; then
    stuck=$((stuck+1)); echo "[cc-dispatch] no-progress turn (rc=$rc) stuck=$stuck/$MAX_STUCK"
    if [ "$stuck" -ge "$MAX_STUCK" ]; then
      bid="$(board_lines | grep -v '\[Closed\]' | grep -v 'BLOCKED' | head -1 | awk '{print $1}')"
      [ -n "$bid" ] && cc-board move "$bid" Build "BLOCKED: supervisor — no progress after $MAX_STUCK turns." >/dev/null 2>&1
      stuck=0
    fi
  else
    stuck=0; echo "[cc-dispatch] progress (rc=$rc)"
  fi
  sleep 3
done
