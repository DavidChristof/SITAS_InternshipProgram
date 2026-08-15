"""SQL Agent 测试（成员A，阶段三·任务9）。

覆盖：
1. LLM 生成合法 SQL：白名单通过、正确执行返回数据
2. 危险 SQL 全部被拦：非 SELECT / 堆叠语句 / 注释 / 白名单外表 / 白名单外列
3. 无 key 规则兜底：各岗位平均分 / 通过率 / 各环节平均分 / 不支持的问题
4. 空问题不崩溃
"""
import sqlalchemy as sa
import pytest

from backend.app.services import sql_agent
from backend.app.utils import llm

_DDL = """
CREATE TABLE enterprises (id INTEGER PRIMARY KEY, name TEXT, industry TEXT, description TEXT, created_at TEXT);
CREATE TABLE jobs (id INTEGER PRIMARY KEY, enterprise_id INTEGER, title TEXT, description TEXT, requirements TEXT, skills TEXT, created_at TEXT);
CREATE TABLE candidates (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, resume_text TEXT, resume_file TEXT, profile_json TEXT, status TEXT, created_at TEXT);
CREATE TABLE interviews (id INTEGER PRIMARY KEY, candidate_id INTEGER, job_id INTEGER, interviewer_id INTEGER, status TEXT, current_round INTEGER, report_json TEXT, started_at TEXT, created_at TEXT);
CREATE TABLE interview_answers (id INTEGER PRIMARY KEY, interview_id INTEGER, round_no INTEGER, category TEXT, question TEXT, answer_text TEXT, audio_url TEXT, score REAL, feedback TEXT, evidence TEXT, created_at TEXT);
CREATE TABLE interviewers (id INTEGER PRIMARY KEY, name TEXT, role TEXT, title TEXT, created_at TEXT);
CREATE TABLE questions (id INTEGER PRIMARY KEY, job_id INTEGER, category TEXT, question TEXT, expected_points TEXT, sample_answer TEXT, difficulty INTEGER, created_at TEXT);
"""

_GOOD_SQL = (
    "SELECT j.title, ROUND(AVG(a.score), 1) AS avg_score "
    "FROM interviews i JOIN jobs j ON i.job_id = j.id "
    "JOIN interview_answers a ON a.interview_id = i.id "
    "WHERE i.status = 'finished' GROUP BY j.title ORDER BY avg_score DESC"
)


@pytest.fixture()
def temp_engine(tmp_path, monkeypatch):
    eng = sa.create_engine(f"sqlite:///{tmp_path / 't.db'}")
    with eng.begin() as conn:
        for stmt in (s.strip() for s in _DDL.split(";")):
            if stmt:
                conn.execute(sa.text(stmt))
        conn.execute(sa.text("INSERT INTO enterprises (id, name) VALUES (1,'甲公司'),(2,'乙公司')"))
        conn.execute(sa.text("INSERT INTO jobs (id, enterprise_id, title) VALUES (1,1,'Python后端'),(2,2,'前端开发')"))
        conn.execute(sa.text("INSERT INTO candidates (id, name) VALUES (1,'张三'),(2,'李四')"))
        conn.execute(sa.text(
            "INSERT INTO interviews (id, candidate_id, job_id, status) VALUES "
            "(1,1,1,'finished'),(2,2,1,'finished'),(3,1,2,'pending')"
        ))
        # 已结束的两场面试共 4 条回答（job1 平均分 75.0）；pending 的 1 条不计入
        conn.execute(sa.text(
            "INSERT INTO interview_answers (id, interview_id, round_no, category, question, answer_text, score) VALUES "
            "(1,1,1,'technical','q','a',90),(2,1,2,'project','q','a',70),"
            "(3,2,1,'technical','q','a',80),(4,2,2,'project','q','a',60),(5,3,1,'technical','q','a',50)"
        ))
    monkeypatch.setattr(sql_agent, "engine", eng)
    return eng


class TestAskLLM:
    def test_valid_sql_returns_data(self, temp_engine, monkeypatch):
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: _GOOD_SQL)
        result = sql_agent.ask("各岗位平均分")
        assert result["sql"] == _GOOD_SQL
        assert result["columns"] == ["title", "avg_score"]
        # 仅 job1 有 finished 面试，(90+70+80+60)/4 = 75.0
        assert result["rows"] == [["Python后端", 75.0]]
        assert "1 行" in result["explanation"]

    def test_code_fence_stripped(self, temp_engine, monkeypatch):
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: f"```sql\n{_GOOD_SQL};\n```")
        result = sql_agent.ask("各岗位平均分")
        assert result["sql"] == _GOOD_SQL
        assert result["rows"]

    def test_empty_sql_degrades(self, temp_engine, monkeypatch):
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: "")
        result = sql_agent.ask("各岗位平均分")
        assert result["sql"] == _GOOD_SQL  # 规则兜底
        assert result["rows"] == [["Python后端", 75.0]]


