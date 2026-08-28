"""反问环节提示词模板（成员A维护）。

字段约定（与 interview_agent.py 的 format 调用严格对齐）：
- 出题 REVERSE_SYSTEM   占位：{company_brief}
- 评分 REVERSE_EVALUATE 占位：{job_title} {question} {answer}
  注意：候选人的反问内容必须引用 {answer}（候选人的回答），
  {question} 只是面试官收尾问话作为上下文，绝不可当作"候选人反问"（曾踩坑）。
"""
from __future__ import annotations

REVERSE_SYSTEM = """面试已接近尾声。请以面试官口吻告诉候选人：可以就岗位工作内容、团队氛围、成长路径、公司文化等方面提 1-2 个问题。
企业背景：{company_brief}
只输出面试官收尾的话术（2-3 句）。"""

REVERSE_EVALUATE = """请评估候选人反问问题的质量。
岗位：{job_title}
面试官收尾问话（上下文，非候选人反问）：{question}
候选人反问（要评估的对象）：{answer}

评分参考（100 分制）：
- 是否体现对岗位/公司的深入思考与预先调研（40%）
- 是否具体、有针对性、可回答（30%）
- 是否展现清晰的求职动机与发展规划（20%）
- 提问的条理性与沟通礼仪（10%）

若候选人反问贴合岗位/公司实际、问得具体深入，应给高分（80+），不要因回答较长而压分。

请严格按以下 JSON 返回：
{{
  "score": 0-100 的整数,
  "feedback": "点评反问质量",
  "improvement": "可参考的反问方向"
}}"""
