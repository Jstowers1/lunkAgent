#!/usr/bin/env bash
# LunkAgent launcher — native Hermes WebUI client.
# Usage: ./run.sh [URL] [--fullscreen] [--no-theme]
#   URL defaults to http://localhost:8787
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Check for required system packages.
if ! python3 -c "import gi; gi.require_version('WebKit', '6.0')" 2>/dev/null; then
    echo "ERROR: WebKit6 GTK bindings not found."
    echo "  CachyOS: sudo pacman -S webkit2gtk-6.0 gtk4 libadwaita python-gobject"
    echo "  Ubuntu:  sudo apt install gir1.6-webkit6-4.1 gir1.6-gtk-4.0 gir1.6-adw-1 python3-gi"
    exit 1
fi

if ! python3 -c "import gi; gi.require_version('Adw', '1')" 2>/dev/null; then
    echo "ERROR: libadwaita not found."
    echo "  CachyOS: sudo pacman -S libadwaita"
    echo "  Ubuntu:  sudo apt install gir1.6-adw-1"
    exit 1
fi

PYTHON="$(command -v python3)"

exec "$PYTHON" "$REPO_DIR/lunkagent.py" "$@"
