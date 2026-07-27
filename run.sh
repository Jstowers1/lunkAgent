#!/usr/bin/env bash
# LunkAgent launcher — native Hermes WebUI client.
# Usage: ./run.sh [URL] [--fullscreen] [--no-theme]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if ! python3 -c "import gi; gi.require_version('WebKit2', '4.1')" 2>/dev/null; then
    echo "ERROR: WebKit2 GTK bindings not found."
    echo "  CachyOS: sudo pacman -S webkit2gtk-4.1 gtk3 python-gobject"
    echo "  Ubuntu:  sudo apt install gir1.2-webkit2-4.1 gir1.2-gtk-3.0 python3-gi"
    exit 1
fi

exec python3 "$REPO_DIR/lunkagent.py" "$@"
