#!/usr/bin/env bash
set -euo pipefail

BASE="/home/eposter"
PY_SCRIPT="$BASE/show_eposters.py"

# --- Settings ---
# Wi-Fi (optional) - set these if you want the device to auto-join a network at boot.
# If you don't want auto Wi-Fi, leave WIFI_SSID empty or comment the lines.
export WIFI_SSID="YourWifiName"
export WIFI_PSK="YourWifiPassword"
export WIFI_CONNECT_TIMEOUT=60

# Poster settings
export POSTER_TOKEN="API_TOKEN"
export CACHE_REFRESH=60
export DISPLAY_TIME=5

echo "[launcher] Starting ePoster viewer…"
echo "  POSTER_TOKEN: [HIDDEN]"
echo "  CACHE_REFRESH=$CACHE_REFRESH"
echo "  DISPLAY_TIME=$DISPLAY_TIME"
echo "  WIFI_SSID: ${WIFI_SSID:+[SET]}"
exec python3 "$PY_SCRIPT"
