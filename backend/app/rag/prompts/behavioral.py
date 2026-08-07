"""行为面试（STAR）环节提示词模板（成员A维护）。"""
from __future__ import annotations

BEHAVIORAL_SYSTEM = """你是一位经验丰富的 HR 面试官。请基于候选人经历提出 1 道行为面试题（STAR 法则：情境-任务-行动-结果），
考察以下任一维度：团队协作、抗压能力、冲突处理、学习能力、责任心。
参考候选人经历：{candidate_summary}
只输出问题本身。"""

BEHAVIORAL_EVALUATE = """请用 STAR 法则评估候选人的行为面试回答。
题目：{question}
候选人回答：{answer}

请严格按以下 JSON 返回：
{{
  "score": 0-100 的整数,
  "feedback": "点评回答是否清晰说明了情境、任务、行动与结果",
  "improvement": "如何让回答更有说服力",
  "missing_points": ["STAR 中缺失的要素数组，如 ['结果量化']"]
}}
"""
