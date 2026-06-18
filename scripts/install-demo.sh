#!/usr/bin/env bash
# One-off installer: venv + systemd service for PCCS4 demo (Ubuntu Server).
#
# Run from the cloned demo repo (or set INSTALL_DIR):
#   cd ~/pccs-demo
#   chmod +x scripts/install-demo.sh
#   sudo ./scripts/install-demo.sh
#
# Re-running is safe: refreshes the venv, service unit, and firewall rule.
set -euo pipefail

SERVICE_NAME="pccs-demo"
APP_PORT="${APP_PORT:-5000}"
INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (e.g. sudo ./scripts/install-demo.sh)" >&2
    exit 1
fi

if [[ ! -f "$INSTALL_DIR/app.py" ]]; then
    echo "app.py not found in $INSTALL_DIR — set INSTALL_DIR to the repo root" >&2
    exit 1
fi

# User that owns the install tree (the user who invoked sudo, when available).
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
    SERVICE_USER="$SUDO_USER"
else
    SERVICE_USER="${SERVICE_USER:-root}"
fi
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"

open_firewall_port() {
    local port="$1"
    if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q 'Status: active'; then
        echo "==> Opening port $port/tcp in ufw"
        ufw allow "${port}/tcp" comment 'pccs-demo' >/dev/null
        return
    fi
    if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
        echo "==> Opening port $port/tcp in firewalld"
        firewall-cmd --permanent --add-port="${port}/tcp" >/dev/null
        firewall-cmd --reload >/dev/null
        return
    fi
    echo "==> No active host firewall detected — port $port should be reachable on the LAN"
}

echo "==> PCCS4 demo install"
echo "    Directory : $INSTALL_DIR"
echo "    Run as    : $SERVICE_USER:$SERVICE_GROUP"
echo "    Port      : $APP_PORT"

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-venv

echo "==> Python virtualenv + demo dependencies"
if [[ ! -d "$INSTALL_DIR/venv" ]]; then
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv"
fi
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements-demo.txt"

if [[ ! -f "$INSTALL_DIR/config/demo_playlist.json" ]] || [[ ! -d "$INSTALL_DIR/static/demo/music" ]]; then
    echo "==> Demo playlist / artwork missing — running setup-demo-playlist.py"
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/scripts/setup-demo-playlist.py"
fi

echo "==> Configuring app to listen on all interfaces (port $APP_PORT)"
CONF="$INSTALL_DIR/config/pccs.conf"
if grep -q '^host = ' "$CONF"; then
    sed -i 's/^host = .*/host = 0.0.0.0/' "$CONF"
else
    printf '\n# Set by install-demo.sh — listen on all interfaces.\nhost = 0.0.0.0\n' >> "$CONF"
fi
if grep -q '^port = ' "$CONF"; then
    sed -i "s/^port = .*/port = $APP_PORT/" "$CONF"
else
    printf 'port = %s\n' "$APP_PORT" >> "$CONF"
fi
if grep -q '^debug = ' "$CONF"; then
    sed -i 's/^debug = .*/debug = false/' "$CONF"
fi

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
chown "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/logs"

echo "==> Installing systemd unit: $SERVICE_NAME.service"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"
sed \
    -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" \
    -e "s|@SERVICE_USER@|$SERVICE_USER|g" \
    -e "s|@SERVICE_GROUP@|$SERVICE_GROUP|g" \
    "$INSTALL_DIR/config/systemd/pccs-demo.service" > "$UNIT_DST"
chmod 644 "$UNIT_DST"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

open_firewall_port "$APP_PORT"

echo ""
echo "PCCS4 demo installed."
echo "  Service : systemctl status $SERVICE_NAME"
echo "  Logs    : journalctl -u $SERVICE_NAME -f"
echo "  URL     : http://$(hostname -I | awk '{print $1}'):${APP_PORT}/"
echo ""
echo "To update app code: git pull origin demo, then sudo systemctl restart $SERVICE_NAME"