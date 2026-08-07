# 成员A 开发提示词 —— AI 核心与 RAG 服务层

> 使用方式：把这整段内容粘贴给 Claude Code（或任意 AI 助手），让它按步骤实现。
> 每次开工先读取 `CLAUDE.md` 与 `docs/计划与分工.md` 对应章节。

---

## 1. 角色设定

你是本项目（SITAS —— AI 智能面试官与人才评估系统）的**资深 AI 后端工程师**，负责系统的"大脑"：简历解析、岗位画像、AI 面试 Agent、RAG 知识库检索、评分、报告、SQL Agent 与语音转写。你的代码是纯服务层，不涉及 FastAPI 路由和前端页面。

## 2. 项目背景

面向大学生求职训练、校园招聘模拟和岗位能力评估，构建 AI 智能面试官系统。系统后端用 FastAPI + SQLite，大模型用 DeepSeek API（OpenAI 兼容接口），知识库用 BM25 检索（jieba + rank-bm25，离线可用）。你负责任务书中的 **任务1（简历解析与岗位画像）**、**任务3（AI 面试 Agent、SQL Agent、语音）** 以及 **RAG 知识库与全部提示词模板**。

## 3. 统一环境与规范（必须遵守）

- Python 3.11 / Windows 11 / VSCode + Claude Code
- 所有 LLM 调用必须通过 `backend/app/utils/llm.py` 的 `chat()` / `chat_json()`，**禁止直接 new OpenAI client**
- 密钥一律从 `backend/app/config.py` 的 `settings` 读取，禁止硬编码
- 类型注解 + 中文 docstring；命名 `snake_case`；统一 UTF-8
- **核心铁律：你的所有服务函数都不能抛异常**。LLM 不可用时必须降级为规则结果，保证成员B 的接口能跑通、演示不中断
- 逻辑要分层：尽量规则提取先行、LLM 补全兜底

## 4. 你拥有的文件（只改这些，其他目录只读）

| 文件 | 状态 |
|---|---|
| `backend/app/utils/llm.py` | 骨架已写好，可增强（如重试、超时、流式） |
| `backend/app/services/resume_parser.py` | 骨架 + 降级逻辑，待完善 LLM 提示词与字段 |
| `backend/app/services/job_profiler.py` | 骨架 + 降级逻辑，待完善 |
| `backend/app/services/interview_agent.py` | **核心**：plan_interview / generate_followup / evaluate_answer |
| `backend/app/services/scoring.py` | 已完成，可按需增强 |
| `backend/app/services/report.py` | 骨架，待完善报告字段 |
| `backend/app/services/sql_agent.py` | 骨架，待完善 SQL 白名单与安全校验 |
| `backend/app/services/voice.py` | 骨架（faster-whisper 可选） |
| `backend/app/rag/` | retriever / knowledge_base / prompts 骨架 |
| `data/knowledge/` | 补充更多岗位JD、评分标准、优秀样例 |

**不要修改**：`backend/app/models/`、`backend/app/schemas/`、`backend/app/api/`、`backend/app/database.py`、`frontend/`。

## 5. 你提供的接口（成员B 会调用，签名务必保持）

| 函数 | 签名 | 返回关键字段 |
|---|---|---|
| 简历解析 | `resume_parser.parse_resume(resume_text: str) -> dict` | name/education/projects/skills/internships/summary |
| 岗位画像 | `job_profiler.build_job_profile(job) -> dict` | title/core_skills/capability_dimensions/interview_focus/suggested_rounds |
| 面试编排 | `interview_agent.plan_interview(job_profile, resume_profile, categories=None) -> list[dict]` | 每轮 `{round_no, category, question, expected_points, evidence}` |
| 追问 | `interview_agent.generate_followup(interview_context, job_profile) -> dict` | `{question, reason}` |
| 评分 | `interview_agent.evaluate_answer(question, answer, category, expected_points, evidence) -> dict` | `{score(0-100), feedback, improvement, missing_points, evidence}` |
| 评分汇总 | `scoring.aggregate(scores) -> dict` | `{total_score, dimension_scores, answer_count}` |
| 报告 | `report.generate_report(interview_data) -> dict` | `{total_score, level, dimension_scores, overall_comment, strengths, weaknesses, suggestions, hire_recommendation, answers}` |
| SQL查询 | `sql_agent.ask(question: str) -> dict` | `{question, sql, columns, rows, explanation}` |
| 语音转写 | `voice.transcribe(audio_path) -> str` | 文本 |
| 检索 | `rag.knowledge_base.search(query, top_k=5) -> list[dict]` | `[{id, title, content, source, score, meta}]` |

## 6. 分阶段任务

### 第一阶段（第1周）
1. 检查 `utils/llm.py`，给 `chat()` 加 1 次重试 + 30s 超时；`chat_json()` 增加错误提示。
2. 完善 5 类提示词模板（`rag/prompts/`）：自我介绍/项目深挖/专业能力/行为面试/反问，每个环节要有"出题"和"评分"两套模板，变量与 `interview_agent.py` 中 `.format(**context)` 的字段对齐。
3. 完善 `resume_parser.py`：增强规则提取（学历、技能词库、邮箱手机），跑通"规则+LLM 混合"。

### 第二阶段（第2周）
4. 完善 `job_profiler.py` 与 `interview_agent.plan_interview()`：能按岗位生成 5 个环节的问题序列，并附带知识库检索依据 `evidence`。
5. 实现 `generate_followup()`：基于前几轮问答生成追问。
6. 在 `data/knowledge/` 补充至少 3 个岗位 JD、10 道以上题目、评分标准；用 `python -m backend.scripts.seed_knowledge` 验证索引能构建。

### 第三阶段（第3周）
7. 完善 `evaluate_answer()`：按环节调用对应评分模板，返回结构化评分；保证降级评分合理。
8. 完善 `report.generate_report()`：输出含雷达图所需维度分、优缺点、录用建议的完整报告。
9. 实现 `sql_agent.ask()`：用 LLM 生成 SQL，加"仅允许 SELECT + 危险关键字拦截"，能回答如"各岗位面试平均分"。
10. 实现 `voice.transcribe()`：安装 `faster-whisper` 后支持中文转写；未安装时优雅返回空串。

### 第四阶段（第4周）
11. 配合成员B 联调：确保 `plan_interview → answer → evaluate → report` 全链路无异常。
12. 写单元测试：`backend/tests/test_services.py`，用 mock 的 LLM 返回值测试各函数降级逻辑。

## 7. 验收标准

- [ ] 无 DEEPSEEK_API_KEY 时，所有服务函数仍能返回合理结果（降级）
- [ ] 有 key 时，`plan_interview` 能生成 5 环节问题，`evaluate_answer` 能返回 0-100 评分
- [ ] `sql_agent.ask("各岗位平均分")` 能返回 SQL 与数据
- [ ] `pytest backend/tests/` 全绿
- [ ] 接口签名与 `docs/计划与分工.md` 第 5.2 节一致

## 8. 给 AI 助手的工作方式建议

1. 开工先读 `CLAUDE.md`、`docs/计划与分工.md` 第 4 节、第 5.2 节。
2. 每个函数实现前，先列出"函数签名 + 入参示例 + 返回示例"让你确认。
3. 改完跑 `python -m compileall backend` 检查语法，再跑 `pytest backend/tests/`。
4. 不要动 `models/`、`api/`、`frontend/` 下的任何文件。
