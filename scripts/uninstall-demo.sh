#!/usr/bin/env bash
# Remove everything installed by scripts/install-demo.sh.
#
# Run from the demo repo (or set INSTALL_DIR):
#   cd ~/pccs-demo
#   chmod +x scripts/uninstall-demo.sh
#   sudo ./scripts/uninstall-demo.sh
#
# Stops the service, removes the systemd unit, venv, logs, and firewall rule.
# Does not delete the repo or uninstall system packages (python3-venv, etc.).
set -euo pipefail

SERVICE_NAME="pccs-demo"
APP_PORT="${APP_PORT:-5000}"
INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (e.g. sudo ./scripts/uninstall-demo.sh)" >&2
    exit 1
fi

close_firewall_port() {
    local port="$1"
    if command -v ufw >/dev/null 2>&1; then
        echo "==> Removing ufw rule for port $port/tcp (if present)"
        ufw delete allow "${port}/tcp" >/dev/null 2>&1 || true
    fi
    if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
        echo "==> Removing firewalld rule for port $port/tcp (if present)"
        firewall-cmd --permanent --remove-port="${port}/tcp" >/dev/null 2>&1 || true
        firewall-cmd --reload >/dev/null 2>&1 || true
    fi
}

echo "==> PCCS4 demo uninstall"
echo "    Directory : $INSTALL_DIR"

if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "==> Stopping $SERVICE_NAME"
    systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "==> Disabling $SERVICE_NAME"
    systemctl disable "$SERVICE_NAME"
fi

UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"
if [[ -f "$UNIT_DST" ]]; then
    echo "==> Removing systemd unit"
    rm -f "$UNIT_DST"
    systemctl daemon-reload
    systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true
fi

close_firewall_port "$APP_PORT"

if [[ -d "$INSTALL_DIR/venv" ]]; then
    echo "==> Removing Python virtualenv"
    rm -rf "$INSTALL_DIR/venv"
fi

if [[ -d "$INSTALL_DIR/logs" ]]; then
    echo "==> Removing logs directory"
    rm -rf "$INSTALL_DIR/logs"
fi

if [[ -f "$INSTALL_DIR/config/pccs.local.conf" ]]; then
    echo "==> Removing config/pccs.local.conf"
    rm -f "$INSTALL_DIR/config/pccs.local.conf"
fi

echo ""
echo "PCCS4 demo uninstalled."
echo "  Repo at $INSTALL_DIR was kept — delete the directory manually if you no longer need it."