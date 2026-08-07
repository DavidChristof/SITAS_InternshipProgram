"""招聘数据 SQL Agent（成员A：任务3）。

职责：用自然语言查询面试/招聘数据（如"面试通过率最高的岗位"、"各岗位平均分"），
由 LLM 生成 SQL，在 SQLite 上执行并返回结果与解释。

注意：仅允许 SELECT 查询，防止注入破坏数据；SQL 黑名单兜底。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from ..database import engine
from ..utils import llm

logger = logging.getLogger(__name__)

_BANNED = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|attach|pragma)\b", re.I)

_SQL_AGENT_SYSTEM = """你是数据分析师。请把用户的招聘数据问题翻译成 SQLite 查询。
数据库包含表：enterprises(企业)、jobs(岗位)、candidates(候选人)、interviews(面试记录, status='finished'表示已结束)、interview_answers(逐题回答, 含 score)。
要求：
1. 只输出一条 SQL，且必须以 SELECT 开头；
2. 表名/字段名必须与上述一致；
3. 中文别名请用英文；
4. 不生成注释。
"""


def ask(question: str) -> dict[str, Any]:
    """自然语言查数据。返回 {question, sql, columns, rows, explanation}。

    任何异常（含危险 SQL 被拦）都会返回可读错误，不抛给调用方。
    """
    try:
        sql = llm.chat(
            [
                {"role": "system", "content": _SQL_AGENT_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=300,
        ).strip()
        sql = sql.strip().strip(";")
        if not sql.upper().startswith("SELECT"):
            raise ValueError("SQL Agent 生成了非 SELECT 语句，已拒绝")
        if _BANNED.search(sql):
            raise ValueError("SQL 包含危险关键字，已拒绝")

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchmany(50)]

        return {
            "question": question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "explanation": f"共返回 {len(rows)} 行",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("SQL Agent 失败: %s", exc)
        return {"question": question, "sql": "", "columns": [], "rows": [], "explanation": f"查询失败：{exc}"}
