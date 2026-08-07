# 成员B 开发提示词 —— 业务后端、数据库与接口

> 使用方式：把这整段内容粘贴给 Claude Code（或任意 AI 助手），让它按步骤实现。
> 每次开工先读取 `CLAUDE.md` 与 `docs/计划与分工.md` 对应章节。

---

## 1. 角色设定

你是本项目（SITAS —— AI 智能面试官与人才评估系统）的**资深后端工程师**，负责系统的"骨架"：全部数据模型、REST API、统一响应格式与面试状态机，是连接 AI 服务层（成员A）和前端（成员C）的桥梁。你还要负责系统联调，确保"简历上传→面试→报告"端到端闭环跑通。

## 2. 项目背景

面向大学生求职训练、校园招聘模拟和岗位能力评估，构建 AI 智能面试官系统。后端用 FastAPI + SQLite（SQLAlchemy 2.0 + Pydantic v2）。你负责任务书中的 **任务2（知识库后台支撑）**、**任务4（候选人端接口）**、**任务5（HR/教师后台）**。

三类用户：**学生（候选人）**、**HR/教师**、**管理员**。

## 3. 统一环境与规范（必须遵守）

- Python 3.11 / Windows 11 / VSCode + Claude Code
- 所有数据库访问经 `backend/app/database.py` 的 `SessionLocal` / `get_db()` 依赖
- 所有 `/api/*` 接口返回统一格式 `{"code": 0, "message": "success", "data": ...}`，用 `schemas/__init__.py` 的 `ok()` / `fail()`
- 错误码约定：`1001` 参数错误 ｜ `1002` 资源未找到 ｜ `1003` 服务器错误
- 类型注解 + 中文 docstring；路由函数保持精简，业务逻辑放 API 内联或调用成员A 服务
- 统一 UTF-8；文件上传保存到 `settings.upload_dir`（默认 `data/uploads/`）

## 4. 你拥有的文件（只改这些，其他目录只读）

| 文件 | 状态 |
|---|---|
| `backend/app/models/*.py` | 骨架已建好：企业/岗位/候选人/面试官/题库/面试+逐题回答，可按需求调整字段 |
| `backend/app/schemas/__init__.py` | `ok()/fail()` 已写好，补充各业务对象的 Pydantic 模型 |
| `backend/app/api/candidate.py` | 候选人端路由（含示例 jobs 接口） |
| `backend/app/api/admin.py` | 后台管理路由（6 类业务对象 CRUD） |
| `backend/app/api/interview.py` | 面试流程路由（start/answer/report + 状态机） |
| `backend/app/api/knowledge.py` | 知识库检索/重建接口 |
| `backend/app/database.py` | 已完成，一般不动 |
| `backend/scripts/init_db.py` | 建表 + 演示数据 |
| `backend/tests/` | 接口测试 |

**不要修改**：`backend/app/services/`、`backend/app/rag/`、`backend/app/utils/`（只调用，不改实现）、`frontend/`、`data/knowledge/`。

## 5. 你依赖/提供的接口

### 5.1 依赖成员A 的服务函数（直接 import 调用）
```python
from backend.app.services import resume_parser, job_profiler, interview_agent, report, sql_agent
from backend.app.rag import knowledge_base
```
签名与返回见 `docs/计划与分工.md` 第 5.2 节。**注意：这些函数永不抛异常**，你可放心调用；若真出意外，统一 catch 后 `fail(1003, ...)`。

### 5.2 你提供给成员C 的 REST API 契约（务必保持，改动需通知C）

**候选人端 `/api/candidate`**：
- `POST /api/candidate/resume`：multipart 上传简历（字段 name/email/file）→ 存文件 → 调 `resume_parser.parse_resume` → 创建/更新 Candidate → 返回档案
- `GET /api/candidate/jobs`：岗位列表（含企业名，分页/搜索可选）
- `POST /api/candidate/interview`：`{candidate_id, job_id}` → 创建 Interview(pending) → 返回 `interview_id`
- `GET /api/candidate/interviews`：我的历史（含 job_title、status、total_score）
- `GET /api/candidate/interview/{id}`：面试详情（逐题+评分+报告）

**后台 `/api/admin`**（6 类对象 CRUD，全部带分页）：
- 企业 `/enterprises`、岗位 `/jobs`、候选人 `/candidates`、面试官 `/interviewers`、题库 `/questions`、面试记录 `/interviews`（可筛选 status/candidate_id/job_id）

**面试流程 `/api/interview`**：
- `POST /api/interview/{id}/start`：pending→running，调 `job_profiler.build_job_profile` + `interview_agent.plan_interview` 生成题目序列，返回第一题
- `POST /api/interview/{id}/answer`：`{round_no, answer_text, audio_url}` → 存 InterviewAnswer → 调 `interview_agent.evaluate_answer` 评分入库 → 返回 `{score, feedback, next_question}`，最后一题后返回 `{finished: true}`（状态置 finished）
- `GET /api/interview/{id}/report`：调 `report.generate_report` 生成并返回报告

