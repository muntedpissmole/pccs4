#!/usr/bin/env bash
# Run on the Rock 5C kitchen panel with sudo after PCCS screen setup.
set -euo pipefail

SCREEN_USER="${SCREEN_USER:-joel}"
MAINT_SUDOERS='/etc/sudoers.d/pccs-screen-maint'
DKMS_NO_AUTO='/etc/dkms/no-autoinstall.conf'
AIC8800_DKMS='aic8800-usb/5.0+git20260123.5f7be68d-5'

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

install_maint_sudoers() {
    local maint_line="${SCREEN_USER} ALL=(root) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get, /usr/bin/apt-mark, /usr/sbin/apt-cache, /usr/sbin/dpkg, /usr/sbin/dkms, /usr/sbin/update-initramfs, /usr/bin/deb-systemd-helper, /usr/sbin/depmod"
    install -d -m 755 /etc/sudoers.d
    printf '%s\n' "${maint_line}" > "${MAINT_SUDOERS}"
    chmod 440 "${MAINT_SUDOERS}"
    visudo -cf "${MAINT_SUDOERS}"
    visudo -c
    echo "Installed ${MAINT_SUDOERS}"
}

block_wifi_dkms_autoinstall() {
    install -d -m 755 /etc/dkms
    touch "${DKMS_NO_AUTO}"
    chmod 644 "${DKMS_NO_AUTO}"
    if ! grep -qxF "${AIC8800_DKMS}" "${DKMS_NO_AUTO}" 2>/dev/null; then
        echo "${AIC8800_DKMS}" >> "${DKMS_NO_AUTO}"
        echo "Blocked WiFi DKMS autoinstall in ${DKMS_NO_AUTO}"
    else
        echo "WiFi DKMS already blocked in ${DKMS_NO_AUTO}"
    fi
}

unhold_kernel_packages() {
    apt-mark unhold \
        linux-image-current-rockchip64 \
        linux-headers-current-rockchip64 \
        linux-dtb-current-rockchip64 \
        linux-u-boot-rock-5c-current 2>/dev/null || true
    echo "Kernel/u-boot holds cleared"
}

repair_package_state() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get -f install -y
    dpkg --configure -a
}

install_maint_sudoers
block_wifi_dkms_autoinstall
unhold_kernel_packages
repair_package_state

echo
echo "Kitchen panel is ready for apt upgrade."
echo "WiFi DKMS autoinstall is disabled (ethernet end0 is used for PCCS)."
echo "From this host or the PCCS Pi you can now run:"
echo "  sudo apt update && sudo apt full-upgrade -y"
echo
apt-mark showhold || true
dpkg -l | grep -E '^hi|^iF|^iU' || true