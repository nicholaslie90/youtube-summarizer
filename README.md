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

The app stays in the Dock while the server runs: quit it (⌘Q or Dock → Quit) to stop the server, click its icon to reopen the page. Logs: `app.log`.

## CLI

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
.venv/bin/python summarize.py "https://www.youtube.com/watch?v=VIDEO_ID"   # --no-summary for transcript only
```

Writes `out/<video_id>/transcript.md` and `summary.md`. Videos with no captions are rejected.
