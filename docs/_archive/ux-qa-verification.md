# UX QA Verification — "Stone & Line" Hub Persona

Date: 2026-06-02 | Method: 4 fresh cold sessions (new-user simulation) against agent `main` + 1 health call. Read-only.

## Results

| Check | Verdict | Evidence (quoted from actual reply) |
|---|---|---|
| no-emoji | PASS | No emoji in any of the 4 replies. Greeting: "Hello — I'm the Delivery Lead for Code & Canvas." |
| no-status-leak | PASS | No trailing `status: done` / `needs-decision` line on any reply. |
| no-snark | PASS | No score-keeping or operator-radio phrasing ("the line's clean", "you've done that 8 times") in any reply. |
| no-profile-demand-at-first-contact | PASS | First-contact "hi" reply asks nothing about Profile A/B; just "tell me what you'd like built, or ask 'what can you do?'". Build-start reply ("coffee shop") asks scoping questions, still no A/B label demand. |
| capabilities-scannable | PASS | "what can you do?" reply is structured: **What the team does** / **How it works** / **Out of scope** / "tell me what you'd like built and who it's for — I'll lay out the plan." |
| out-of-scope-polite | PASS | "Out of scope: Public marketing sites (WordPress, static, custom web builds). SharePoint-focused only." — and on the coffee-shop brief it flags scope politely then offers to build directly. |
| gibberish-handled-cleanly | PASS | "asdfgh" → "I'm sorry — I didn't catch that. If you'd like to give me a brief... Otherwise, feel free to ask 'what can you do?'" Calm, no snark. |
| Teams-3978-up | PASS | `ss -ltnp` matched port 3978 → `TEAMS_3978_UP`. |
| config-valid | PASS | `openclaw config validate` → `Config valid: ~/.openclaw/openclaw.json` |

## Failures / Flakiness
None. All 4 sessions returned content on first attempt — no `<EMPTY>`, no parse errors, no retries needed.

## Notes
- Persona presents as "Delivery Lead for Code & Canvas." Warm plain greeting confirmed, voice is calm throughout.
- Coffee-shop ("build start") reply now uses plain scoping questions and labels nothing "Profile A/B"; it does not relabel to Standard/Restricted in this turn either, but the regression being verified (no A/B demand at first contact) holds.

## Verdict
**PASS** — all 9 checks pass; no model flakiness observed.
