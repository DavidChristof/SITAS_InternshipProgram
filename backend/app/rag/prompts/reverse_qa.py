"""反问环节提示词模板（成员A维护）。"""
from __future__ import annotations

REVERSE_SYSTEM = """面试已接近尾声。请以面试官口吻告诉候选人：可以就岗位工作内容、团队氛围、成长路径、公司文化等方面提 1-2 个问题。
结合企业资料：{company_brief}
只输出面试官收尾的话术。"""

REVERSE_EVALUATE = """请评估候选人反问问题的质量。
岗位：{job_title}
候选人反问：{question}

请严格按以下 JSON 返回：
{{
  "score": 0-100 的整数,
  "feedback": "点评反问问题是否体现对岗位/公司的思考",
  "improvement": "可参考的反问方向"
}}
"""
