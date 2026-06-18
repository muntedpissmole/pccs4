#!/usr/bin/env bash
# Pull the latest demo branch and refresh the install. Resets config/pccs.conf if it
# was edited locally — machine-specific settings belong in config/pccs.local.conf.
#
#   cd ~/pccs-demo
#   chmod +x scripts/update-demo.sh
#   sudo ./scripts/update-demo.sh
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BRANCH="${BRANCH:-demo}"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (e.g. sudo ./scripts/update-demo.sh)" >&2
    exit 1
fi

if [[ ! -f "$INSTALL_DIR/app.py" ]]; then
    echo "app.py not found in $INSTALL_DIR — set INSTALL_DIR to the repo root" >&2
    exit 1
fi

if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
    REPO_USER="$SUDO_USER"
else
    REPO_USER="${SERVICE_USER:-root}"
fi

cd "$INSTALL_DIR"

if [[ ! -d .git ]]; then
    echo "Not a git repository: $INSTALL_DIR" >&2
    exit 1
fi

if ! sudo -u "$REPO_USER" git diff --quiet -- config/pccs.conf 2>/dev/null; then
    echo "==> Resetting config/pccs.conf to match the repo"
    echo "    Machine-specific settings live in config/pccs.local.conf (gitignored)."
    sudo -u "$REPO_USER" git checkout -- config/pccs.conf
fi

echo "==> Pulling origin/$BRANCH"
sudo -u "$REPO_USER" git pull origin "$BRANCH"

echo "==> Refreshing demo install"
exec "$INSTALL_DIR/scripts/install-demo.sh"