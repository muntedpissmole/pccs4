#!/usr/bin/env bash
# Inspect a Rock 5C kitchen Armbian SD card plugged into the PCCS Pi (usually /dev/sdb1).
set -euo pipefail

DEV="${KITCHEN_SD_DEV:-/dev/sdb1}"
MNT="${KITCHEN_SD_MNT:-/mnt/kitchen}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

if [[ ! -b "$DEV" ]]; then
    echo "Block device not found: $DEV" >&2
    echo "Current block devices:" >&2
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT | grep -E 'NAME|sd|mmc' >&2
    exit 1
fi

mkdir -p "$MNT"
if ! mountpoint -q "$MNT"; then
    mount -o ro "$DEV" "$MNT"
    umount_on_exit=1
else
    umount_on_exit=0
fi

cleanup() {
    if [[ "${umount_on_exit:-0}" -eq 1 ]] && mountpoint -q "$MNT"; then
        umount "$MNT"
    fi
}
trap cleanup EXIT

echo "========== SD CARD: $DEV mounted at $MNT =========="
echo

echo "========== HOST / RELEASE =========="
cat "$MNT/etc/hostname" 2>/dev/null || true
cat "$MNT/etc/armbian-release" 2>/dev/null || true
echo

echo "========== BOOT CONFIG =========="
for f in "$MNT/boot/armbianEnv.txt" "$MNT/boot/firmware/armbianEnv.txt"; do
    if [[ -f "$f" ]]; then
        echo "--- $f ---"
        cat "$f"
        echo
    fi
done
echo "--- kernels / initrd in /boot ---"
ls -lt "$MNT/boot"/vmlinuz* "$MNT/boot"/initrd* "$MNT/boot/firmware"/vmlinuz* 2>/dev/null | head -20 || true
echo

echo "========== APT HISTORY (last 80 lines) =========="
if [[ -f "$MNT/var/log/apt/history.log" ]]; then
    tail -80 "$MNT/var/log/apt/history.log"
else
    echo "(no apt history.log)"
fi
echo

echo "========== APT TERM LOG (last 60 lines) =========="
latest_term="$(ls -t "$MNT/var/log/apt"/term.log* 2>/dev/null | head -1 || true)"
if [[ -n "$latest_term" ]]; then
    echo "--- $latest_term ---"
    tail -60 "$latest_term"
else
    echo "(no apt term log)"
fi
echo

echo "========== DPKG LOG (errors/warnings, last 40) =========="
if [[ -f "$MNT/var/log/dpkg.log" ]]; then
    grep -iE 'error|warning|fail|half-config|abort' "$MNT/var/log/dpkg.log" | tail -40 || true
fi
echo

echo "========== PCCS SETUP FILES =========="
ls -la "$MNT/etc/sudoers.d"/pccs-screen-* 2>/dev/null || echo "(no pccs sudoers)"
if [[ -f "$MNT/home/joel/.ssh/authorized_keys" ]]; then
    echo "--- joel authorized_keys ---"
    cat "$MNT/home/joel/.ssh/authorized_keys"
fi
echo

echo "========== NETWORK CONFIG =========="
ls -la "$MNT/etc/NetworkManager/system-connections/" 2>/dev/null || true
ls -la "$MNT/etc/netplan/" 2>/dev/null || true
for f in "$MNT/etc/NetworkManager/system-connections/"*; do
    [[ -f "$f" ]] || continue
    echo "--- $(basename "$f") ---"
    grep -vE '^(uuid=|psk=|cert|key|password)' "$f" 2>/dev/null || true
done
echo

echo "========== LAST BOOT JOURNAL (if present) =========="
for j in "$MNT/var/log/journal" "$MNT/var/log/syslog"; do
    if [[ -e "$j" ]]; then
        echo "--- $j exists ---"
    fi
done
if [[ -d "$MNT/var/log/journal" ]] && command -v journalctl >/dev/null; then
    journalctl -D "$MNT/var/log/journal" -b -1 --no-pager -p err..alert 2>/dev/null | tail -50 || \
        journalctl -D "$MNT/var/log/journal" -b 0 --no-pager -p err..alert 2>/dev/null | tail -50 || \
        echo "(could not read journal)"
fi
if [[ -f "$MNT/var/log/syslog" ]]; then
    echo "--- syslog errors (tail) ---"
    grep -iE 'error|fail|panic|oops|end0|eth|network|systemd' "$MNT/var/log/syslog" | tail -40 || true
fi
echo

echo "========== HELD / RECENT KERNEL PACKAGES =========="
if [[ -f "$MNT/var/lib/dpkg/status" ]]; then
    grep -A3 '^Package: linux-image' "$MNT/var/lib/dpkg/status" | grep -E '^Package:|^Status:|^Version:' | head -30
fi
echo

echo "========== DISK SPACE =========="
df -h "$MNT" "$MNT/boot" "$MNT/boot/firmware" 2>/dev/null || df -h "$MNT"
echo

echo "========== DONE =========="