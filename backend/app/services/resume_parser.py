"""简历解析与岗位画像模块（成员A：任务1）。

职责：从简历文本抽取教育经历、项目经历、技能关键词、岗位要求、能力维度。
策略：先规则提取（正则抓邮箱/手机/学历/常见技能词），再用 LLM 补全结构化字段；
      LLM 失败时降级为纯规则结果，保证接口不抛异常。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..utils import llm

# ============ 规则提取 ============
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"1[3-9]\d{9}")
_DEGREE_KEYWORDS = ["博士", "硕士", "本科", "大专", "学士"]


def _rule_extract(text: str) -> dict[str, Any]:
    """纯规则提取的兜底画像。"""
    degree = next((d for d in _DEGREE_KEYWORDS if d in text), "")
    return {
        "name": "",
        "email": (_EMAIL_RE.findall(text) or [""])[0],
        "phone": (_PHONE_RE.findall(text) or [""])[0],
        "degree": degree,
        "education": [],
        "projects": [],
        "skills": [],
        "internships": [],
        "summary": "",
        "rule_only": True,
    }


# ============ LLM 解析 ============
_RESUME_PARSE_SYSTEM = """你是简历解析助手。请从候选人简历文本中抽取以下字段，并以 JSON 返回：
{
  "name": "姓名",
  "email": "邮箱",
  "phone": "手机号",
  "education": [{"school": "学校", "degree": "学历", "major": "专业", "years": "时间"}],
  "projects": [{"name": "项目名", "role": "角色", "description": "项目描述", "tech_stack": "技术栈", "achievements": "成果与量化指标"}],
  "skills": ["技能关键词数组"],
  "internships": [{"company": "公司", "position": "职位", "duration": "时长", "description": "职责描述"}],
  "summary": "一句话候选人概述"
}
只输出 JSON，不要任何解释。"""


def parse_resume(resume_text: str) -> dict[str, Any]:
    """解析简历文本，返回结构化画像。

    返回字段（供面试 Agent / 岗位画像使用）：
    name, email, phone, education[], projects[], skills[], internships[], summary
    """
    if not resume_text or not resume_text.strip():
        return _rule_extract("")
    messages = [
        {"role": "system", "content": _RESUME_PARSE_SYSTEM},
        {"role": "user", "content": resume_text[:6000]},
    ]
    try:
        data = llm.chat_json(messages)
        base = _rule_extract(resume_text)
        base.update({k: v for k, v in data.items() if v})
        base["rule_only"] = False
        return base
    except Exception as exc:  # noqa: BLE001  网络/解析失败一律降级
        logging.getLogger(__name__).warning("简历解析降级为规则模式: %s", exc)
        return _rule_extract(resume_text)
