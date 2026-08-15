"""utils/llm.py 单元测试（成员A）。

测试 JSON 解析健壮性与重试逻辑（用 monkeypatch 模拟，不真实调用 DeepSeek）。
运行：pytest backend/tests/test_llm.py -v
"""
import pytest

from backend.app.utils import llm


class TestParseJson:
    """_parse_json 的降级提取能力。"""

    def test_plain_json(self):
        assert llm._parse_json('{"a": 1}') == {"a": 1}

    def test_markdown_fence(self):
        assert llm._parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_fence_no_lang(self):
        assert llm._parse_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_text_around(self):
        assert llm._parse_json('好的，结果如下：{"a": 1} 以上') == {"a": 1}

    def test_nested_object(self):
        assert llm._parse_json('{"a": {"b": [1, 2]}}') == {"a": {"b": [1, 2]}}

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            llm._parse_json("这根本不是JSON")


class TestChatRetry:
    """chat() 的瞬时错误重试逻辑。"""

    def test_retry_then_success(self, monkeypatch):
        calls = {"n": 0}

        def fake_once(messages, model, temperature, max_tokens):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("connect timeout")
            return "ok"

        monkeypatch.setattr(llm, "_chat_once", fake_once)
        monkeypatch.setattr(llm, "_RETRYABLE", (TimeoutError,))
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        assert llm.chat([{"role": "user", "content": "hi"}]) == "ok"
        assert calls["n"] == 2  # 第一次失败，重试一次成功

    def test_retry_exhausted_raises(self, monkeypatch):
        def fake_once(messages, model, temperature, max_tokens):
            raise TimeoutError("always fails")

        monkeypatch.setattr(llm, "_chat_once", fake_once)
        monkeypatch.setattr(llm, "_RETRYABLE", (TimeoutError,))
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        with pytest.raises(RuntimeError, match="已重试"):
            llm.chat([{"role": "user", "content": "hi"}])

    def test_non_retryable_propagates(self, monkeypatch):
        """非瞬时错误（如 key 错误）不重试，直接抛出。"""

        def fake_once(messages, model, temperature, max_tokens):
            raise ValueError("bad request")

        monkeypatch.setattr(llm, "_chat_once", fake_once)
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        with pytest.raises(ValueError, match="bad request"):
            llm.chat([{"role": "user", "content": "hi"}])
