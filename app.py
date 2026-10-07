#!/usr/bin/env python3
"""Local web UI for summarize.py. Listens on 127.0.0.1:8765 only."""
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import summarize

PORT = 8765
ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
# Remote access via the Cloudflare Access-protected Worker (worker/); unset = local only
if os.environ.get("PUBLIC_ORIGIN"):
    ORIGINS.add(os.environ["PUBLIC_ORIGIN"])
# Keychain account -> key pattern. Claude is primary; Gemini is the fallback (summarize.stream_llm).
KEY_RES = {"anthropic": re.compile(r"^sk-ant-[A-Za-z0-9_-]{20,}$"),
           "gemini": re.compile(r"^(AIza[A-Za-z0-9_-]{35}|AQ\.[A-Za-z0-9_.-]{40,})$")}
PAGE = Path(__file__).with_name("index.html")
FAVICON = Path(__file__).with_name("favicon.svg")
videos = {}  # ponytail: unbounded in-memory cache, fine for a personal app; restart clears it


def api_keys():
    """A key on the clipboard is saved to Keychain (replacing that provider's old one); returns all saved keys."""
    clip = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    keys = {}
    for account, key_re in KEY_RES.items():
        keychain = ["-s", "youtube-summarizer", "-a", account]
        if key_re.match(clip):
            # ponytail: -w puts the key on argv for a moment (visible to local `ps`); fine on a single-user Mac
            subprocess.run(["security", "add-generic-password", "-U", *keychain, "-w", clip], capture_output=True)
        r = subprocess.run(["security", "find-generic-password", *keychain, "-w"], capture_output=True, text=True)
        if r.returncode == 0:
            keys[account] = r.stdout.strip()
    return keys


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
            self.send(200, {"source": "+".join(api_keys()) or None})
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
        self.stream(lambda keys: summarize.stream_summary(info, transcript, keys, summarize.LANGUAGES[lang]))

    def translate(self, markdown, lang):
        if lang not in summarize.LANGUAGES or not markdown.strip():
            return self.send(400, {"error": "Nothing to translate."})
        self.stream(lambda keys: summarize.stream_translation(markdown, keys, summarize.LANGUAGES[lang]))

    def stream(self, make):
        keys = api_keys()
        if not keys:
            return self.send(401, {"error": "No API key. Copy your Anthropic (sk-ant-…) or Gemini API key to the clipboard, then try again."})
        chunks = make(keys)
        try:
            model, err = next(chunks, ""), None  # waits for the first text, so the model (or fallback) is known
        except Exception as e:
            model, err = "", e
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Model", re.sub(r"[^\w.:() -]", "", model))  # shown under the title; API text, so no CR/LF
        self.end_headers()  # no Content-Length: body streams until the connection closes
        try:
            if err:
                raise err
            for chunk in chunks:
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
