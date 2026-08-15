"""DeepSeek 大模型调用封装（成员A维护）。

项目内所有 LLM 调用必须经过本模块，禁止直接 new OpenAI client。
- chat():      通用文本对话（带超时 + 瞬时错误重试 1 次）
- chat_json(): 强制解析 JSON 输出，用于评分/画像等结构化场景

约定：
- 网络/超时/限流等瞬时错误自动重试一次；
- 重试耗尽抛 RuntimeError；认证/参数类错误（如 key 错误）立即抛出不重试；
- 调用方仍需自行 try/except 做业务降级（见 services/ 下各模块）。
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from ..config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

# ===== 网络调用参数 =====
REQUEST_TIMEOUT: float = 30.0  # 单次请求超时（秒）
MAX_RETRIES: int = 1  # 瞬时错误重试次数（共最多 1+1=2 次尝试）
RETRY_WAIT_BASE: float = 1.0  # 重试等待基数（秒，线性递增）

# 可重试的瞬时错误类型
_RETRYABLE: tuple[type[BaseException], ...] = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)


def get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（base_url 指向 DeepSeek，带超时）。"""
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            logger.warning("未配置 DEEPSEEK_API_KEY，LLM 调用将失败。请在 .env 中配置。")
        _client = OpenAI(
            api_key=settings.deepseek_api_key or "sk-empty",
            base_url=settings.deepseek_base_url,
            timeout=REQUEST_TIMEOUT,
            max_retries=0,  # 重试由本模块控制（便于日志与降级），关闭 SDK 内建重试
        )
    return _client


def reset_client() -> None:
    """重置客户端（测试时用）。"""
    global _client
    _client = None


def _chat_once(
    messages: list[dict[str, str]],
    model: str | None,
    temperature: float,
    max_tokens: int,
) -> str:
    """单次请求（不重试）。"""
    resp = get_client().chat.completions.create(
        model=model or settings.deepseek_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """通用对话（带超时 + 瞬时错误重试）。messages 形如 [{"role", "content"}]。"""
    last_exc: BaseException | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _chat_once(messages, model, temperature, max_tokens)
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_WAIT_BASE * (attempt + 1)
                logger.warning("LLM 调用失败，%.0fs 后重试（第 %d/%d 次）：%s",
                               wait, attempt + 1, MAX_RETRIES, exc)
                time.sleep(wait)
    # 瞬时错误重试耗尽：转成统一异常，由调用方降级处理
    raise RuntimeError(
        f"DeepSeek 调用失败（已重试 {MAX_RETRIES} 次）：{last_exc}"
    ) from last_exc


def chat_json(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """调用并强制解析 JSON 输出；解析失败抛 ValueError 交由调用方降级。"""
    text = chat(messages, temperature=temperature, max_tokens=max_tokens)
    return _parse_json(text)


def _parse_json(text: str) -> dict[str, Any]:
    """从 LLM 输出中稳健地提取 JSON 对象（逐级尝试）。"""
    text = text.strip()
    # 1) 整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2) 去掉 markdown 代码块围栏后解析
    if text.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        stripped = re.sub(r"```\s*$", "", stripped).strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    # 3) 截取第一个 { 到最后一个 } 的片段
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"LLM 未返回有效 JSON：{text[:200]}")
