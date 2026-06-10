#!/usr/bin/env python3
import re
p = '/root/.openclaw/workspace-delivery-lead/AGENTS.md'
s = open(p, encoding='utf-8').read()
s2 = re.sub(
    r'then run\s+`cc-board next-tick` to self-continue\..*?hand-schedule cron\.',
    'then STOP. The supervisor (systemd `cc-dispatch`) owns continuation — it runs the next turn '
    'automatically and self-heals; never schedule cron yourself.',
    s, flags=re.S)
if s2 != s:
    open(p, 'w', encoding='utf-8').write(s2)
    print('AGENTS.md DISPATCH section updated (regex)')
else:
    print('still no match — check manually')
