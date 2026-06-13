#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RULE_SRC="$REPO_ROOT/config/polkit/50-pccs-networkmanager.rules"
RULE_DEST="/etc/polkit-1/rules.d/50-pccs-networkmanager.rules"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run with sudo: sudo $0" >&2
    exit 1
fi

if [[ ! -f "$RULE_SRC" ]]; then
    echo "Missing polkit rule: $RULE_SRC" >&2
    exit 1
fi

install -m 644 "$RULE_SRC" "$RULE_DEST"
echo "Installed $RULE_DEST"
echo "PCCS service users in the netdev group can now run live Wi-Fi scans and connections."