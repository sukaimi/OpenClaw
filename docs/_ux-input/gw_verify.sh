#!/bin/bash
echo "### daemon-reload + restart under new unit ###"
systemctl --user daemon-reload 2>&1
openclaw gateway restart 2>&1 | tail -2
sleep 12
echo
echo "### running under systemd? active state + child cleanup ###"
systemctl --user is-active openclaw-gateway.service 2>&1
systemctl --user is-enabled openclaw-gateway.service 2>&1
echo "linger:"; loginctl show-user root 2>/dev/null | grep -i linger
echo
echo "### channels up? ###"
ss -ltnp 2>/dev/null | grep -q 3978 && echo "Teams :3978 OK" || echo "Teams :3978 DOWN"
echo
echo "### gateway status — should be NO more out-of-date / KillMode / embedded-token warnings ###"
openclaw gateway status 2>&1 | grep -iE "service:|issue|out of date|recommend|looks" | head -8
echo "(no 'issue' lines above = clean)"
