import summarize
from summarize import parse_json3, pick_caption_lang, ts


def test_ts():
    assert ts(65) == "01:05" and ts(3725) == "1:02:05"


def test_pick_caption_lang():
    assert pick_caption_lang({"language": "id", "subtitles": {"en": [], "id": []}}) == ("id", False)
    assert pick_caption_lang({"subtitles": {"live_chat": []}, "automatic_captions": {"en": [], "id-orig": []}}) == ("id-orig", True)
    assert pick_caption_lang({"language": "en", "automatic_captions": {"en-orig": [], "fr": []}}) == ("en-orig", True)
    assert pick_caption_lang({}) == (None, False)


def test_parse_json3():
    events = [{"tStartMs": t * 1000, "segs": [{"utf8": f"word{t}."}]} for t in range(0, 130, 10)]
    events.insert(1, {"tStartMs": 5000, "segs": [{"utf8": "\n"}]})  # blank events are skipped
    paras = parse_json3({"events": events})
    assert [s for s, _ in paras] == [0, 60, 120]
    assert paras[0][1].startswith("word0. word10.")


def test_stream_llm_fallback():
    def claude_down(*a):
        raise RuntimeError("overloaded")
        yield
    def claude_midway(*a):
        yield "claude"
        yield "part"
        raise RuntimeError("dropped")
    llm = lambda keys: list(summarize.stream_llm("s", "c", keys))
    real = summarize.stream_claude, summarize.stream_gemini
    summarize.stream_gemini = lambda s, c, k: iter(["gemini", f"text:{k}"])
    summarize.stream_claude = lambda s, c, k: iter(["claude", f"text:{k}"])
    assert llm({"anthropic": "A", "gemini": "G"}) == ["claude", "text:A"]  # first item = model label
    summarize.stream_claude = claude_down
    assert llm({"anthropic": "A", "gemini": "G"}) == ["gemini (fallback: RuntimeError)", "text:G"]
    assert llm({"gemini": "G"}) == ["gemini (fallback: no Anthropic key)", "text:G"]
    for keys, err in [({"anthropic": "A"}, RuntimeError), ({}, summarize.Error)]:
        try:
            "".join(summarize.stream_llm("s", "c", keys)); assert False
        except err:
            pass
    summarize.stream_claude = claude_midway  # failure after output started: no silent model switch
    try:
        "".join(summarize.stream_llm("s", "c", {"anthropic": "A", "gemini": "G"})); assert False
    except RuntimeError:
        pass
    summarize.stream_claude, summarize.stream_gemini = real


def test_stream_gemini_retries_overload():
    import io, urllib.error, urllib.request
    calls = []
    def busy(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError("u", 503, "x", {}, io.BytesIO(b'{"error":{"message":"busy"}}'))
    real = urllib.request.urlopen, summarize.time.sleep
    urllib.request.urlopen, summarize.time.sleep = busy, lambda s: None
    try:
        next(summarize.stream_gemini("s", "c", "k")); assert False
    except summarize.Error as e:
        assert len(calls) == 3 and "503: busy" in str(e)
    finally:
        urllib.request.urlopen, summarize.time.sleep = real


if __name__ == "__main__":
    test_ts(); test_pick_caption_lang(); test_parse_json3(); test_stream_llm_fallback(); test_stream_gemini_retries_overload(); print("ok")
