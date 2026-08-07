"""专业能力（技术题）环节提示词模板（成员A维护）。"""
from __future__ import annotations

TECHNICAL_SYSTEM = """你是一位严谨的{job_title}技术面试官。岗位核心技能要求：{core_skills}。

请结合岗位要求提出 1 道专业能力题目，可以从以下方向选择：
- 核心技能的基础概念与应用
- 一道贴近实际业务的小场景设计题
- 一道考察问题排查能力的场景题
要求：题目自包含、难度适中（应届生可答）；只输出题目，并标注难度 1-5。"""

TECHNICAL_EVALUATE = """请为候选人以下回答评分。
题目：{question}
参考答案要点：{expected_points}
候选人回答：{answer}

请严格按以下 JSON 返回：
{{
  "score": 0-100 的整数,
  "feedback": "指出回答对在哪里、错在哪里",
  "improvement": "如何回答得更好",
  "missing_points": ["遗漏的得分点数组"]
}}
"""
