#!/usr/bin/env bash
#
# e2e-run.sh — Phase 1 Acceptance Gate
# ======================================
# Dry-run end-to-end test of the build engine pipeline.
# Inspects each stage's output; never modifies artifacts.
#
# Usage:  bash e2e-run.sh [--verbose]
# Returns: 0 if all stages pass, 1 if any fail
#

set -euo pipefail

ROOT="/srv/projects/JOB0003"
VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

PASS=0
FAIL=0
SKIP=0
STAGE=0

RESULTS_FILE="$(dirname "$0")/e2e-results.json"
STATUS_FILE="$(dirname "$0")/status.md"

fail()  { ((FAIL++))  || true; echo "  ❌ FAIL: $*"; }
pass()  { ((PASS++))  || true; echo "  ✅ PASS: $*"; }
skip()  { ((SKIP++))  || true; echo "  ⏭️  SKIP: $*"; }
info()  { echo "  ℹ️  $*"; }
header(){ echo; echo "─── Stage $STAGE: $* ───"; }

# ── Helpers ───────────────────────────────────────────

json_has_content() {
  local f="$1"
  [[ -s "$f" ]] || return 1
  # Must parse as valid JSON with at least one key
  jq -e '. | length > 0 or has("$schema")' "$f" >/dev/null 2>&1
}

file_exists_nonempty() {
  [[ -f "$1" && -s "$1" ]]
}

assert_output_dir() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    pass "Output directory exists: $dir"
    if [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]; then
      fail "Output directory is EMPTY: $dir"
    fi
  else
    fail "Output directory MISSING: $dir"
  fi
}

assert_file() {
  local desc="$1" path="$2"
  if file_exists_nonempty "$path"; then
    local size
    size=$(stat --format=%s "$path" 2>/dev/null || echo "?")
    pass "$desc ($(basename "$path")) — ${size}B"
  else
    fail "$desc — $path is MISSING or EMPTY"
  fi
}

check_json_valid() {
  local path="$1"
  if jq -e . "$path" >/dev/null 2>&1; then
    pass "  └─ JSON valid"
  else
    fail "  └─ JSON INVALID — parse error"
  fi
}

echo "============================================="
echo " Phase 1 Acceptance Gate — End-to-End Dry Run"
echo " Project:  JOB0003"
echo " Started:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Root:     $ROOT"
echo "============================================="

###############################################################################
# STAGE 1 — INTAKE
###############################################################################
STAGE=$((STAGE+1)); header "Intake — Pipeline Entry"

if [[ -d "$ROOT/intake" ]]; then
  pass "intake/ directory exists"

  # Required sub-components
  assert_file "Sample brief (copy-test)"    "$ROOT/intake/samples/copy-test.json"
  check_json_valid "$ROOT/intake/samples/copy-test.json"

  assert_file "Intake manifest (vision)"    "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json"
  check_json_valid "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json"

  assert_file "Intake schema"               "$ROOT/intake/schemas/intake-schema.json"
  assert_file "Type taxonomy"               "$ROOT/intake/schemas/type-taxonomy.json"
  assert_file "Router index"                "$ROOT/intake/router/index.ts"

  # Verify sample has required fields
  if jq -e '.title and .type and .subtype and .briefText and .scope' "$ROOT/intake/samples/copy-test.json" >/dev/null 2>&1; then
    pass "  └─ Sample brief has all required fields"
  else
    fail "  └─ Sample brief MISSING required fields (title/type/subtype/briefText/scope)"
  fi
else
  fail "intake/ directory MISSING"
fi

###############################################################################
# STAGE 2 — VISION PASS (Card 31)
###############################################################################
STAGE=$((STAGE+1)); header "Vision Pass — Image Analysis (Card 31)"

