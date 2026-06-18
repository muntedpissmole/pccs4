#!/usr/bin/env bash
# Run PCCS4 in self-contained demo mode (Ubuntu server).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
    echo "Creating virtualenv..."
    python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

pip install -q -r requirements-demo.txt

echo "Starting PCCS4 demo on http://0.0.0.0:5000"
exec python app.py