#!/usr/bin/env python3
"""Local web UI for summarize.py. Listens on 127.0.0.1:8765 only."""
import json
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import summarize

PORT = 8765
ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
KEY_RE = re.compile(r"^sk-ant-[A-Za-z0-9_-]{20,}$")
KEYCHAIN = ["-s", "youtube-summarizer", "-a", "anthropic"]
PAGE = Path(__file__).with_name("index.html")
FAVICON = Path(__file__).with_name("favicon.svg")
videos = {}  # ponytail: unbounded in-memory cache, fine for a personal app; restart clears it


def api_key():
    """Key on the clipboard wins (and is saved to Keychain); otherwise use the saved one."""
    clip = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    if KEY_RE.match(clip):
        # ponytail: -w puts the key on argv for a moment (visible to local `ps`); fine on a single-user Mac
        subprocess.run(["security", "add-generic-password", "-U", *KEYCHAIN, "-w", clip], capture_output=True)
        return clip, "clipboard"
    r = subprocess.run(["security", "find-generic-password", *KEYCHAIN, "-w"], capture_output=True, text=True)
    return (r.stdout.strip(), "keychain") if r.returncode == 0 else (None, None)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def trusted(self):
        # Host check blocks DNS rebinding; Origin check blocks other websites POSTing here (CSRF)
        host_ok = self.headers.get("Host") in {o.split("//")[1] for o in ORIGINS}
        return host_ok and (self.command == "GET" or self.headers.get("Origin") in ORIGINS)

    def do_GET(self):
        if not self.trusted():
            return self.send(403, {"error": "forbidden"})
        if self.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/favicon.svg":
            self.send(200, FAVICON.read_bytes(), "image/svg+xml")
        elif self.path == "/health":
            self.send(200, b"ok", "text/plain")
        elif self.path == "/api/languages":
            self.send(200, summarize.LANGUAGES)
        elif self.path == "/api/key":
            self.send(200, {"source": api_key()[1]})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.trusted() or self.headers.get("Content-Type") != "application/json":
            return self.send(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 500_000)))
        except ValueError:
            return self.send(400, {"error": "bad request"})
        if self.path == "/api/transcript":
            self.transcript(str(body.get("url", "")).strip())
        elif self.path == "/api/summary":
            self.summary(str(body.get("id", "")), str(body.get("lang", "en")))
        elif self.path == "/api/translate":
            self.translate(str(body.get("markdown", "")), str(body.get("lang", "")))
        else:
            self.send(404, {"error": "not found"})

    def transcript(self, url):
        if not re.match(r"^https?://", url):
            return self.send(400, {"error": "Paste a full video URL (https://…)."})
        try:
            info, lang, is_auto, paragraphs = summarize.fetch(url)
        except summarize.Error as e:
            return self.send(422, {"error": str(e)})
        vid = info.get("id") or ""
        videos[vid] = (info, summarize.header(info, lang, is_auto), summarize.format_transcript(paragraphs))
        self.send(200, {
            "id": vid, "title": info.get("title"), "url": info.get("webpage_url"),
            "channel": info.get("channel") or info.get("uploader"),
            "duration": summarize.ts(info.get("duration") or 0),
            "captions": lang + (" (auto-generated)" if is_auto else ""),
            "thumbnail": info.get("thumbnail"),
            "header": videos[vid][1], "markdown": videos[vid][1] + videos[vid][2],
        })

    def summary(self, vid, lang):
        if lang not in summarize.LANGUAGES:
            return self.send(400, {"error": "Unknown language."})
        if vid not in videos:  # e.g. app restarted; the page falls back to /api/translate
            return self.send(404, {"error": "Transcript is no longer loaded. Summarize the video again."})
        info, _, transcript = videos[vid]
        self.stream(lambda key: summarize.stream_summary(info, transcript, key, summarize.LANGUAGES[lang]))

    def translate(self, markdown, lang):
        if lang not in summarize.LANGUAGES or not markdown.strip():
            return self.send(400, {"error": "Nothing to translate."})
        self.stream(lambda key: summarize.stream_translation(markdown, key, summarize.LANGUAGES[lang]))

    def stream(self, make):
        key, _ = api_key()
        if not key:
            return self.send(401, {"error": "No API key. Copy your Anthropic API key (sk-ant-…) to the clipboard, then try again."})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()  # no Content-Length: body streams until the connection closes
        try:
            for chunk in make(key):
                self.wfile.write(chunk.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # tab closed or language switched mid-stream; closing the generator stops the API call
        except Exception as e:  # API errors (bad key, rate limit…) surface in the page
            self.wfile.write(f"\n\n**Error:** {getattr(e, 'message', None) or e}".encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
