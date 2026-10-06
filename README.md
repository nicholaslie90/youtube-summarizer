# youtube-summarizer

Paste a YouTube URL, get the full timestamped transcript and a detailed Claude summary.

```bash
brew install yt-dlp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
.venv/bin/python summarize.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Writes `out/<video_id>/transcript.md` and `out/<video_id>/summary.md`. Use `--no-summary` for transcript only.
Videos with no captions (manual or auto-generated) are rejected.
