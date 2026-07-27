#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# Transcript: WebKit by default (local page, ZapZap-style).
#   CHICKENBUTT_TRANSCRIPT=native ./run.sh   # old GTK bubble renderer
exec python3 main.py "$@"
