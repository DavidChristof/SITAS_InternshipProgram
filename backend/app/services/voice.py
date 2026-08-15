"""流式语音面试：语音转文字（成员A：任务3/10 可选增强）。

实现方案（按顺序尝试）：
1. faster-whisper 本地转写（Windows CPU 可运行，模型默认 base，中文效果够用）
   pip install faster-whisper
2. 若未安装 faster-whisper，或模型加载/文件异常，则优雅返回空串（面试仍走文字模式）。

前端通过 MediaRecorder 录音上传，后端保存后调用本函数转写。
铁律：transcribe 绝不抛异常，任何失败都返回空串。
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)

_WHISPER_MODEL = None  # 懒加载；False 表示加载失败（已尝试，不再重试）


def _get_model():
    """懒加载 WhisperModel。未安装/加载失败返回 None 并缓存 False。"""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            from faster_whisper import WhisperModel  # 延迟导入，未安装时不报错

            _WHISPER_MODEL = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type=settings.whisper_compute_type,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "faster-whisper 不可用（安装：pip install faster-whisper）: %s", exc
            )
            _WHISPER_MODEL = False
    return _WHISPER_MODEL or None


def transcribe(audio_path: str | Path, language: str = "zh") -> str:
    """语音文件转文字。返回转写文本；任何不可用/失败场景都返回空串。"""
    model = _get_model()
    if model is None:
        logger.warning("faster-whisper 未就绪，语音转写跳过（面试可走文字模式）")
        return ""

    path = Path(audio_path)
    if not path.exists():
        logger.warning("语音文件不存在: %s", path)
        return ""
    try:
        if path.stat().st_size == 0:
            logger.warning("语音文件为空: %s", path)
            return ""
    except OSError as exc:
        logger.warning("无法读取语音文件信息 %s: %s", path, exc)
        return ""

    try:
        segments, _info = model.transcribe(
            str(path), language=language, vad_filter=True
        )
        text = "".join(seg.text for seg in segments).strip()
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("语音转写失败 %s: %s", path, exc)
        return ""
