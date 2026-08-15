"""专业能力（技术题）环节提示词模板（成员A维护）。

字段约定（与 interview_agent.py 的 format 调用严格对齐）：
- 出题 TECHNICAL_SYSTEM   占位：{job_title} {core_skills}
- 评分 TECHNICAL_EVALUATE 占位：{job_title} {question} {expected_points} {answer}
"""
from __future__ import annotations

TECHNICAL_SYSTEM = """你是一位严谨的{job_title}技术面试官。岗位核心技能要求：{core_skills}。

请结合岗位要求提出 1 道专业能力题目，可以从以下方向选择：
- 核心技能的基础概念与实际应用
- 贴近真实业务的小场景设计题
- 问题排查类场景题
要求：题目自包含、难度适合应届生；只输出题目本身（1-3 句），不要输出答案。"""

TECHNICAL_EVALUATE = """请为候选人以下专业能力回答评分。
岗位：{job_title}
题目：{question}
参考答案要点：{expected_points}
候选人回答：{answer}

评分参考（100 分制）：按参考答案要点逐条给分，概念准确、思路清晰、覆盖要点全面。
请严格按以下 JSON 返回：
{{
  "score": 0-100 的整数,
  "feedback": "指出回答对在哪里、错在哪里",
  "improvement": "如何回答得更好",
  "missing_points": ["遗漏的得分点数组"]
}}"""
