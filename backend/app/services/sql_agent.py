"""招聘数据 SQL Agent（成员A：任务3/任务9）。

职责：用自然语言查询面试/招聘数据（如"各岗位面试平均分"、"通过率最高的岗位"），
由 LLM 生成 SQL，经白名单校验后在 SQLite 上执行并返回结果与解释。

安全模型（白名单优先，黑名单兜底）：
1. 仅允许单条 SELECT：堆叠语句、SQL 注释一律拒绝；
2. 危险关键字黑名单兜底（insert/update/delete/drop/...）；
3. 表名必须命中 _SAFE_SCHEMA 白名单，禁止访问 sqlite_master 等内部对象；
4. 直接以"表名.列名"引用的列必须命中该表白名单。
LLM 不可用或生成的 SQL 不安全/执行失败时，按问题关键词回退到内置规则查询，
保证"各岗位平均分"这类演示问题在无 key 场景也能返回真实数据。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from ..database import engine
from ..utils import llm

logger = logging.getLogger(__name__)

# 白名单：允许的表与列（与 backend/app/models 中成员B 的表结构保持一致）
_SAFE_SCHEMA: dict[str, set[str]] = {
    "enterprises": {"id", "name", "industry", "description", "created_at"},
    "jobs": {"id", "enterprise_id", "title", "description", "requirements", "skills", "created_at"},
    "candidates": {"id", "name", "email", "phone", "resume_text", "resume_file", "profile_json", "status", "created_at"},
    "interviews": {"id", "candidate_id", "job_id", "interviewer_id", "status", "current_round", "report_json", "started_at", "created_at"},
    "interview_answers": {"id", "interview_id", "round_no", "category", "question", "answer_text", "audio_url", "score", "feedback", "evidence", "created_at"},
    "interviewers": {"id", "name", "role", "title", "created_at"},
    "questions": {"id", "job_id", "category", "question", "expected_points", "sample_answer", "difficulty", "created_at"},
}
_SAFE_TABLES = set(_SAFE_SCHEMA)

# 黑名单（兜底）：写/结构/系统级关键字
_BANNED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|attach|detach|pragma|vacuum|reindex|replace|explain)\b",
    re.I,
)
# 语句中的表引用（FROM/JOIN 后跟表名）
_TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
# 显式"表.列"引用
_COLUMN_REF = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b", re.I)
# SQL 注释（SQLite 仅支持 -- 与 /* */）
_COMMENT_RE = re.compile(r"--|/\*|\*/")

_SQL_AGENT_SYSTEM = """你是数据分析师。请把用户的招聘数据问题翻译成 SQLite 查询，只输出一条 SQL。
数据库包含表：enterprises(企业)、jobs(岗位)、candidates(候选人)、interviews(面试记录, status='finished'表示已结束)、interview_answers(逐题回答, 含 score)。
要求：
1. 只输出一条 SQL，且必须以 SELECT 开头；
2. 表名/字段名必须与上述一致，不得访问 sqlite_master；
3. 中文别名请用英文；
4. 不生成注释、不生成分号结尾。
"""


def _clean_sql(raw: str) -> str:
    """清洗 LLM 输出：去掉代码块围栏/首尾分号；拒绝堆叠语句与注释。"""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:sql)?\s*|\s*```$", "", raw, flags=re.I).strip()  # 去掉 ```sql ``` 围栏
    if not raw:
        raise ValueError("LLM 未生成 SQL")
    body = raw.rstrip().rstrip(";").strip()
    if ";" in body:
        raise ValueError("检测到堆叠语句（多条 SQL），已拒绝")
    if _COMMENT_RE.search(body):
        raise ValueError("SQL 含注释，已拒绝")
    return body


# 紧跟表名后的保留字：出现则说明该表没有别名
_JOIN_KEYWORDS = {
    "on", "where", "group", "order", "limit", "having", "as",
    "left", "right", "inner", "cross", "full", "join",
    "union", "except", "intersect",
}


def _alias_after_table(rest: str) -> str | None:
    """解析表名之后的别名（FROM jobs j / FROM jobs AS j），无别名返回 None。"""
    m = re.match(r"\s*(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*)", rest)
    if not m:
        return None
    word = m.group(1).lower()
    return None if word in _JOIN_KEYWORDS else word


def _validate_sql(sql: str) -> None:
    """白名单 + 黑名单双重校验，不通过则抛 ValueError（由 ask 兜底降级）。

    表名一律校验；列引用先解析别名到真实表，再做列白名单校验，
    防止 LLM 通过别名（如 i.secret）引用不存在的列。
    """
    if not sql.upper().startswith("SELECT"):
        raise ValueError("仅允许 SELECT 查询")
    if _BANNED.search(sql):
        raise ValueError("SQL 含危险关键字，已拒绝")
    if re.search(r"sqlite_", sql, re.I):
        raise ValueError("禁止访问 SQLite 内部对象")
    # 表名白名单 + 收集 别名->表名 映射
    aliases: dict[str, str] = {}
    for m in _TABLE_REF.finditer(sql):
        tbl = m.group(1).lower()
        if tbl not in _SAFE_TABLES:
            raise ValueError(f"表 {tbl} 不在白名单")
        alias = _alias_after_table(sql[m.end():])
        if alias:
            aliases[alias] = tbl
    # 列白名单（解析别名）
    for m in _COLUMN_REF.finditer(sql):
        qual, col = m.group(1).lower(), m.group(2).lower()
        tbl = aliases.get(qual, qual)
        if tbl in _SAFE_TABLES and col not in _SAFE_SCHEMA[tbl]:
            raise ValueError(f"列 {qual}.{col} 不在白名单")


# ============ 规则兜底（无 key / LLM 不可用 / SQL 不安全） ============

_RULE_AVG = (
    "SELECT j.title, ROUND(AVG(a.score), 1) AS avg_score "
    "FROM interviews i "
    "JOIN jobs j ON i.job_id = j.id "
    "JOIN interview_answers a ON a.interview_id = i.id "
    "WHERE i.status = 'finished' "
    "GROUP BY j.title ORDER BY avg_score DESC"
)
_RULE_PASS_RATE = (
    "SELECT j.title, COUNT(i.id) AS total, "
    "SUM(CASE WHEN i.status = 'finished' THEN 1 ELSE 0 END) AS passed, "
    "ROUND(100.0 * SUM(CASE WHEN i.status = 'finished' THEN 1 ELSE 0 END) / COUNT(i.id), 1) AS pass_rate "
    "FROM interviews i JOIN jobs j ON i.job_id = j.id "
    "GROUP BY j.title ORDER BY pass_rate DESC"
)
_RULE_CATEGORY = (
    "SELECT category, ROUND(AVG(score), 1) AS avg_score, COUNT(*) AS answer_count "
    "FROM interview_answers GROUP BY category ORDER BY avg_score DESC"
)


def _rule_sql(question: str) -> dict[str, Any]:
    """按问题关键词返回内置规则查询（演示问题可无 key 出数据）。"""
    q = question or ""
    if "通过率" in q:
        sql, label = _RULE_PASS_RATE, "各岗位面试通过率"
    elif "环节" in q or "维度" in q or "category" in q.lower():
        sql, label = _RULE_CATEGORY, "各面试环节平均分"
    elif "平均" in q or ("岗位" in q and "分" in q):
        sql, label = _RULE_AVG, "各岗位面试平均分"
    else:
        return {
            "question": question,
            "sql": "",
            "columns": [],
            "rows": [],
            "explanation": "已降级为规则查询（LLM 暂不可用）：暂不支持该问题，可尝试“各岗位平均分”“面试通过率”“各环节平均分”",
        }

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchmany(50)]
        return {
            "question": question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "explanation": f"规则查询（{label}）：共返回 {len(rows)} 行",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("规则查询失败: %s", exc)
        return {"question": question, "sql": "", "columns": [], "rows": [], "explanation": f"查询失败：{exc}"}


def ask(question: str) -> dict[str, Any]:
    """自然语言查数据。返回 {question, sql, columns, rows, explanation}。

    任何异常（含危险 SQL 被拦、LLM 不可用）都不抛给调用方：
    优先规则兜底给出真实数据，规则也不可用时返回可读错误。
    """
    try:
        sql = llm.chat(
            [
                {"role": "system", "content": _SQL_AGENT_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        sql = _clean_sql(sql)
        _validate_sql(sql)

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
        logger.warning("SQL Agent 降级为规则查询: %s", exc)
        return _rule_sql(question)