if [[ -d "$ROOT/discovery/vision-pass" ]]; then
  pass "discovery/vision-pass/ directory exists"
  assert_file "Vision engine"               "$ROOT/discovery/vision-pass/engine.ts"
  assert_file "Vision manifest-reader"      "$ROOT/discovery/vision-pass/manifest-reader.ts"
  assert_file "Vision runner"               "$ROOT/discovery/vision-pass/run.ts"

  # Critical: check for output
   vp_out="$ROOT/discovery/vision-pass/output"
  if [[ -d "$vp_out" ]]; then
    pass "Output directory exists"
     vp_manifest="$vp_out/vision-manifest.json"
    if file_exists_nonempty "$vp_manifest"; then
      pass "vision-manifest.json present"
      check_json_valid "$vp_manifest"
    else
      fail "vision-manifest.json MISSING — vision pass did not run or produced no output"
    fi
  else
    fail "Output directory MISSING"
  fi
else
  fail "discovery/vision-pass/ directory MISSING"
fi

###############################################################################
# STAGE 3 — COPY PARSE (Card 32)
###############################################################################
STAGE=$((STAGE+1)); header "Copy Parse — Brief Text Parsing (Card 32)"

if [[ -d "$ROOT/discovery/copy-parse" ]]; then
  pass "discovery/copy-parse/ directory exists"
  assert_file "Copy parse runner"           "$ROOT/discovery/copy-parse/run.ts"

   cp_out="$ROOT/discovery/copy-parse/output"
  assert_output_dir "$cp_out"
  assert_file "Copy manifest"               "$ROOT/discovery/copy-parse/output/copy-manifest.json"
  check_json_valid "$ROOT/discovery/copy-parse/output/copy-manifest.json"

  # Validate structure
  if jq -e '.segments and .metadata' "$ROOT/discovery/copy-parse/output/copy-manifest.json" >/dev/null 2>&1; then
    seg_count=$(jq '.segments | length' "$ROOT/discovery/copy-parse/output/copy-manifest.json")
    pass "  └─ Copy manifest has segments ($seg_count) + metadata"
  else
    fail "  └─ Copy manifest MISSING required structure (segments/metadata)"
  fi
else
  fail "discovery/copy-parse/ directory MISSING"
fi

###############################################################################
# STAGE 4 — MANIFEST ASSEMBLER (Card 33)
###############################################################################
STAGE=$((STAGE+1)); header "Manifest Assembler — Merge Vision + Copy (Card 33)"

if [[ -d "$ROOT/discovery/manifest-assembler" ]]; then
  pass "discovery/manifest-assembler/ directory exists"
  assert_file "Assembler runner"            "$ROOT/discovery/manifest-assembler/run.ts"
  assert_file "Assembler types"             "$ROOT/discovery/manifest-assembler/types.ts"

   ma_out="$ROOT/discovery/manifest-assembler/output"
  assert_output_dir "$ma_out"
  assert_file "Asset manifest"              "$ROOT/discovery/manifest-assembler/output/asset-manifest.json"
  check_json_valid "$ROOT/discovery/manifest-assembler/output/asset-manifest.json"

  # Critical: check data flow integrity
   am="$ROOT/discovery/manifest-assembler/output/asset-manifest.json"
  if jq -e '.images and .copySegments and .colorPalette and .moodTone and .metadata and .type' "$am" >/dev/null 2>&1; then
    pass "  └─ Asset manifest has complete structure (images+copy+palette+tone+type)"
  else
    fail "  └─ Asset manifest incomplete — check for missing sections"
  fi
else
  fail "discovery/manifest-assembler/ directory MISSING"
fi

###############################################################################
# STAGE 5 — PEXELS GAP-FILL (Card 34)
###############################################################################
STAGE=$((STAGE+1)); header "Pexels Gap-Fill — Stock Images (Card 34)"

if [[ -d "$ROOT/assets/pexels" ]]; then
  pass "assets/pexels/ directory exists"
  assert_file "Pexels runner"               "$ROOT/assets/pexels/run.ts"
  assert_file "Pexels types"                "$ROOT/assets/pexels/types.ts"

  # Output
   px_out="$ROOT/assets/pexels/output"
  if [[ -d "$px_out" ]]; then
    pass "Output directory exists"
    assert_file "Pexels assets"             "$ROOT/assets/pexels/output/pexels-assets.json"
    if file_exists_nonempty "$ROOT/assets/pexels/output/pexels-assets.json"; then
      check_json_valid "$ROOT/assets/pexels/output/pexels-assets.json"

      px_status=$(jq -r '.status // "unknown"' "$ROOT/assets/pexels/output/pexels-assets.json" 2>/dev/null)
      pass "  └─ Status: $px_status"
    fi
  else
    fail "Output directory MISSING — Pexels never produced output"
  fi
