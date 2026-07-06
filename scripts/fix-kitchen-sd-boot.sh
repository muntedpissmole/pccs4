#!/usr/bin/env bash
# Repair Rock 5C kitchen SD after a failed apt upgrade broke boot symlinks.
set -euo pipefail

DEV="${KITCHEN_SD_DEV:-/dev/sdb1}"
MNT="${KITCHEN_SD_MNT:-/mnt/kitchen}"
KVER="${KITCHEN_KERNEL_VER:-6.18.35-current-rockchip64}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

if [[ ! -b "$DEV" ]]; then
    echo "Block device not found: $DEV" >&2
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT | grep -E 'NAME|sd|mmc' >&2
    exit 1
fi

mkdir -p "$MNT"
if mountpoint -q "$MNT"; then
    mount -o remount,rw "$MNT"
else
    mount "$DEV" "$MNT"
fi

for f in "vmlinuz-${KVER}" "initrd.img-${KVER}" "uInitrd-${KVER}"; do
    if [[ ! -f "$MNT/boot/$f" ]]; then
        echo "Missing boot file: /boot/$f" >&2
        exit 1
    fi
done

cd "$MNT/boot"
ln -sf "vmlinuz-${KVER}" vmlinuz
ln -sf "vmlinuz-${KVER}" Image
ln -sf "initrd.img-${KVER}" initrd.img
ln -sf "uInitrd-${KVER}" uInitrd
echo "Fixed boot symlinks to ${KVER}:"
ls -la vmlinuz Image initrd.img uInitrd dtb

# Kitchen uses onboard ethernet; don't let broken WiFi DKMS block kernel configure.
if [[ -d "$MNT/var/lib/dkms/aic8800-usb" ]]; then
    echo "Removing aic8800-usb DKMS (WiFi only; ethernet unaffected)..."
    rm -rf "$MNT/var/lib/dkms/aic8800-usb"
fi

mount --bind /dev  "$MNT/dev"
mount --bind /proc "$MNT/proc"
mount --bind /sys  "$MNT/sys"
mount --bind /run  "$MNT/run"

chroot "$MNT" bash -lc "
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
dpkg --configure -a || true
apt-mark hold linux-image-current-rockchip64 linux-headers-current-rockchip64 linux-dtb-current-rockchip64 linux-u-boot-rock-5c-current 2>/dev/null || true
"

umount "$MNT/run" "$MNT/sys" "$MNT/proc" "$MNT/dev"

echo
echo "SD repair complete. Safely eject, boot the Rock 5C, then verify:"
echo "  ip -4 addr show end0"
echo "  ssh joel@10.10.10.10"