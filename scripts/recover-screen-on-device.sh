#!/usr/bin/env bash
# Run ON the touchscreen (local terminal or mounted rootfs) if a reboot fails
# after PCCS screen setup. Removes only the files our setup scripts add.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

removed=0
for f in /etc/sudoers.d/pccs-screen-blank /etc/sudoers.d/pccs-screen-shutdown; do
    if [[ -f "$f" ]]; then
        rm -f "$f"
        echo "Removed $f"
        removed=1
    fi
done

if [[ "$removed" -eq 1 ]]; then
    visudo -c
    echo "Sudoers validated — reboot again."
else
    echo "No PCCS screen sudoers files found."
fi