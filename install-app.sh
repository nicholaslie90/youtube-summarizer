#!/bin/bash
# Creates "/Applications/YouTube Summarizer.app", which runs launch.sh from this folder.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="/Applications/YouTube Summarizer.app"
rm -rf "$APP"
osacompile -o "$APP" -e "do shell script quoted form of \"$DIR/launch.sh\""
echo "Installed: $APP"
