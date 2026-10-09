# youtube-summarizer

Paste a YouTube URL, get the full timestamped transcript and a detailed Claude summary.

## Mac app (local web page)

```bash
brew install yt-dlp librsvg   # librsvg renders the app icon from icon.svg
./install-app.sh        # creates /Applications/YouTube Summarizer.app
```

Open **YouTube Summarizer** from Applications. It starts a server on `127.0.0.1:8765` (local only) and opens the page.

**API key:** copy your Anthropic key (`sk-ant-…`) to the clipboard. The app saves it to the macOS Keychain
(service `youtube-summarizer`) and reuses it after that. Copying a new key replaces the saved one.

A Gemini API key copied the same way is saved too and used as a **fallback**: if Claude fails before writing
(bad key, out of credit, overloaded), `gemini-3.5-flash` writes the summary instead. The line under the title shows
which model wrote it (red when it's the fallback). CLI: set `GEMINI_API_KEY`.

Pick the summary language from the menu next to **Summarize** (20 languages). Switching language rewrites the summary
from the original transcript; if the app was restarted and the transcript is gone, it translates an existing summary instead.

The app stays in the Dock while the server runs: quit it (⌘Q or Dock → Quit) to stop the server, click its icon to reopen the page. Logs: `app.log`.

## Chrome extension

One click on the toolbar button opens the app next to your YouTube tab and summarizes it (the app must be running).
Install: `chrome://extensions` → Developer mode → **Load unpacked** → pick `extension/`. Pin it from the puzzle-piece menu.

## Remote access (Cloudflare Access)

`https://youtube-summarizer.nl9.workers.dev` is a Worker (`worker/`) behind Cloudflare Access (members of the personal
Cloudflare account only). It reaches this Mac through the "Nic Air" tunnel via a Workers VPC service to `127.0.0.1:8765`.

```bash
./install-remote.sh                        # launchd agents: always-on server + tunnel (token: ~/.cloudflared/nic-air.token)
(cd worker && npx wrangler deploy)         # after editing the Worker
```

With the agents installed, launchd restarts the server if the Dock app's Quit stops it. Logs: `com.nic.youtube-summarizer*.log`.
To stop: `launchctl bootout gui/$UID/com.nic.youtube-summarizer` (and `…-tunnel`).

## CLI

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
.venv/bin/python summarize.py "https://www.youtube.com/watch?v=VIDEO_ID"   # --no-summary for transcript only, -l id for Indonesian, etc.
```

Writes `out/<video_id>/transcript.md` and `summary.md`. Videos with no captions are rejected.