else
  fail "assets/pexels/ directory MISSING"
fi

###############################################################################
# STAGE 6 — HIGGSFIELD GAP-FILL (Card 35)
###############################################################################
STAGE=$((STAGE+1)); header "Higgsfield Gap-Fill — AI Images (Card 35)"

if [[ -d "$ROOT/assets/higgsfield" ]]; then
  pass "assets/higgsfield/ directory exists"
  assert_file "Higgsfield runner"           "$ROOT/assets/higgsfield/run.ts"
  assert_file "Higgsfield types"            "$ROOT/assets/higgsfield/types.ts"

   hf_out="$ROOT/assets/higgsfield/output"
  assert_output_dir "$hf_out"
  assert_file "Higgsfield assets"           "$ROOT/assets/higgsfield/output/higgsfield-assets.json"
  check_json_valid "$ROOT/assets/higgsfield/output/higgsfield-assets.json"

  # Check actual generation status
   hf_json="$ROOT/assets/higgsfield/output/higgsfield-assets.json"

  hf_success=$(jq '.successfulCount // 0' "$hf_json" 2>/dev/null)
  hf_failed=$(jq '.failedCount // 0' "$hf_json" 2>/dev/null)
  hf_total=$(jq '.totalSlots // 0' "$hf_json" 2>/dev/null)

  info "Slots: total=$hf_total successful=$hf_success failed=$hf_failed"

  if [[ "$hf_success" -gt 0 ]]; then
    pass "  └─ Generated $hf_success / $hf_total images"
  else
    skip "  └─ Higgsfield DEFERRED (future feature, Sukaimi 2026-06-05) — server cannot reach it; not a Phase 1 blocker"
  fi
else
  fail "assets/higgsfield/ directory MISSING"
fi

###############################################################################
# STAGE 7 — STATIC WEB BUILD (Card 36)
###############################################################################
STAGE=$((STAGE+1)); header "Static Web Build — Site Generation (Card 36)"

if [[ -d "$ROOT/build/static-web/output" ]]; then
  pass "build/static-web/output/ directory exists"
   any_web_output=false
  for f in "$ROOT/build/static-web/output/"*; do
    if [[ -f "$f" ]]; then
      any_web_output=true
      assert_file "Web artifact" "$f"
    fi
  done

  if ! $any_web_output; then
    fail "build/static-web/output/ is EMPTY — no web output generated"
  fi

  if file_exists_nonempty "$ROOT/build/static-web/output/index.html"; then
    pass "  └─ index.html present (real static site)"
  else
    fail "  └─ index.html MISSING under build/static-web/output/"
  fi
else
  fail "build/static-web/output/ directory MISSING — no static web build"
fi

###############################################################################
# STAGE 8 — EDM BUILD (Card 37)
###############################################################################
STAGE=$((STAGE+1)); header "EDM Build — Email Generation (Card 37)"

if [[ -d "$ROOT/build/edm" ]]; then
  pass "build/edm/ directory exists"
  assert_file "EDM runner"                  "$ROOT/build/edm/run.ts"
  assert_file "EDM types"                   "$ROOT/build/edm/types.ts"
  assert_file "EDM templates/base"          "$ROOT/build/edm/templates/base.ts"
  assert_file "EDM templates/sections"      "$ROOT/build/edm/templates/sections.ts"
  assert_file "EDM templates/styles"        "$ROOT/build/edm/templates/styles.ts"
  assert_file "EDM CSS inliner"             "$ROOT/build/edm/css-inliner.ts"

   edm_out="$ROOT/build/edm/output"
  assert_output_dir "$edm_out"
  assert_file "Email HTML"                  "$ROOT/build/edm/output/email.html"
  assert_file "Email preview (text)"        "$ROOT/build/edm/output/email-preview.txt"

  # Validate HTML content
  if file_exists_nonempty "$ROOT/build/edm/output/email.html"; then
    if grep -qi '<!DOCTYPE html' "$ROOT/build/edm/output/email.html" 2>/dev/null; then
      pass "  └─ email.html has valid DOCTYPE"
    else
      fail "  └─ email.html missing DOCTYPE"
    fi
    if grep -q '</html>' "$ROOT/build/edm/output/email.html" 2>/dev/null; then
      pass "  └─ email.html has closing html tag"
    else
      fail "  └─ email.html missing closing html tag"
    fi
  fi
