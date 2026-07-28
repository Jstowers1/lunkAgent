#!/usr/bin/env bash
# LunkAgent launcher — native Hermes WebUI client.
# Usage: ./run.sh [--fullscreen] [--no-theme] [--no-sound]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Dependency check is done inside lunkagent.py (auto-detects WebKit2 version).
exec python3 "$REPO_DIR/lunkagent.py" "$@"