class TestSafety:
    """危险 SQL 必须被拦并降级为规则查询，绝不透传给数据库执行。"""

    @pytest.mark.parametrize(
        "bad_sql",
        [
            "DELETE FROM interviews",            # 非 SELECT（也是黑名单关键字）
            "INSERT INTO jobs (title) VALUES ('x')",
            "SELECT * FROM interviews; DROP TABLE candidates",  # 堆叠语句
            "SELECT * FROM interviews -- drop",  # 注释
            "SELECT * FROM interviews /* drop */",
            "SELECT * FROM sqlite_master",       # 内部对象
            "SELECT * FROM users",               # 白名单外的表
            "SELECT i.secret FROM interviews i",  # 白名单外的列（显式 表.列）
            "PRAGMA table_info(interviews)",      # 系统级
        ],
    )
    def test_unsafe_sql_blocked(self, temp_engine, monkeypatch, bad_sql):
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: bad_sql)
        result = sql_agent.ask("各岗位平均分")
        # 降级到规则查询：返回的是规则 SQL（或安全说明），绝不含坏 SQL
        assert result["sql"] != bad_sql
        assert result["rows"] == [["Python后端", 75.0]]  # 规则兜底真实数据

    def test_alias_resolved_column_rejected_at_validation(self):
        # LLM 曾臆造 i.result 列：别名解析后应在校验阶段就被拦，而不是等执行报错
        with pytest.raises(ValueError, match="不在白名单"):
            sql_agent._validate_sql("SELECT i.result FROM interviews i")

    def test_valid_aliased_sql_passes_validation(self):
        sql_agent._validate_sql(
            "SELECT j.title, ROUND(AVG(a.score),1) AS avg_score "
            "FROM interviews i JOIN jobs j ON i.job_id=j.id "
            "JOIN interview_answers a ON a.interview_id=i.id "
            "WHERE i.status='finished' GROUP BY j.title"
        )

    def test_unsafe_sql_with_unsupported_question(self, temp_engine, monkeypatch):
        # 危险 SQL + 问题不匹配任何规则 -> 给出可读说明而非抛异常
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: "DROP TABLE candidates")
        result = sql_agent.ask("给我删掉候选人表")
        assert "sqlite" not in result["sql"].lower() or result["sql"] == ""
        assert "查询失败" in result["explanation"] or "暂不支持" in result["explanation"]


class TestRuleFallback:
    def test_avg_per_job(self, temp_engine, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("各岗位平均分")
        assert result["rows"] == [["Python后端", 75.0]]
        assert "规则查询" in result["explanation"]

    def test_pass_rate(self, temp_engine, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("各岗位面试通过率")
        assert result["columns"] == ["title", "total", "passed", "pass_rate"]
        # job1: finished 2 / total 2 = 100.0；job2: 0/1 = 0.0
        by = {r[0]: r[3] for r in result["rows"]}
        assert by["Python后端"] == 100.0
        assert by["前端开发"] == 0.0

    def test_category_avg(self, temp_engine, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("各环节平均分")
        assert result["columns"] == ["category", "avg_score", "answer_count"]

    def test_unsupported_question_readable(self, temp_engine, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("今天天气怎么样")
        assert result["sql"] == ""
        assert "暂不支持" in result["explanation"]

    def test_empty_question_no_crash(self, temp_engine, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("")
        assert "question" in result


class TestWhitelistSchema:
    def test_all_model_tables_in_whitelist(self):
        """白名单必须与成员B 的表结构一致（防止漏表导致误拦合法查询）。"""
        assert {"enterprises", "jobs", "candidates", "interviews", "interview_answers", "interviewers", "questions"} <= sql_agent._SAFE_TABLES

    def test_key_columns_present(self):
        assert "score" in sql_agent._SAFE_SCHEMA["interview_answers"]
        assert "status" in sql_agent._SAFE_SCHEMA["interviews"]
        assert "title" in sql_agent._SAFE_SCHEMA["jobs"]
        assert "name" in sql_agent._SAFE_SCHEMA["enterprises"]
