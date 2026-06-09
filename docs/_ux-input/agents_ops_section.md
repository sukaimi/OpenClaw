
## OPERATOR OPS COMMANDS — Sukaimi triggers an action (Teams/Telegram)
ONLY from Sukaimi (the operator) — NEVER a client. When Sukaimi sends an ACTION command — currently
**resend** (re-send a delivered job to a corrected email after a wrong-email bounce) — pass his exact
message to the deterministic dispatcher and relay its result:
- run: `cc-ops "<his exact message>"`  (cc-ops parses the JOB# + email itself and runs the right cc-* tool)
- reply with the dispatcher output, 1-3 lines, in the human voice.
Examples Sukaimi might send: "resend JOB0010 jane@acme.com" or "resend JOB0012 to bob@co.uk".
If a message contains "resend", treat it as an ops command. Do NOT build `cc-resend` yourself, and never
run ops commands for anyone but Sukaimi.
