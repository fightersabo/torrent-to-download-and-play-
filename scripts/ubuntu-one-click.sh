#!/usr/bin/env bash
set -euo pipefail

# This script installs Transmission, prepares Python deps, and starts the web UI.
# Defaults can be overridden by exporting the env vars before running.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOWNLOAD_DIR="${TRANSMISSION_DOWNLOAD_DIR:-/var/lib/transmission-daemon/downloads}"
TRANS_USER="${TRANSMISSION_USERNAME:-admin}"
TRANS_PASS="${TRANSMISSION_PASSWORD:-changeme}"
SECRET_KEY="${APP_SECRET_KEY:-}"

printf "\n[1/5] Installing system dependencies (Transmission, Python)...\n"
sudo apt update
sudo apt install -y transmission-daemon python3-venv python3-pip jq

printf "\n[2/5] Configuring Transmission RPC...\n"
sudo systemctl stop transmission-daemon
CONFIG_PATH="/etc/transmission-daemon/settings.json"
sudo jq \
  --arg user "$TRANS_USER" \
  --arg pass "$TRANS_PASS" \
  --arg dir "$DOWNLOAD_DIR" \
  '."rpc-enabled"=true
   | ."rpc-bind-address"="0.0.0.0"
   | ."rpc-port"=9091
   | ."rpc-authentication-required"=true
   | ."rpc-username"=$user
   | ."rpc-password"=$pass
   | ."rpc-whitelist-enabled"=false
   | ."download-dir"=$dir' \
  "$CONFIG_PATH" | sudo tee "$CONFIG_PATH" >/dev/null

sudo mkdir -p "$DOWNLOAD_DIR"
sudo chown debian-transmission:debian-transmission "$DOWNLOAD_DIR"
sudo chmod 775 "$DOWNLOAD_DIR"

sudo systemctl start transmission-daemon
sleep 2
sudo systemctl status --no-pager transmission-daemon || true

printf "\n[3/5] Creating Python virtual environment and installing deps...\n"
cd "$ROOT_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

printf "\n[4/5] Preparing environment variables for the web app...\n"
if [ -z "$SECRET_KEY" ]; then
  SECRET_KEY=$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
  )
fi
cat > .env.local <<EOF_ENV
TRANSMISSION_HOST=${TRANSMISSION_HOST:-localhost}
TRANSMISSION_PORT=${TRANSMISSION_PORT:-9091}
TRANSMISSION_USERNAME=$TRANS_USER
TRANSMISSION_PASSWORD=$TRANS_PASS
TRANSMISSION_DOWNLOAD_DIR=$DOWNLOAD_DIR
APP_SECRET_KEY=$SECRET_KEY
EOF_ENV

printf "\n[5/5] Launching the Flask app...\n"
export $(grep -v '^#' .env.local | xargs)
python app.py
