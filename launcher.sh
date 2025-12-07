#!/usr/bin/env bash
set -euo pipefail

# Debug timestamp
echo "[launcher] Cron/Autostart started at $(date)" >> /home/bhavy/eposter/launcher.log

# Wait a bit for the desktop/session to initialise (adjust if needed)
sleep 6

# Ensure full absolute python path
PYTHON=/usr/bin/python3

# Ensure graphical env variables for pygame/SDL
export DISPLAY=:0
export XAUTHORITY="/home/bhavy/.Xauthority"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

echo "[launcher] ENV: DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >> /home/bhavy/eposter/launcher.log


# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$SCRIPT_DIR"
PY_SCRIPT="$BASE/show_eposters.py"

# --- Settings ---
export WIFI_SSID="BHAVY"
export WIFI_PSK="Bms@1266"
export WIFI_SSID_2="BHAVY2"
export WIFI_PSK_2="Bms@1266"
export WIFI_CONNECT_TIMEOUT=60

export POSTER_TOKEN="A9993E364706816ABA3E25717850C26C9CD0D89D"
export CACHE_REFRESH=60
export DISPLAY_TIME=5

$ECHO "[launcher] Starting ePoster viewer…"
$ECHO "  POSTER_TOKEN: [HIDDEN]"
$ECHO "  CACHE_REFRESH=$CACHE_REFRESH"
$ECHO "  DISPLAY_TIME=$DISPLAY_TIME"
$ECHO "  WIFI_SSID: ${WIFI_SSID:+[SET]}"
$ECHO "  WIFI_SSID_2: ${WIFI_SSID_2:+[SET]}"

# Change to the script directory
cd "$BASE" || {
    $ECHO "[launcher] ERROR: Cannot change to directory $BASE"
    exit 1
}

# --- RUN PYTHON SCRIPT ---
exec $PYTHON "$PY_SCRIPT"
