#!/bin/bash
# Start the local server if it isn't running, then open the page.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"  # apps launched from Finder get a bare PATH (no yt-dlp)
if ! curl -fs "$URL/health" >/dev/null; then
  [ -x "$DIR/.venv/bin/python" ] || { python3 -m venv "$DIR/.venv" && "$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"; }
  nohup "$DIR/.venv/bin/python" "$DIR/app.py" >"$DIR/app.log" 2>&1 &
  for _ in $(seq 50); do curl -fs "$URL/health" >/dev/null && break; sleep 0.1; done
fi
open "$URL"
