#!/usr/bin/env bash
# Set up a remote touchscreen for PCCS wake/sleep over SSH:
#   1. Passwordless SSH (dedicated pccs_screen key)
#   2. Passwordless sudo for framebuffer blanking (fb0/blank)
# Run as the same user that runs pccs4.service (usually joel).
set -euo pipefail

SCREEN_USER="${SCREEN_USER:-joel}"
SCREEN_HOST="${SCREEN_HOST:-10.10.10.10}"
SCREEN_ALIAS="${SCREEN_ALIAS:-kitchen-screen}"
BLANK_PATH="${BLANK_PATH:-/sys/class/graphics/fb0/blank}"

KEY="$HOME/.ssh/pccs_screen"
SSH_CONFIG="$HOME/.ssh/config"
KNOWN_HOSTS="$HOME/.pccs/screen_known_hosts"

SSH_BASE=(
    -o PreferredAuthentications=publickey
    -o UserKnownHostsFile="${KNOWN_HOSTS}"
    -o StrictHostKeyChecking=accept-new
)

SSH_BATCH=(
    "${SSH_BASE[@]}"
    -o BatchMode=yes
)

RUN_SSH=1
RUN_BLANK=1

usage() {
    cat <<EOF
Usage: SCREEN_USER=joel SCREEN_HOST=10.10.10.10 $0

Sets up passwordless SSH from the PCCS Pi to a remote touchscreen, then
installs passwordless sudo for framebuffer blanking so panels fully turn off
when the linked reed closes (backlight 0% alone often leaves a faint glow).

Options:
  --ssh-only     Only install SSH keys
  --blank-only   Only install blank sysfs permissions (SSH must already work)
  -h, --help     Show this help

Environment:
  SCREEN_USER    SSH user on the touchscreen (default: joel)
  SCREEN_HOST    Touchscreen IP/hostname (default: 10.10.10.10)
  SCREEN_ALIAS   SSH config Host alias (default: kitchen-screen)
  BLANK_PATH     Sysfs blank path (default: /sys/class/graphics/fb0/blank)
  SKIP_BLANK=1   Skip framebuffer blank sudo setup
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --ssh-only)
            RUN_BLANK=0
            ;;
        --blank-only)
            RUN_SSH=0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

if [[ "${SKIP_BLANK:-}" == "1" ]]; then
    RUN_BLANK=0
fi

setup_ssh() {
    mkdir -p "$HOME/.ssh" "$(dirname "$KNOWN_HOSTS")"
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
    ssh "${SSH_BATCH[@]}" "${SCREEN_USER}@${SCREEN_HOST}" 'echo ok'
}

setup_blank() {
    # Do not pipe a script on stdin — that prevents ssh -t from allocating a TTY for sudo.
    # Do not write fb0/blank here — on Rock 5C + KDE/Wayland that can leave HDMI dark after reboot.
    local remote_cmd
    remote_cmd=$(cat <<EOF
set -euo pipefail
BLANK_PATH='${BLANK_PATH}'
BLANK_SUDOERS='/etc/sudoers.d/pccs-screen-blank'
SHUTDOWN_SUDOERS='/etc/sudoers.d/pccs-screen-shutdown'
BLANK_LINE='${SCREEN_USER} ALL=(root) NOPASSWD: /usr/bin/tee ${BLANK_PATH}'
SHUTDOWN_LINE='${SCREEN_USER} ALL=(root) NOPASSWD: /sbin/shutdown -h now, /usr/sbin/shutdown -h now, /sbin/poweroff, /usr/sbin/poweroff'
install -d -m 755 /etc/sudoers.d
printf '%s\n' "\$BLANK_LINE" > "\$BLANK_SUDOERS"
chmod 440 "\$BLANK_SUDOERS"
visudo -cf "\$BLANK_SUDOERS"
printf '%s\n' "\$SHUTDOWN_LINE" > "\$SHUTDOWN_SUDOERS"
chmod 440 "\$SHUTDOWN_SUDOERS"
visudo -cf "\$SHUTDOWN_SUDOERS"
visudo -c
echo "Installed \$BLANK_SUDOERS and \$SHUTDOWN_SUDOERS"
sudo -n -l | grep -F "/usr/bin/tee \${BLANK_PATH}" >/dev/null
sudo -n -l | grep -F '/sbin/shutdown -h now' >/dev/null
echo "passwordless blank and shutdown sudo verified"
EOF
)

    echo "Installing passwordless tee for ${BLANK_PATH} on ${SCREEN_USER}@${SCREEN_HOST}..."
    echo "(enter the touchscreen sudo password when prompted)"
    ssh -t "${SSH_BASE[@]}" "${SCREEN_USER}@${SCREEN_HOST}" \
        "sudo bash -c $(printf '%q' "$remote_cmd")"

    echo "Verifying passwordless sudo from PCCS (no fb blank write during setup)..."
    ssh "${SSH_BATCH[@]}" "${SCREEN_USER}@${SCREEN_HOST}" \
        "sudo -n -l | grep -F '/usr/bin/tee ${BLANK_PATH}'"
}

if [[ "$RUN_SSH" -eq 1 ]]; then
    setup_ssh
fi

if [[ "$RUN_BLANK" -eq 1 ]]; then
    setup_blank
fi

echo ""
echo "Done — PCCS can control ${SCREEN_USER}@${SCREEN_HOST} over SSH."
if [[ "$RUN_BLANK" -eq 1 ]]; then
    echo "Framebuffer blanking enabled via ${BLANK_PATH}."
    echo "Passwordless remote shutdown/poweroff enabled for ${SCREEN_USER}."
fi