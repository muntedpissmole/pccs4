#!/usr/bin/env bash
# Allow PCCS (via SSH) to write fb0/blank on a remote touchscreen without a password.
# Run from the PCCS Pi after setup-screen-ssh.sh. Prompts for the touchscreen sudo password once.
set -euo pipefail

SCREEN_USER="${SCREEN_USER:-joel}"
SCREEN_HOST="${SCREEN_HOST:-10.10.10.10}"
BLANK_PATH="${BLANK_PATH:-/sys/class/graphics/fb0/blank}"

SSH_BASE=(
    -o PreferredAuthentications=publickey
    -o UserKnownHostsFile="${HOME}/.pccs/screen_known_hosts"
    -o StrictHostKeyChecking=accept-new
)

SSH_BATCH=(
    "${SSH_BASE[@]}"
    -o BatchMode=yes
)

usage() {
    echo "Usage: SCREEN_USER=joel SCREEN_HOST=10.10.10.10 $0" >&2
    exit 1
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

# Do not pipe a script on stdin — that prevents ssh -t from allocating a TTY for sudo.
REMOTE_CMD=$(cat <<EOF
set -euo pipefail
BLANK_PATH='${BLANK_PATH}'
SUDOERS_FILE='/etc/sudoers.d/pccs-screen-blank'
LINE='${SCREEN_USER} ALL=(root) NOPASSWD: /usr/bin/tee ${BLANK_PATH}'
install -d -m 755 /etc/sudoers.d
printf '%s\n' "\$LINE" > "\$SUDOERS_FILE"
chmod 440 "\$SUDOERS_FILE"
visudo -cf "\$SUDOERS_FILE"
echo "Installed \$SUDOERS_FILE"
echo 0 | sudo -n tee "\$BLANK_PATH" >/dev/null
echo "blank=\$(cat "\$BLANK_PATH")"
EOF
)

echo "Installing passwordless tee for ${BLANK_PATH} on ${SCREEN_USER}@${SCREEN_HOST}..."
echo "(enter the touchscreen sudo password when prompted)"
ssh -t "${SSH_BASE[@]}" "${SCREEN_USER}@${SCREEN_HOST}" "sudo bash -c $(printf '%q' "$REMOTE_CMD")"

echo "Verifying wake command from PCCS (no password)..."
ssh "${SSH_BATCH[@]}" "${SCREEN_USER}@${SCREEN_HOST}" \
    "echo 0 | sudo -n tee ${BLANK_PATH} >/dev/null && cat ${BLANK_PATH}"

echo "Done — PCCS can now wake/sleep this screen over SSH."