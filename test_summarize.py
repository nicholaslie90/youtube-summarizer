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


if __name__ == "__main__":
    test_ts(); test_pick_caption_lang(); test_parse_json3(); print("ok")
