#!/bin/bash
# Always-on server + Cloudflare Tunnel as launchd agents, for remote use via the Access-protected Worker (worker/).
# Needs the tunnel token in ~/.cloudflared/nic-air.token (chmod 600).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
LA=~/Library/LaunchAgents
agent() {  # label, program args..., written as a KeepAlive agent
	local label=$1; shift
	{
		echo '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict>'
		echo "<key>Label</key><string>$label</string><key>RunAtLoad</key><true/><key>KeepAlive</key><true/>"
		echo "<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>"
		echo "<key>PUBLIC_ORIGIN</key><string>https://youtube-summarizer.nl9.workers.dev</string></dict>"
		echo "<key>StandardOutPath</key><string>$DIR/$label.log</string><key>StandardErrorPath</key><string>$DIR/$label.log</string>"
		echo "<key>ProgramArguments</key><array>"; for a in "$@"; do echo "<string>$a</string>"; done; echo "</array></dict></plist>"
	} > "$LA/$label.plist"
	launchctl bootout "gui/$UID/$label" 2>/dev/null || true
	launchctl bootstrap "gui/$UID" "$LA/$label.plist"
}
pkill -f "$DIR/app.py" || true  # replace a Dock-started server so the new one gets PUBLIC_ORIGIN
agent com.nic.youtube-summarizer "$DIR/.venv/bin/python" "$DIR/app.py"
agent com.nic.youtube-summarizer-tunnel /opt/homebrew/bin/cloudflared tunnel --no-autoupdate run --token-file "$HOME/.cloudflared/nic-air.token"
echo "Running. Remote: https://youtube-summarizer.nl9.workers.dev"
