#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONF_SRC="$REPO_ROOT/config/dnsmasq/50-pccs-screens.conf"
DROPIN_DEST="/etc/dnsmasq.d/50-pccs-screens.conf"
MAIN_CONF="/etc/dnsmasq.conf"
LEASE_FILE="/var/lib/misc/dnsmasq.leases"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run with sudo: sudo $0" >&2
    exit 1
fi

if [[ ! -f "$CONF_SRC" ]]; then
    echo "Missing dnsmasq config: $CONF_SRC" >&2
    exit 1
fi

install -m 644 "$CONF_SRC" "$DROPIN_DEST"
echo "Installed $DROPIN_DEST"

# Reservations live in dnsmasq.d only — remove duplicates from the main conf.
if [[ -f "$MAIN_CONF" ]]; then
    while IFS= read -r line; do
        [[ "$line" =~ ^dhcp-host=([0-9a-f:]+), ]] || continue
        mac="${BASH_REMATCH[1],,}"
        if grep -qi "$mac" "$MAIN_CONF"; then
            sed -i "/${mac}/Id" "$MAIN_CONF"
            echo "Removed duplicate dhcp-host for $mac from $MAIN_CONF"
        fi
    done < <(grep '^dhcp-host=' "$CONF_SRC" || true)
fi

# Drop stale dynamic leases so reserved MACs pick up their fixed IP immediately.
if [[ -f "$LEASE_FILE" ]]; then
    while IFS= read -r line; do
        [[ "$line" =~ ^dhcp-host=([0-9a-f:]+), ]] || continue
        mac="${BASH_REMATCH[1],,}"
        if grep -qi "$mac" "$LEASE_FILE"; then
            sed -i "/${mac}/Id" "$LEASE_FILE"
            echo "Cleared old lease for $mac"
        fi
    done < <(grep '^dhcp-host=' "$CONF_SRC" || true)
fi

if command -v dnsmasq >/dev/null 2>&1; then
    /usr/share/dnsmasq/systemd-helper checkconfig
    systemctl restart dnsmasq
    echo "dnsmasq restarted — renew DHCP on each touchscreen (reboot or replug Ethernet)"
else
    echo "dnsmasq not found — install it first (see INSTALL.md)"
fi