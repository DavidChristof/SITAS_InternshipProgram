# SITAS —— AI 智能面试官与人才评估系统

面向大学生求职训练、校园招聘模拟和岗位能力评估场景的 AI 面试官系统。
覆盖：简历解析、岗位知识库检索、结构化面试、多轮追问、回答评分、反馈报告、面试记录、后台题库管理。

> 三位成员的详细分工、开发提示词、接口契约见 [docs/计划与分工.md](docs/计划与分工.md)。

---

## 一、技术栈与环境（统一约定）

| 项 | 约定 |
|---|---|
| 语言 | Python 3.11 |
| 系统 | Windows 11 |
| 开发工具 | VSCode + Claude Code（对接 DeepSeek API） |
| Web 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite（文件：`data/sitas.db`） |
| ORM | SQLAlchemy 2.0 |
| 大模型 | DeepSeek API（OpenAI 兼容接口，`openai` SDK 调用） |
| RAG 检索 | BM25（`jieba` 分词 + `rank-bm25`，离线可用，无需向量库） |
| 前端 | Vue 3（CDN）+ Bootstrap 5，由 FastAPI 托管静态页，无 Node 构建 |
| 语音 | 预留（`faster-whisper` 本地转写，可选） |
| 版本控制 | Git（建议建 GitHub/Gitee 私有仓库） |

## 二、目录结构

```
SITAS/
├── README.md                 # 本文件
├── CLAUDE.md                 # Claude Code 协作规范（每位成员必读）
├── requirements.txt          # 依赖
├── .env.example              # 环境变量模板（复制为 .env 填入密钥）
├── .gitignore
├── docs/
│   ├── 计划与分工.md          # 三人分工、进度、接口契约
│   ├── 任务书原文.txt         # 任务书原始内容
│   └── 提示词/               # 三人各自的 AI 助手提示词
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 全局配置
│   │   ├── database.py       # SQLAlchemy 引擎/会话
│   │   ├── models/           # ORM 模型（成员B）
│   │   ├── schemas/          # Pydantic 模型 + 统一响应格式（成员B）
│   │   ├── api/              # REST 路由（成员B）
│   │   ├── services/         # 业务服务层（成员A）
│   │   ├── rag/              # RAG 检索 + 提示词模板（成员A）
│   │   └── utils/            # LLM 封装等工具（成员A）
│   ├── scripts/              # init_db / seed_knowledge（成员B/A）
│   └── tests/                # pytest 测试
├── frontend/
│   ├── index.html            # 前端入口（面试大厅）
│   └── static/
│       ├── css/style.css
│       └── js/               # api / main / candidate / admin / interview
└── data/
    └── knowledge/            # 示例知识库（JD/题库/企业/评分标准/优秀回答）
```

## 三、快速开始

```bash
# 1. 创建虚拟环境并安装依赖
cd D:/26实习/SITAS
python -m venv .venv
.venv\Scripts\activate            # PowerShell 下激活
pip install -r requirements.txt

# 2. 配置密钥
copy .env.example .env           # 然后编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 初始化数据库（建表 + 演示数据）
python -m backend.scripts.init_db

# 4. 启动服务（在项目根目录运行）
uvicorn backend.app.main:app --reload --port 8000

# 5. 访问
#    前端页面  http://127.0.0.1:8000/
#    API 文档  http://127.0.0.1:8000/docs
```

## 四、测试

```bash
pytest backend/tests/ -v
```

## 五、Git 协作约定

- 每位成员在自己负责的目录/文件下开发，使用功能分支，合并前先拉最新 `main`。
- 提交信息建议：`[模块] 做了什么`，如 `[候选人API] 新增简历上传接口`。
- `.env` 一律不入库；数据库文件、上传文件不入库。
