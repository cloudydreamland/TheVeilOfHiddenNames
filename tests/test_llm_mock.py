"""LLM recognizer：偏移对齐与失败模式（全部 mock，不发真实请求）。"""

from __future__ import annotations

import json

import pytest

from helan.recognizers.llm import LLMRecognizer, LLMRecognizerError


def _resp(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


class TestParse:
    def test_offset_alignment_single(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k")
        text = "患者王建国，电话 13812345678。"
        ents = rec._parse(json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王建国"}]}), text)
        assert len(ents) == 1
        assert ents[0].start == 2 and ents[0].end == 5
        assert ents[0].text == "王建国"

    def test_nth_occurrence(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k")
        text = "张三找张三借书"
        ents = rec._parse(
            json.dumps({"entities": [
                {"type": "PERSON_NAME", "text": "张三"},
                {"type": "PERSON_NAME", "text": "张三"},
            ]}),
            text,
        )
        assert [(e.start, e.end) for e in ents] == [(0, 2), (3, 5)]

    def test_unmatched_quote_dropped(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k")
        ents = rec._parse(
            json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王建国不存在的引用"}]}),
            "患者王建国。",
        )
        assert ents == []

    def test_type_not_requested_dropped(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", types=("PHONE",))
        ents = rec._parse(
            json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王建国"}]}),
            "患者王建国。",
        )
        assert ents == []

    def test_invalid_json_raises(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k")
        with pytest.raises(LLMRecognizerError):
            rec._parse("不是json", "文本")

    def test_offset_invariant_holds(self):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k")
        text = "地址：北京市朝阳区建国路88号，联系人李明。"
        ents = rec._parse(
            json.dumps({"entities": [
                {"type": "ADDRESS", "text": "北京市朝阳区建国路88号"},
                {"type": "PERSON_NAME", "text": "李明"},
            ]}),
            text,
        )
        for e in ents:
            assert e.text == text[e.start : e.end]


def _fake_ok_response() -> object:
    """一个可 with 进入、返回有效 JSON 的假 urlopen 响应。"""
    import json

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(
                _resp(json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王建国"}]}))
            ).encode("utf-8")

    return FakeResp()


class TestHttp:
    def test_post_payload_and_parsing(self, monkeypatch):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="secret")
        captured = {}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return json.dumps(
                    _resp(json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王建国"}]}))
                ).encode("utf-8")

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return FakeResp()

        monkeypatch.setattr("helan.recognizers.llm.urllib.request.urlopen", fake_urlopen)
        ents = rec("患者王建国。")
        assert captured["url"].startswith("http://x/chat/completions")
        assert captured["headers"]["Authorization"] == "Bearer secret"
        assert captured["payload"]["temperature"] == 0
        assert ents[0].text == "王建国"

    def test_http_error_wrapped(self, monkeypatch):
        import urllib.error

        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", retries=0)

        def fake_urlopen(req, timeout):
            raise urllib.error.HTTPError("http://x", 400, "boom", None, None)

        monkeypatch.setattr("helan.recognizers.llm.urllib.request.urlopen", fake_urlopen)
        with pytest.raises(LLMRecognizerError, match="HTTP 400"):
            rec("文本")

    def test_retry_on_500_then_success(self, monkeypatch):
        import urllib.error

        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", retries=2)
        calls = {"n": 0}

        def fake_urlopen(req, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.HTTPError("http://x", 500, "flaky", None, None)
            return _fake_ok_response()

        monkeypatch.setattr("helan.recognizers.llm.urllib.request.urlopen", fake_urlopen)
        monkeypatch.setattr("time.sleep", lambda _s: None)  # 跳过退避等待
        ents = rec("患者王建国。")
        assert calls["n"] == 3
        assert ents[0].text == "王建国"

    def test_non_retryable_400_no_retry(self, monkeypatch):
        import urllib.error

        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", retries=2)
        calls = {"n": 0}

        def fake_urlopen(req, timeout):
            calls["n"] += 1
            raise urllib.error.HTTPError("http://x", 400, "bad request", None, None)

        monkeypatch.setattr("helan.recognizers.llm.urllib.request.urlopen", fake_urlopen)
        with pytest.raises(LLMRecognizerError, match="HTTP 400"):
            rec("文本")
        assert calls["n"] == 1  # 400 不重试

    def test_rate_limit_enforces_interval(self, monkeypatch):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", max_per_second=1000.0)

        def fake_urlopen(req, timeout):
            return _fake_ok_response()

        sleeps: list[float] = []
        monkeypatch.setattr("helan.recognizers.llm.urllib.request.urlopen", fake_urlopen)
        monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
        monkeypatch.setattr("time.monotonic", lambda: 100.0)  # 恒定时钟，强制触发等待
        rec("患者王建国。")  # 首次请求不等待
        rec("患者王建国。")  # 第二次必须等到最小间隔
        assert len(sleeps) == 1 and sleeps[0] > 0

    def test_missing_key_env(self, monkeypatch):
        monkeypatch.delenv("MIANJU_LLM_API_KEY", raising=False)
        rec = LLMRecognizer(base_url="http://x", model="m")
        assert rec.api_key == ""

    def test_chunking_offsets_shifted(self, monkeypatch):
        rec = LLMRecognizer(base_url="http://x", model="m", api_key="k", max_chars=5)

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return json.dumps(
                    _resp(json.dumps({"entities": [{"type": "PERSON_NAME", "text": "王"}]}))
                ).encode("utf-8")

        monkeypatch.setattr(
            "helan.recognizers.llm.urllib.request.urlopen", lambda req, timeout: FakeResp()
        )
        ents = rec("王先生住在王家卫的电影里")
        # 两个分块各命中一个 "王"，第二块的偏移必须平移
        starts = sorted(e.start for e in ents)
        assert starts[1] >= 5
        text = "王先生住在王家卫的电影里"
        for e in ents:
            assert e.text == text[e.start : e.end]
