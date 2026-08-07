# CLAUDE.md —— 项目协作规范（所有成员 + AI 助手必须遵守）

本文件是 SITAS 项目对 Claude Code / AI 助手的统一约定。每次开始开发前，先读取本文件与 `docs/计划与分工.md`。

## 1. 项目定位

AI 智能面试官与人才评估系统（校园招聘模拟 + 岗位能力评估），后端 FastAPI + SQLite，AI 核心调 DeepSeek API，前端 Vue3(CDN)+Bootstrap。

## 2. 角色与目录所有权（重要，防止互相覆盖代码）

| 成员 | 拥有目录/文件 | 不要修改 |
|---|---|---|
| 成员A（AI核心与RAG） | `backend/app/services/`、`backend/app/rag/`、`backend/app/utils/` | 其他目录 |
| 成员B（业务后端与数据库） | `backend/app/models/`、`backend/app/schemas/`、`backend/app/api/`、`backend/app/database.py`、`backend/scripts/` | `services/`、`rag/`、`utils/` 的内部实现 |
| 成员C（前端） | `frontend/` 全部 | 后端任何文件 |

> 以上为**所有权约定**，但接口契约需要双方配合时，可通过 PR 评审协商修改。修改跨域文件前必须在代码评审中说明理由。

## 3. 统一环境

- Python 3.11 / Windows 11 / VSCode + Claude Code（DeepSeek API）
- FastAPI + Uvicorn、SQLAlchemy 2.0、SQLite、Pydantic v2、openai SDK（base_url=`https://api.deepseek.com`）
- 前端 Vue3 CDN + Bootstrap 5，**禁止引入 Node 构建工具**
- 所有密钥放 `.env`（见 `.env.example`），**禁止把密钥写死在代码里**，用 `backend/app/config.py` 读取

## 4. 编码规范

- 统一 UTF-8 编码；注释和文档用中文
- 每个函数写类型注解 + docstring（说明入参、返回、异常）
- 命名：变量/函数 `snake_case`，类 `PascalCase`，URL 用 kebab-case
- 所有 LLM 调用必须经 `backend/app/utils/llm.py`（`chat` / `chat_json`），**禁止直接 new OpenAI client**
- 所有数据库访问必须经 `database.py` 的 `SessionLocal` / `get_db()`
- 服务层函数不得直接 `print` 业务结果，日志用 `logging`
- 不确定怎么写时，参考同目录已有文件的风格

## 5. 统一 API 响应格式（成员B 提供，成员C 依赖）

所有 `/api/*` 接口返回统一 JSON：

```json
{ "code": 0, "message": "success", "data": { } }
```

- 成功：HTTP 200，`code=0`
- 业务失败：HTTP 200 或对应状态码，`code` 为业务错误码（如 1001 参数错误 / 1002 未找到 / 1003 服务器错误），`message` 给中文说明
- `schemas/__init__.py` 中已提供 `ok()` / `fail()` 辅助函数，直接使用

## 6. 运行方式

```bash
# 项目根目录（D:/26实习/SITAS）
uvicorn backend.app.main:app --reload --port 8000
```

- 前端静态页由 FastAPI 托管：`GET /` 返回 `frontend/index.html`，静态资源在 `/static/`
- 初始化数据库：`python -m backend.scripts.init_db`
- 测试：`pytest backend/tests/ -v`

## 7. Git 约定

- 功能分支开发，如 `feature/interview-api`，完成后再合并 `main`
- 提交前 `git pull --rebase`，解决冲突优先保留双方最新代码
- `.env`、`data/*.db`、`data/uploads/` 不入库

## 8. 给 Claude Code 的建议使用姿势

- 每次开工先让它读 `CLAUDE.md` 和 `docs/计划与分工.md` 中你自己的章节
- 改动前先让它"列出本次要创建/修改的文件清单"给你确认
- 完成后让它跑 `pytest` 与启动冒烟，确保不破坏其他人代码