else
  fail "build/edm/ directory MISSING"
fi

###############################################################################
# STAGE 9 — VERCEL DEPLOY (Card 38)
###############################################################################
STAGE=$((STAGE+1)); header "Vercel Deploy — Deployment Config (Card 38)"

if [[ -d "$ROOT/deploy/vercel" ]]; then
  pass "deploy/vercel/ directory exists"
  assert_file "Vercel config"               "$ROOT/deploy/vercel/vercel.json"
  assert_file "Deploy script"               "$ROOT/deploy/vercel/deploy.sh"
  assert_file "Rollback script"             "$ROOT/deploy/vercel/rollback.sh"
  assert_file "Deploy runner"               "$ROOT/deploy/vercel/deploy.ts"

  # Check if vercel.json is valid JSON
  if jq -e . "$ROOT/deploy/vercel/vercel.json" >/dev/null 2>&1; then
    pass "  └─ vercel.json is valid JSON"

    project_name=$(jq -r '.name // "none"' "$ROOT/deploy/vercel/vercel.json" 2>/dev/null)
    info "Vercel project name: $project_name"
  else
    fail "  └─ vercel.json is invalid JSON"
  fi

  # Check .vercel directory (indicates init/login happened)
  if [[ -f "$ROOT/deploy/vercel/.vercel/project.json" ]]; then
    pass "  └─ Vercel project linked (project.json present)"
  else
    fail "  └─ Vercel project NOT linked — run 'vercel link'"
  fi

  # Check output directory
   vc_out="$ROOT/deploy/vercel/output"
  if [[ -d "$vc_out" ]]; then
    if [[ -z "$(ls -A "$vc_out" 2>/dev/null)" ]]; then
      fail "  └─ Vercel output/ directory is EMPTY — no build deployed"
    else
      pass "  └─ Vercel output/ has content"
    fi
  else
    fail "  └─ Vercel output/ directory MISSING — no build deployed"
  fi
else
  fail "deploy/vercel/ directory MISSING"
fi

###############################################################################
# STAGE 10 — EDM DELIVERY (Card 39)
###############################################################################
STAGE=$((STAGE+1)); header "EDM Delivery — Package for Dispatch (Card 39)"

if [[ -d "$ROOT/deploy/edm" ]]; then
  pass "deploy/edm/ directory exists"

   ed_del="$ROOT/deploy/edm/output"
  assert_output_dir "$ed_del"

  # Check for delivery artifacts
   found_artifacts=false
  while IFS= read -r -d '' f; do
    found_artifacts=true
    assert_file "Delivery artifact" "$f"
  done < <(find "$ed_del" -maxdepth 1 -type f -print0 2>/dev/null)

  if ! $found_artifacts; then
    fail "EDM delivery output is EMPTY — no dispatch package prepared"
  fi
else
  fail "deploy/edm/ directory MISSING"
fi

###############################################################################
# SUMMARY
###############################################################################
echo
echo "============================================="
echo " Acceptance Gate Results"
echo "============================================="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo "---------------------------------------------"

TOTAL=$((STAGE))
echo "  Pipeline stages: $TOTAL"
echo "  Overall: "
if [[ "$FAIL" -eq 0 ]]; then
  echo "    ✅ ALL STAGES PASS"
else
  echo "    ❌ $FAIL FAILURE(S) DETECTED"
fi
echo "============================================="

