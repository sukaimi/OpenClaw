#!/usr/bin/env python3
"""cc-ops <operator message...> — deterministic operator-command dispatcher for the bot (BL-004).

The bot passes the operator's raw chat message here; this parses it and runs the matching cc-* tool,
returning a short reply the bot relays. Tolerant parsing (extracts JOB# + email from anywhere in the
message, so "resend JOB0010 to jane@acme.com" works). AUTH is enforced by the bot/agent (operator-only)
— cc-ops itself just executes, so the agent MUST only call it for the allowlisted operator.

Commands:
  resend <JOB####> <email>   re-send a delivered job (live URL + source) to a corrected address
  status [JOB####]           board summary
  help
"""
import sys, re, subprocess

JOB = re.compile(r"(JOB\d{4,})", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return "error running %s: %s" % (cmd[0], str(e)[:120])


def main():
    msg = " ".join(sys.argv[1:]).strip()
    low = msg.lower()

    if "resend" in low:
        j, e = JOB.search(msg), EMAIL.search(msg)
        if not (j and e):
            print("Usage: resend <JOB####> <email>  —  e.g. resend JOB0010 jane@acme.com"); return
        job, email = j.group(1).upper(), e.group(0)
        out = run(["cc-resend", job, email] + (["--dry"] if "--dry" in low else []))
        print(out or ("Re-sent %s to %s." % (job, email)))
        return

    if low.startswith("status"):
        j = JOB.search(msg)
        out = run(["cc-board", "read"] + ([j.group(1).upper()] if j else []))
        print(out or "(no board output)")
        return

    if low in ("help", "?", "/help", "commands", "ops"):
        print("Operator commands:\n"
              "  resend <JOB####> <email> — re-send a delivered job to a corrected address\n"
              "  status [JOB####] — board summary\n"
              "  help")
        return

    print("Unknown command. Try:  resend <JOB####> <email>  |  status  |  help")


if __name__ == "__main__":
    main()