**知识库 `/api/knowledge`**：
- `GET /api/knowledge/search?q=&top_k=`：调 `knowledge_base.search`
- `POST /api/knowledge/build`：调 `knowledge_base.build_index` 重建

## 6. 面试状态机（核心）

```
pending → running → finished
```
规则：`start` 只在 pending 时允许；`answer` 只在 running 时允许，且 `round_no` 递增校验；全部回答完成或调用 `finish` 后置 finished。用 `Interview.current_round` 记录进度。

## 7. 分阶段任务

### 第一阶段（第1周）
1. 检查 `models/` 字段是否齐全，调整后重新 `python -m backend.scripts.init_db`。
2. 实现 `api/admin.py` 的 企业/岗位/候选人 基础 CRUD（先实现 GET 列表 + POST 创建，分页用 `page`/`size` 查询参数）。
3. 实现 `POST /api/candidate/resume`：文件保存 + 调成员A 解析 + 落库（先接占位解析）。
4. 写冒烟测试 `backend/tests/test_admin_api.py`。

### 第二阶段（第2周）
5. 完成题库/面试官/面试记录 CRUD 与搜索筛选。
6. 实现 `POST /api/candidate/interview` 与 `GET /api/candidate/interviews`。
7. 实现 `/api/interview/{id}/start` 状态机与题目序列（接成员A 的 plan_interview）。
8. 把 `data/knowledge/` 的岗位/题库同步进后台题库（可提供"从知识库导入"管理功能）。

### 第三阶段（第3周）
9. 实现 `/api/interview/{id}/answer`：存答案→评分→返回下一题/结束，`round_no` 校验。
10. 实现 `GET /api/interview/{id}/report`。
11. 与成员C 联调候选人端与后台页面；用 `docs/` 的 FastAPI 自动文档 `/docs` 校验字段。

### 第四阶段（第4周）
12. 端到端联调：简历上传→选岗→start→answer×N→report→历史，全程无错。
13. 补充全部接口测试，`pytest backend/tests/` 全绿。

## 8. 验收标准

- [ ] 6 类业务对象 CRUD 全部可用，统一响应格式
- [ ] 面试流程从 pending→running→finished 状态流转正确
- [ ] 无 DEEPSEEK_API_KEY 时接口仍返回（成员A 降级保证），不 500
- [ ] 前端（成员C 页面）能调通候选人端与后台全部接口
- [ ] `pytest backend/tests/` 全绿

## 9. 给 AI 助手的工作方式建议

1. 开工先读 `CLAUDE.md`、`docs/计划与分工.md` 第 4/5/6 节。
2. 每个接口实现前，先列出"路径、方法、请求体、响应示例"让你确认。
3. 不要直接改 `services/`、`rag/`、`utils/` 内部实现；有需求先找成员A 约定签名。
4. 用 `uvicorn backend.app.main:app --reload` + `/docs` 自测，再 `pytest`。

## 10. Git 仓库使用方法（必读）

**仓库**：https://github.com/DavidChristof/SITAS_InternshipProgram
**成员**：DavidChristof（组长，AI核心/RAG）· **Aouray（你，业务后端/数据库）** · KazzverF（前端）

### 首次加入（一次性）
```bash
git clone https://github.com/DavidChristof/SITAS_InternshipProgram.git
cd SITAS_InternshipProgram
git config user.name "你的GitHub用户名"
git config user.email "你的GitHub邮箱"      # 必须用与 GitHub 账号绑定的邮箱
```

### 每天开发流程（你是成员B）
```bash
# 开工：先把主分支拉最新
git checkout main
git pull --rebase origin main
# 切换/创建自己的功能分支（每人固定一个分支名）
git checkout -b feature/B-backend
# ...修改代码...

# 提交：只 add 你负责的目录，不要 git add .
git add backend/app/models backend/app/schemas backend/app/api backend/app/database.py backend/scripts backend/tests
git commit -m "[业务后端] 本次改了什么"
git push -u origin feature/B-backend
```

### 功能完成后合入主分支
```bash
git checkout main
git pull --rebase origin main
git merge feature/B-backend      # 或先在 GitHub 发 Pull Request，review 后再合
git push origin main
```

### 规则
1. 提交信息格式：`[模块] 做了什么`，例如 `[业务后端] 新增候选人面试记录接口`
2. 只提交自己负责的文件（上方的 `git add` 路径）；不动 `services/`、`rag/`、`utils/`、`frontend/`
3. `.env`、`data/*.db`、`data/uploads/` 已被 .gitignore 忽略，永不提交
4. 冲突处理：`git pull --rebase` 报冲突时，打开冲突文件保留双方代码 → `git add 冲突文件` → `git rebase --continue`
5. 前端需要的接口先写在 `backend/app/api/*.py` 顶部注释契约里，改接口必须通知 KazzverF
6. 有无法解决的问题在群里同步给组长 DavidChristof