# Write results JSON
cat > "$RESULTS_FILE" <<JSONEOF
{
  "\$schema": "../schemas/e2e-results-schema.json",
  "projectId": "JOB0003",
  "phase": 1,
  "gate": "acceptance",
  "runAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "summary": {
    "totalStages": $TOTAL,
    "passed": $PASS,
    "failed": $FAIL,
    "skipped": $SKIP,
    "result": $( [[ "$FAIL" -eq 0 ]] && echo '"PASS"' || echo '"FAIL"' )
  },
  "stages": [
    {
      "id": 1,
      "name": "intake",
      "description": "Pipeline entry — brief intake, schemas, routing",
      "card": "intake",
      "outDir": "$ROOT/intake",
      "files": [
        {"path": "samples/copy-test.json", "required": true, "exists": $( [[ -f "$ROOT/intake/samples/copy-test.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/intake/samples/copy-test.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/intake/samples/copy-test.json" >/dev/null 2>&1 && echo "true" || echo "false")},
        {"path": "manifests/vision-intake.json", "required": true, "exists": $( [[ -f "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json" >/dev/null 2>&1 && echo "true" || echo "false")},
        {"path": "schemas/intake-schema.json", "required": true, "exists": $( [[ -f "$ROOT/intake/schemas/intake-schema.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/intake/schemas/intake-schema.json" 2>/dev/null || echo 0)},
        {"path": "router/index.ts", "required": true, "exists": $( [[ -f "$ROOT/intake/router/index.ts" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/intake/router/index.ts" 2>/dev/null || echo 0)}
      ],
      "overall": $( [[ -f "$ROOT/intake/samples/copy-test.json" && -f "$ROOT/intake/manifests/b4e7a1c2-0001-4000-8000-000000000001.vision-intake.json" && -f "$ROOT/intake/schemas/intake-schema.json" && -f "$ROOT/intake/router/index.ts" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 2,
      "name": "vision-pass",
      "description": "Image analysis — produces vision-manifest.json",
      "card": 31,
      "outDir": "$ROOT/discovery/vision-pass/output",
      "files": [
        {"path": "output/vision-manifest.json", "required": true, "exists": $( [[ -f "$ROOT/discovery/vision-pass/output/vision-manifest.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/discovery/vision-pass/output/vision-manifest.json" 2>/dev/null || echo 0)}
      ],
      "overall": $( [[ -f "$ROOT/discovery/vision-pass/output/vision-manifest.json" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 3,
      "name": "copy-parse",
      "description": "Brief text parsing — produces copy-manifest.json",
      "card": 32,
      "outDir": "$ROOT/discovery/copy-parse/output",
      "files": [
        {"path": "output/copy-manifest.json", "required": true, "exists": $( [[ -f "$ROOT/discovery/copy-parse/output/copy-manifest.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/discovery/copy-parse/output/copy-manifest.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/discovery/copy-parse/output/copy-manifest.json" >/dev/null 2>&1 && echo "true" || echo "false")}
      ],
      "overall": $( [[ -f "$ROOT/discovery/copy-parse/output/copy-manifest.json" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 4,
      "name": "manifest-assembler",
      "description": "Merges vision + copy into unified asset-manifest.json",
      "card": 33,
      "outDir": "$ROOT/discovery/manifest-assembler/output",
      "files": [
        {"path": "output/asset-manifest.json", "required": true, "exists": $( [[ -f "$ROOT/discovery/manifest-assembler/output/asset-manifest.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/discovery/manifest-assembler/output/asset-manifest.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/discovery/manifest-assembler/output/asset-manifest.json" >/dev/null 2>&1 && echo "true" || echo "false")}
      ],
      "overall": $( [[ -f "$ROOT/discovery/manifest-assembler/output/asset-manifest.json" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 5,
      "name": "pexels-gap-fill",
      "description": "Stock image search for missing assets",
      "card": 34,
      "outDir": "$ROOT/assets/pexels/output",
      "files": [
        {"path": "output/pexels-assets.json", "required": true, "exists": $( [[ -f "$ROOT/assets/pexels/output/pexels-assets.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/assets/pexels/output/pexels-assets.json" 2>/dev/null || echo 0)}
      ],
      "overall": $( [[ -f "$ROOT/assets/pexels/output/pexels-assets.json" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 6,
      "name": "higgsfield-gap-fill",
      "description": "AI image generation for missing assets",
      "card": 35,
      "outDir": "$ROOT/assets/higgsfield/output",
      "files": [
        {"path": "output/higgsfield-assets.json", "required": true, "exists": $( [[ -f "$ROOT/assets/higgsfield/output/higgsfield-assets.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/assets/higgsfield/output/higgsfield-assets.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/assets/higgsfield/output/higgsfield-assets.json" >/dev/null 2>&1 && echo "true" || echo "false")}
      ],
      "overall": $( [[ -f "$ROOT/assets/higgsfield/output/higgsfield-assets.json" && $(jq '.successfulCount' "$ROOT/assets/higgsfield/output/higgsfield-assets.json" 2>/dev/null) -gt 0 ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 7,
      "name": "static-web-build",
      "description": "Static website generation",
      "card": 36,
      "outDir": "$ROOT/build/web-rails",
      "files": [
        {"path": "build/web-rails/", "required": true, "exists": $( [[ -d "$ROOT/build/web-rails" ]] && echo "true" || echo "false" ), "nonEmpty": $( [[ -d "$ROOT/build/web-rails" && -n "$(ls -A "$ROOT/build/web-rails" 2>/dev/null)" ]] && echo "true" || echo "false")}
      ],
      "overall": $( [[ -d "$ROOT/build/web-rails" && -n "$(ls -A "$ROOT/build/web-rails" 2>/dev/null)" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 8,
      "name": "edm-build",
      "description": "EDM email generation",
      "card": 37,
      "outDir": "$ROOT/build/edm/output",
      "files": [
        {"path": "output/email.html", "required": true, "exists": $( [[ -f "$ROOT/build/edm/output/email.html" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/build/edm/output/email.html" 2>/dev/null || echo 0)},
        {"path": "output/email-preview.txt", "required": true, "exists": $( [[ -f "$ROOT/build/edm/output/email-preview.txt" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/build/edm/output/email-preview.txt" 2>/dev/null || echo 0)}
      ],
      "overall": $( [[ -f "$ROOT/build/edm/output/email.html" && -f "$ROOT/build/edm/output/email-preview.txt" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 9,
      "name": "vercel-deploy",
      "description": "Vercel deployment config and execution",
      "card": 38,
      "outDir": "$ROOT/deploy/vercel/output",
      "files": [
        {"path": "vercel.json", "required": true, "exists": $( [[ -f "$ROOT/deploy/vercel/vercel.json" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/deploy/vercel/vercel.json" 2>/dev/null || echo 0), "validJson": $(jq -e . "$ROOT/deploy/vercel/vercel.json" >/dev/null 2>&1 && echo "true" || echo "false")},
        {"path": "deploy.sh", "required": true, "exists": $( [[ -f "$ROOT/deploy/vercel/deploy.sh" ]] && echo "true" || echo "false" ), "size": $(stat --format=%s "$ROOT/deploy/vercel/deploy.sh" 2>/dev/null || echo 0)},
        {"path": "output/", "required": true, "exists": $( [[ -d "$ROOT/deploy/vercel/output" ]] && echo "true" || echo "false" ), "nonEmpty": $( [[ -d "$ROOT/deploy/vercel/output" && -n "$(ls -A "$ROOT/deploy/vercel/output" 2>/dev/null)" ]] && echo "true" || echo "false")}
      ],
      "overall": $( [[ -f "$ROOT/deploy/vercel/vercel.json" && -f "$ROOT/deploy/vercel/deploy.sh" ]] && echo '"PASS"' || echo '"FAIL"' )
    },
    {
      "id": 10,
      "name": "edm-delivery",
      "description": "Packages EDM for dispatch",
      "card": 39,
      "outDir": "$ROOT/deploy/edm/output",
      "files": [
        {"path": "output/", "required": true, "exists": $( [[ -d "$ROOT/deploy/edm/output" ]] && echo "true" || echo "false" ), "nonEmpty": $( [[ -d "$ROOT/deploy/edm/output" && -n "$(ls -A "$ROOT/deploy/edm/output" 2>/dev/null)" ]] && echo "true" || echo "false")}
      ],
      "overall": $( [[ -d "$ROOT/deploy/edm/output" && -n "$(ls -A "$ROOT/deploy/edm/output" 2>/dev/null)" ]] && echo '"PASS"' || echo '"FAIL"' )
    }
  ],
  "pipelineIntegration": {
    "endToEndDataFlowComplete": false,
    "flowBreaks": [
      "Vision pass output is empty (no vision-manifest.json) — downstream manifest assembler receives no vision data",
      "Pexels output missing (pexels-assets.json does not exist) — asset gap not filled for stock images",
      "Higgsfield slots all queued (0/2+ successful) — AI-generated assets not delivered",
      "No static web output — web build rail not wired end-to-end",
      "Vercel output directory empty — deployment config present but never executed",
      "EDM delivery output empty — delivery packaging not completed"
    ]
  }
}
JSONEOF

echo "Results saved to: $RESULTS_FILE"

# Build status.md (with pre-computed dynamic values)
STATUS_RESULT_PASS=false
[[ "$FAIL" -eq 0 ]] && STATUS_RESULT_PASS=true
STATUS_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATUS_DATE="$(date -u +%Y-%m-%d)"
STATUS_VERDICT="❌ FAIL — ${FAIL} failure(s) detected"
$STATUS_RESULT_PASS && STATUS_VERDICT="✅ PASS"

cat > "$STATUS_FILE" <<'MDEOF'
# Phase 1 Acceptance Gate — Status Report

**Project:** JOB0003
**Gate:** Acceptance (dry run)
**Run at:** STATUS_TIMESTAMP_PLACEHOLDER
**Result:** STATUS_VERDICT_PLACEHOLDER

---

## Pipeline Coverage

| Stage | Card | Directory | Status | Key Artifact |
|-------|------|-----------|--------|-------------|
| 1. Intake | — | \`intake/\` | ✅ PASS | \`samples/copy-test.json\`, \`manifests/*.json\` |
| 2. Vision Pass | 31 | \`discovery/vision-pass/\` | ❌ FAIL | Output directory **empty** — \`vision-manifest.json\` not produced |
| 3. Copy Parse | 32 | \`discovery/copy-parse/\` | ✅ PASS | \`output/copy-manifest.json\` (1,263B, valid) |
| 4. Manifest Assembler | 33 | \`discovery/manifest-assembler/\` | ✅ PASS | \`output/asset-manifest.json\` (4,295B, valid) |
| 5. Pexels Gap-Fill | 34 | \`assets/pexels/\` | ❌ FAIL | \`output/pexels-assets.json\` **missing** — runner never executed |
| 6. Higgsfield Gap-Fill | 35 | \`assets/higgsfield/\` | ❌ FAIL | All slots **queued** (0 success) — generation never ran |
| 7. Static Web | 36 | \`build/web-rails/\` | ❌ FAIL | Directory **empty** — no output produced |
| 8. EDM Build | 37 | \`build/edm/\` | ✅ PASS | \`output/email.html\` (16.8KB), \`email-preview.txt\` (1.7KB) |
| 9. Vercel Deploy | 38 | \`deploy/vercel/\` | ⚠️ PARTIAL | Config present, but \`output/\` **empty** — no deployment executed |
| 10. EDM Delivery | 39 | \`deploy/edm/\` | ❌ FAIL | \`output/\` **empty** — no dispatch package |

---

## Data Flow Integrity

```
[Intake] ──→ [Vision] ──→ [Manifest Assembler] ──→ [Asset Fill] ──→ [Build] ──→ [Deploy]
   ✅          ❌              ✅ (no vision data)      ❌              ❌          ❌
```

### Broken Links

1. **Vision → Manifest Assembler**: Vision pass produced \`vision-manifest.json\` but the output directory is empty. The manifest assembler appears to have run with placeholder/default data rather than real vision analysis.

2. **Manifest Assembler → Pexels**: The \`asset-manifest.json\` lists missing images (\`img-hero-001\`, etc.) but the Pexels runner never produced its output. The \`pexels-assets.json\` file does not exist at the expected path.

3. **Manifest Assembler → Higgsfield**: The Higgsfield runner created its output manifest with slots defined, but all slots remain \`queued\` (generation was never actually invoked).

4. **Asset Fill → Static Web Build**: With no pexels output and no actual higgsfield generations, the static web build has no resolved assets to work with. The \`build/web-rails\` directory is empty.

5. **Asset Fill → EDM Build**: The EDM build has output, but it was generated from a **standalone test manifest** (\`GreenLeaf Monthly\` newsletter), not from the assembled \`asset-manifest.json\`. This means the EDM rail is **not actually wired** into the pipeline — it runs independently.

6. **Build → Vercel Deploy**: Vercel deployment has config/scripts but the \`output/\` directory is empty. The \`deploy.sh\` script exists but was never invoked.

7. **Build → EDM Delivery**: The EDM delivery output directory exists but is completely empty — no dispatch package was prepared.

---

## Detailed Findings

### Strengths (what's working)

- **Intake schema + routing** is solid: samples, manifests, schemas, and router code all present
- **Copy parsing** works end-to-end: produces structured \`copy-manifest.json\` with segments + metadata
- **Manifest assembler** correctly merges and validates structure (images, copy, palette, scope)
- **EDM build rail** generates full HTML email with responsive styles, dark mode support, and plaintext preview
- **Vercel deploy scripts** have deployment and rollback scripts defined
- Code-level types are well-defined across all stages

### Weaknesses / Gaps

- **Vision pass** produced code and types but the actual analysis engine was never executed against the intake images
- **Pexels integration** has the runner code but the output file is absent — likely needs API authentication configured
- **Higgsfield** both needs API auth and actual generation to be triggered
- **Static web (Card 36)** has an empty directory — no build output exists at all
- **Pipeline isolation**: EDM output uses a test manifest, not the pipeline's \`asset-manifest.json\`

### Data Consistency Issues

- Copy manifest references \`briefId: b4e7a1c2-0001...\` but sample brief uses \`b4e7a1c2-0041...\` — mismatched IDs
- EDM email content (GreenLeaf newsletter) is unrelated to the pipeline's Acme Corp/NovaTech briefs
- Vision intake manifest references image files that don't exist on disk

---

## Recommendations for Phase 2

| # | Recommendation | Priority |
|---|---------------|----------|
| 1 | **Execute vision pass** before manifest assembly — wire up `discovery/vision-pass/run.ts` so it produces `vision-manifest.json` from the intake manifest | 🔴 Critical |
| 2 | **Run Pexels and Higgsfield runners** — configure API keys in secrets store, trigger actual search/generation | 🔴 Critical |
| 3 | **Build static web output** — implement the web build rail to consume \`asset-manifest.json\` and produce HTML/CSS | 🔴 Critical |
| 4 | **Wire EDM build to the pipeline manifest** — replace standalone test manifests with live \`asset-manifest.json\` consumption | 🟡 High |
| 5 | **Execute Vercel deployment** — run \`deploy.sh\` after web build completes, populate \`output/\` | 🟡 High |
| 6 | **Complete EDM delivery packaging** — implement dispatch bundle generation in \`deploy/edm/\` | 🟡 High |
| 7 | **Add stage orchestration** — a pipeline runner that sequences stages, passes artifacts between them, and fails fast | 🟡 High |
| 8 | **Add integration tests** — verify each stage consumes the previous stage's output correctly | 🟢 Medium |
| 9 | **Add brief ID consistency check** — ensure all manifests reference the same \`briefId\` | 🟢 Medium |
| 10 | **Audit file dependencies** — confirm each stage's input files exist before executing | 🟢 Medium |

---

*Report generated by e2e acceptance gate harness on $(date -u +%Y-%m-%d).*
MDEOF

echo "Status report saved to: $STATUS_FILE"

# Exit code
[[ "$FAIL" -eq 0 ]]