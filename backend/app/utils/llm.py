"""DeepSeek 大模型调用封装（成员A维护）。

项目内所有 LLM 调用必须经过本模块，禁止直接 new OpenAI client。
- chat():     通用文本对话
- chat_json(): 强制解析 JSON 输出，用于评分/画像等结构化场景
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from ..config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（base_url 指向 DeepSeek）。"""
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            logger.warning("未配置 DEEPSEEK_API_KEY，LLM 调用将失败。请在 .env 中配置。")
        _client = OpenAI(
            api_key=settings.deepseek_api_key or "sk-empty",
            base_url=settings.deepseek_base_url,
        )
    return _client


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """通用对话。messages 形如 [{"role": "system"|"user"|"assistant", "content": str}]"""
    resp = get_client().chat.completions.create(
        model=model or settings.deepseek_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def chat_json(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """调用并强制解析 JSON 输出；解析失败抛 ValueError 交由调用方降级。"""
    text = chat(messages, temperature=temperature, max_tokens=max_tokens)
    text = text.strip()
    # 去掉 markdown 代码块围栏
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"LLM 未返回 JSON：{text[:200]}")
    return json.loads(text[start : end + 1])
