#!/usr/bin/env bash
# LunkAgent installer — one-liner: curl | bash
set -euo pipefail

INSTALL_DIR="${LUNKAGENT_DIR:-$HOME/.local/share/lunkagent}"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/Jstowers1/lunkAgent.git"

echo "═══ LunkAgent Installer ═══"
echo ""

# 1. Dependencies
echo "→ Installing dependencies..."
if command -v pacman &>/dev/null; then
    sudo pacman -S --needed --noconfirm gtk3 python-gobject webkit2gtk-4.1
elif command -v apt &>/dev/null; then
    sudo apt install -y gir1.2-webkit2-4.1 gir1.2-gtk-3.0 python3-gi
else
    echo "⚠ Unknown package manager. Install manually: gtk3, python-gobject, webkit2gtk-4.1"
fi

# 2. Clone (or update existing)
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating existing install at $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull "$REPO_URL" main --ff-only
else
    echo "→ Cloning to $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# 3. Launcher wrapper in ~/.local/bin
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/lunkagent" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
exec python3 lunkagent.py "\$@"
EOF
chmod +x "$BIN_DIR/lunkagent"

# 4. .desktop entry
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"
cp "$INSTALL_DIR/dev.lunkman.LunkAgent.desktop" "$APP_DIR/dev.lunkman.LunkAgent.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo ""
echo "═══ Done! ═══"
echo "Launch from your app menu, or run: lunkagent"
