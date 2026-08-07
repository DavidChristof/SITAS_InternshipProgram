"""流式语音面试：语音转文字（成员A：任务3/4 可选增强）。

实现方案（按顺序尝试）：
1. faster-whisper 本地转写（Windows CPU 可运行，模型建议 base 或 small，中文效果够用）
   pip install faster-whisper
2. 若未安装 faster-whisper，则返回占位提示（面试仍可走文字模式）。

前端通过 MediaRecorder 录音上传，后端保存后调用本函数转写。
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)

_WHISPER_MODEL = None  # 懒加载


def _get_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            from faster_whisper import WhisperModel  # 延迟导入，未安装时不报错

            _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("faster-whisper 不可用: %s", exc)
            _WHISPER_MODEL = False
    return _WHISPER_MODEL or None


def transcribe(audio_path: str | Path, language: str = "zh") -> str:
    """语音文件转文字。返回转写文本；不可用时返回空串。"""
    model = _get_model()
    if model is None:
        logger.warning("未安装 faster-whisper，语音转写跳过。安装：pip install faster-whisper")
        return ""

    segments, _info = model.transcribe(str(audio_path), language=language, vad_filter=True)
    return "".join(seg.text for seg in segments).strip()
