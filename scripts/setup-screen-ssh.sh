#!/usr/bin/env bash
# Passwordless SSH from the PCCS Pi to remote touchscreens (screen wake/sleep).
# Run as the same user that runs pccs4.service (usually joel).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEY="$HOME/.ssh/pccs_screen"
SSH_CONFIG="$HOME/.ssh/config"

SCREEN_USER="${SCREEN_USER:-joel}"
SCREEN_HOST="${SCREEN_HOST:-10.10.10.10}"
SCREEN_ALIAS="${SCREEN_ALIAS:-kitchen-screen}"

usage() {
    echo "Usage: SCREEN_USER=joel SCREEN_HOST=10.10.10.10 $0" >&2
    echo "Copies ~/.ssh/pccs_screen.pub to the touchscreen (prompts for remote password once)." >&2
    exit 1
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [[ ! -f "$KEY" ]]; then
    ssh-keygen -t ed25519 -f "$KEY" -N "" -C "pccs-screen-control"
    echo "Created $KEY"
fi

if ! grep -q "Host ${SCREEN_HOST} " "$SSH_CONFIG" 2>/dev/null && \
   ! grep -q "Host ${SCREEN_ALIAS}" "$SSH_CONFIG" 2>/dev/null; then
    cat >> "$SSH_CONFIG" <<EOF

# Screen control — ${SCREEN_HOST} (see config/pccs.conf [screens])
Host ${SCREEN_HOST} ${SCREEN_ALIAS}
    HostName ${SCREEN_HOST}
    User ${SCREEN_USER}
    IdentityFile ~/.ssh/pccs_screen
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
    chmod 600 "$SSH_CONFIG"
    echo "Appended SSH config for ${SCREEN_USER}@${SCREEN_HOST}"
fi

echo "Installing public key on ${SCREEN_USER}@${SCREEN_HOST} (enter the touchscreen password when prompted)..."
ssh-copy-id -i "${KEY}.pub" "${SCREEN_USER}@${SCREEN_HOST}"

echo "Verifying passwordless login (same flags PCCS uses)..."
ssh -o BatchMode=yes -o PreferredAuthentications=publickey \
    -o UserKnownHostsFile="$HOME/.pccs/screen_known_hosts" \
    -o StrictHostKeyChecking=accept-new \
    "${SCREEN_USER}@${SCREEN_HOST}" 'echo ok'

echo "Testing screen control (D-Bus ScreenSaver — Armbian/KDE)..."
ssh -o BatchMode=yes -o PreferredAuthentications=publickey \
    -o UserKnownHostsFile="$HOME/.pccs/screen_known_hosts" \
    "${SCREEN_USER}@${SCREEN_HOST}" \
    'export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus; busctl --user call org.freedesktop.ScreenSaver /org/freedesktop/ScreenSaver org.freedesktop.ScreenSaver GetActive'

echo ""
echo "If brightness_path in pccs.conf uses sysfs (fb0/blank), also run:"
echo "  SCREEN_USER=${SCREEN_USER} SCREEN_HOST=${SCREEN_HOST} \"$REPO_ROOT/scripts/setup-screen-remote-perms.sh\""