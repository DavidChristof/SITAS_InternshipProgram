"""语音转写测试（成员A，阶段三·任务10）。

faster-whisper 为可选依赖，本测试不要求安装：
1. 未安装/加载失败 -> 优雅返回空串（不抛异常）
2. 模型就绪时正确拼接转写文本
3. 文件不存在 / 空文件 / 转写抛错 -> 返回空串
"""
from pathlib import Path

import pytest

from backend.app.services import voice


class _Seg:
    def __init__(self, text):
        self.text = text


class _FakeModel:
    """模拟 faster-whisper 模型：transcribe 返回 (segments 生成器, info)。"""

    def __init__(self, segments=None, exc=None):
        self._segments = segments or []
        self._exc = exc

    def transcribe(self, audio_path, language="zh", vad_filter=True):
        if self._exc:
            raise self._exc
        return iter([_Seg(t) for t in self._segments]), None


def _make_audio(tmp_path, content=b"dummy") -> Path:
    p = tmp_path / "answer.wav"
    p.write_bytes(content)
    return p


class TestNotInstalled:
    def test_returns_empty_when_model_unavailable(self, monkeypatch):
        # 模拟 faster-whisper 未安装/加载失败
        monkeypatch.setattr(voice, "_get_model", lambda: None)
        assert voice.transcribe("whatever.wav") == ""

    def test_get_model_caches_failure(self, monkeypatch):
        # 导入抛错 -> 返回 None，且缓存为 False 避免反复尝试
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("faster_whisper"):
                raise ImportError("No module named 'faster_whisper'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setattr(voice, "_WHISPER_MODEL", None)
        assert voice._get_model() is None
        assert voice._WHISPER_MODEL is False


class TestTranscribeWithModel:
    def test_concatenates_segments(self, monkeypatch, tmp_path):
        fake = _FakeModel(segments=["你", "好，", "世界。  "])
        monkeypatch.setattr(voice, "_get_model", lambda: fake)
        audio = _make_audio(tmp_path)
        assert voice.transcribe(audio) == "你好，世界。"

    def test_missing_file_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(voice, "_get_model", lambda: _FakeModel(["文本"]))
        assert voice.transcribe(tmp_path / "no.wav") == ""

    def test_empty_file_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(voice, "_get_model", lambda: _FakeModel(["文本"]))
        audio = _make_audio(tmp_path, content=b"")
        assert voice.transcribe(audio) == ""

    def test_transcribe_raises_returns_empty(self, monkeypatch, tmp_path):
        fake = _FakeModel(exc=RuntimeError("decode failed"))
        monkeypatch.setattr(voice, "_get_model", lambda: fake)
        audio = _make_audio(tmp_path)
        assert voice.transcribe(audio) == ""

    def test_accepts_path_string(self, monkeypatch, tmp_path):
        fake = _FakeModel(segments=["你好"])
        monkeypatch.setattr(voice, "_get_model", lambda: fake)
        audio = _make_audio(tmp_path)
        assert voice.transcribe(str(audio)) == "你好"

    def test_language_param_passed(self, monkeypatch, tmp_path):
        captured = {}

        class _CapturingModel(_FakeModel):
            def transcribe(self, audio_path, language="zh", vad_filter=True):
                captured["language"] = language
                return super().transcribe(audio_path, language=language, vad_filter=vad_filter)

        monkeypatch.setattr(voice, "_get_model", lambda: _CapturingModel(["x"]))
        audio = _make_audio(tmp_path)
        assert voice.transcribe(audio, language="en") == "x"
        assert captured["language"] == "en"
