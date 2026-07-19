#!/bin/bash
echo "########## 1. unit file at /etc/systemd/system ##########"
cat /etc/systemd/system/openclaw-gateway.service 2>/dev/null || echo "(no system unit file)"
echo
echo "########## 2. systemctl (system scope) ##########"
systemctl is-enabled openclaw-gateway.service 2>&1
systemctl is-active openclaw-gateway.service 2>&1
systemctl status openclaw-gateway.service --no-pager 2>&1 | head -6
echo
echo "########## 3. systemctl (user scope) ##########"
systemctl --user is-enabled openclaw-gateway.service 2>&1
ls -la /root/.config/systemd/user/ 2>/dev/null | grep -i openclaw || echo "(no user unit)"
echo
echo "########## 4. the running gateway proc + its parent ##########"
GP=$(pgrep -f "openclaw/dist/index.js gateway" | head -1)
echo "gateway pid: $GP"
if [ -n "$GP" ]; then
  PPID=$(ps -o ppid= -p "$GP" | tr -d ' ')
  echo "parent pid: $PPID  ($(ps -o comm= -p "$PPID" 2>/dev/null))"
  echo "(parent pid 1 = supervised by systemd/init; otherwise detached/orphan)"
fi
echo
echo "########## 5. openclaw gateway status ##########"
openclaw gateway status 2>&1 | head -12
echo
echo "########## 6. boot target wants it? ##########"
ls -la /etc/systemd/system/multi-user.target.wants/ 2>/dev/null | grep -i openclaw || echo "(NOT in multi-user.target.wants — would NOT auto-start on boot)"
