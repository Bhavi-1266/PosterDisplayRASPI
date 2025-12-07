#!/usr/bin/env bash
set -euo pipefail

# --- Command paths (explicit for cron) ---
ECHO=/usr/bin/echo
PYTHON=/usr/bin/python3
SLEEP=/usr/bin/sleep

# Debug timestamp
$ECHO "[launcher] started at $(date)" >> /home/bhavy/eposter/launcher.log

# Short wait to let session/services settle
$SLEEP 6

# Ensure graphical env variables for pygame/SDL (important for cron)
export DISPLAY=:0
export XAUTHORITY="/home/bhavy/.Xauthority"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

$ECHO "[launcher] ENV: DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >> /home/bhavy/eposter/launcher.log

# Move to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$SCRIPT_DIR"
PY_SCRIPT="$BASE/show_eposters.py"
cd "$BASE" || {
    $ECHO "[launcher] ERROR: Cannot change to directory $BASE" >> /home/bhavy/eposter/launcher.log
    exit 1
}

# --- Settings (keep these or move to a separate .env if you prefer) ---
export WIFI_SSID="BHAVY"
export WIFI_PSK="Bms@1266"
export WIFI_SSID_2="BHAVY2"
export WIFI_PSK_2="Bms@1266"
export WIFI_CONNECT_TIMEOUT=60

export POSTER_TOKEN="A9993E364706816ABA3E25717850C26C9CD0D89D"
export CACHE_REFRESH=60
export DISPLAY_TIME=5

$ECHO "[launcher] Starting ePoster viewer…" >> /home/bhavy/eposter/launcher.log
$ECHO "  POSTER_TOKEN: [HIDDEN]" >> /home/bhavy/eposter/launcher.log
$ECHO "  CACHE_REFRESH=$CACHE_REFRESH" >> /home/bhavy/eposter/launcher.log
$ECHO "  DISPLAY_TIME=$DISPLAY_TIME" >> /home/bhavy/eposter/launcher.log
$ECHO "  WIFI_SSID: ${WIFI_SSID:+[SET]}" >> /home/bhavy/eposter/launcher.log
$ECHO "  WIFI_SSID_2: ${WIFI_SSID_2:+[SET]}" >> /home/bhavy/eposter/launcher.log

# Run the python script and append stdout/stderr to launcher.log
exec "$PYTHON" "$PY_SCRIPT" >> /home/bhavy/eposter/launcher.log 2>&1
