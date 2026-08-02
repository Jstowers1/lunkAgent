#!/usr/bin/env bash
#LunkAgent launcher for the native Hermes WebUI client
#Usage, run with flags fullscreen no-theme no-sound
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

#Dependency check runs inside lunkagent.py which auto detects the WebKit2 version
exec python3 "$REPO_DIR/lunkagent.py" "$@"
