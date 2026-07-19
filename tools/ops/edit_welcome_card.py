#!/usr/bin/env python3
import sys, shutil
F = "/root/.openclaw/npm/projects/openclaw-msteams-d29647a7c0/node_modules/@openclaw/msteams/dist/src-D_rcW2Zm.js"
shutil.copy(F, F + ".bak-uxcard")
s = open(F).read()
reps = [
    ("Hi! I'm ${botName}.", "Code & Craft — Delivery Lead"),
    ("I can help you with questions, tasks, and more. Here are some things to try:",
     "I run SharePoint & software delivery for Code & Craft: give me a brief and I'll run a specialist team through to handoff, with your sign-off at each stage. New here? Tap a starting point below, or just tell me what you'd like built."),
    ('"Summarize my last meeting"', '"Start a project brief"'),
    ('"Help me draft an email"', '"How should I brief you?"'),
]
for a, b in reps:
    n = s.count(a)
    if n != 1:
        print("ABORT: expected 1 occurrence of:", repr(a[:40]), "got", n)
        sys.exit(2)
    s = s.replace(a, b)
open(F, "w").write(s)
print("replaced", len(reps), "strings OK; backup at", F + ".bak-uxcard")
