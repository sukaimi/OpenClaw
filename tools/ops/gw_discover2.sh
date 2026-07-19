#!/bin/bash
echo "########## current USER unit contents ##########"
cat /root/.config/systemd/user/openclaw-gateway.service 2>/dev/null || echo "(missing)"
echo
echo "########## does it have Restart=always? ##########"
grep -E "Restart=|KillMode=|WantedBy=" /root/.config/systemd/user/openclaw-gateway.service 2>/dev/null
echo
echo "########## is lingering enabled for root? (needed for user svc to survive reboot/logout) ##########"
loginctl show-user root 2>/dev/null | grep -i linger || echo "(loginctl no data)"
echo
echo "########## install options (system vs user, force) ##########"
openclaw gateway install --help 2>&1 | head -30
