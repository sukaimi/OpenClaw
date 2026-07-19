#!/bin/bash
U=/root/.config/systemd/user/openclaw-gateway.service
echo "### backup current unit ###"
cp "$U" /root/.openclaw/openclaw-gateway.unit.bak-presort && echo "backed up to /root/.openclaw/openclaw-gateway.unit.bak-presort"
echo
echo "### capture whether old unit had GEMINI_API_KEY (for preservation) ###"
grep -q "GEMINI_API_KEY" "$U" && echo "OLD unit had GEMINI_API_KEY: yes" || echo "OLD unit GEMINI: no"
echo
echo "### run gateway install --force (regenerate clean unit) ###"
openclaw gateway install --force 2>&1 | tail -8
echo
echo "### NEW unit — key directives ###"
grep -E "Description=|Restart=|RestartSec=|KillMode=|WantedBy=|OPENCLAW_SERVICE_VERSION" "$U" 2>/dev/null
echo "--- secrets still embedded? (yes = still there) ---"
grep -q "OPENCLAW_GATEWAY_TOKEN" "$U" && echo "TOKEN embedded: STILL YES" || echo "TOKEN embedded: no (good)"
grep -q "GEMINI_API_KEY" "$U" && echo "GEMINI in new unit: yes" || echo "GEMINI in new unit: NO (will restore via drop-in if needed)"
