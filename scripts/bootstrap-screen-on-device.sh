#!/usr/bin/env bash
# Run ON the touchscreen (local terminal) after a fresh Armbian install.
# Bootstraps what scripts/setup-screen.sh does from the PCCS Pi when SSH
# password auth is disabled (default on Armbian).
#
# Rock 5C + KDE/Wayland: do not write /sys/class/graphics/fb0/blank during setup.
# On some images that legacy sysfs path can leave HDMI dark after reboot.
set -euo pipefail

SCREEN_USER="${SCREEN_USER:-joel}"
BLANK_PATH="${BLANK_PATH:-/sys/class/graphics/fb0/blank}"
PCCS_PUBKEY="${PCCS_PUBKEY:-ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKR4OJxCLQHh3LWxppjkUParx2CnmG4VXgf0qU4h6aqf pccs-screen-control}"
SKIP_BLANK="${SKIP_BLANK:-0}"
ENABLE_SHUTDOWN_SUDO="${ENABLE_SHUTDOWN_SUDO:-0}"

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    echo "Run as ${SCREEN_USER}, not root: su - ${SCREEN_USER} -c '$0'" >&2
    exit 1
fi

if [[ "$(whoami)" != "${SCREEN_USER}" ]]; then
    echo "Run as ${SCREEN_USER} (current: $(whoami))" >&2
    exit 1
fi

umask 077
mkdir -p "${HOME}/.ssh"
AUTH_KEYS="${HOME}/.ssh/authorized_keys"
touch "${AUTH_KEYS}"
chmod 600 "${AUTH_KEYS}"

if ! grep -qF "${PCCS_PUBKEY}" "${AUTH_KEYS}"; then
    echo "${PCCS_PUBKEY}" >> "${AUTH_KEYS}"
    echo "Installed PCCS SSH public key in ${AUTH_KEYS}"
else
    echo "PCCS SSH public key already present"
fi

install_blank_sudoers() {
    local blank_sudoers='/etc/sudoers.d/pccs-screen-blank'
    local blank_line="${SCREEN_USER} ALL=(root) NOPASSWD: /usr/bin/tee ${BLANK_PATH}"
    sudo install -d -m 755 /etc/sudoers.d
    printf '%s\n' "${blank_line}" | sudo tee "${blank_sudoers}" >/dev/null
    sudo chmod 440 "${blank_sudoers}"
    sudo visudo -cf "${blank_sudoers}"
    if ! sudo -n -l 2>/dev/null | grep -qF "/usr/bin/tee ${BLANK_PATH}"; then
        echo "Passwordless sudo for ${BLANK_PATH} not visible in sudo -l" >&2
        exit 1
    fi
    echo "Installed ${blank_sudoers}"
}

install_shutdown_sudoers() {
    local shutdown_sudoers='/etc/sudoers.d/pccs-screen-shutdown'
    local shutdown_line="${SCREEN_USER} ALL=(root) NOPASSWD: /sbin/shutdown -h now, /usr/sbin/shutdown -h now, /sbin/poweroff, /usr/sbin/poweroff"
    sudo install -d -m 755 /etc/sudoers.d
    printf '%s\n' "${shutdown_line}" | sudo tee "${shutdown_sudoers}" >/dev/null
    sudo chmod 440 "${shutdown_sudoers}"
    sudo visudo -cf "${shutdown_sudoers}"
    if ! sudo -n -l 2>/dev/null | grep -qF '/sbin/shutdown -h now'; then
        echo "Passwordless shutdown sudo not visible in sudo -l" >&2
        exit 1
    fi
    echo "Installed ${shutdown_sudoers}"
}

if [[ "${SKIP_BLANK}" != "1" ]]; then
    install_blank_sudoers
else
    echo "Skipped blank sudoers (SKIP_BLANK=1)"
fi

if [[ "${ENABLE_SHUTDOWN_SUDO}" == "1" ]]; then
    install_shutdown_sudoers
else
    echo "Skipped shutdown sudoers (set ENABLE_SHUTDOWN_SUDO=1 to enable)"
fi

sudo visudo -c

echo "Bootstrap complete — reboot once, confirm HDMI and network, then run ./scripts/setup-screen.sh on the PCCS Pi."