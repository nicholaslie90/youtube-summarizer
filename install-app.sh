#!/bin/bash
# Creates "/Applications/YouTube Summarizer.app": a stay-open applet that sits in the Dock
# while the server runs. Quitting the app stops the server; clicking its Dock icon reopens the page.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="/Applications/YouTube Summarizer.app"
rm -rf "$APP"
# ponytail: a force-quit or crash of the app orphans the server; launch.sh reuses it next time
osacompile -s -o "$APP" <<EOF
on run
	do shell script quoted form of "$DIR/launch.sh"
end run

on reopen
	do shell script "open http://127.0.0.1:8765"
end reopen

on quit
	do shell script "pkill -f " & quoted form of "$DIR/app.py" & " || true"
	continue quit
end quit
EOF
# App icon from icon.svg (needs: brew install librsvg)
SET="$(mktemp -d)/icon.iconset"; mkdir "$SET"
for n in 16 32 128 256 512; do
	rsvg-convert -w $n -h $n "$DIR/icon.svg" -o "$SET/icon_${n}x${n}.png"
	rsvg-convert -w $((n*2)) -h $((n*2)) "$DIR/icon.svg" -o "$SET/icon_${n}x${n}@2x.png"
done
iconutil -c icns "$SET" -o "$APP/Contents/Resources/applet.icns"
rm -rf "$(dirname "$SET")"
codesign --force --sign - "$APP" 2>/dev/null  # resources changed; re-seal the ad-hoc signature
touch "$APP"
echo "Installed: $APP"
