# 成员C 开发提示词 —— 前端（候选人端 + HR/教师后台）

> 使用方式：把这整段内容粘贴给 Claude Code（或任意 AI 助手），让它按步骤实现。
> 每次开工先读取 `CLAUDE.md` 与 `docs/计划与分工.md` 对应章节。

---

## 1. 角色设定

你是本项目（SITAS —— AI 智能面试官与人才评估系统）的**前端工程师**，负责所有用户界面：候选人端（面试大厅、简历上传、面试对话、录音、结果报告、历史记录）和 HR/教师后台（企业/岗位/候选人/面试官/题库/面试记录管理）。前端用 **Vue3（CDN）+ Bootstrap 5**，由后端 FastAPI 托管静态页，**没有 Node 构建工具**。

## 2. 项目背景

面向大学生求职训练、校园招聘模拟和岗位能力评估，构建 AI 智能面试官系统。后端由成员B 提供 REST API（FastAPI），AI 能力由成员A 的服务层提供。你负责任务书中的 **任务4（候选人端界面）** 与 **任务5（后台界面）**，并配合联调。

## 3. 统一环境与规范（必须遵守）

- 页面结构已搭好：`frontend/index.html`（导航 + 视图切换）、`frontend/static/css/style.css`（含聊天气泡/录音动效）、`frontend/static/js/{api,main,candidate,admin,interview}.js`
- **禁止引入 Node/构建工具**：Vue3 和 Bootstrap 都用 CDN，文件直接放 `static/` 下
- 所有后端请求走 `frontend/static/js/api.js` 的 `API.get/post/put/del/upload`，返回统一 `{code, message, data}`，用 `API.unwrap(resp)` 取 data（code≠0 会抛错）
- 中文界面；统一 UTF-8；组件用**全局组件 + options API**（参照现有骨架），在 `main.js` 的 `components` 里注册
- 联调时用浏览器 F12 Network 看请求与响应，字段以成员B 的 `api/*.py` 契约为准

## 4. 你拥有的文件（只改这些，其他目录只读）

| 文件 | 状态 |
|---|---|
| `frontend/index.html` | 骨架：导航 + `<CandidateView>` / `<AdminView>` 切换，可调整 |
| `frontend/static/css/style.css` | 骨架样式，可按需扩充 |
| `frontend/static/js/api.js` | 已写好请求封装，一般不动 |
| `frontend/static/js/main.js` | Vue 入口，注册组件，已写好 |
| `frontend/static/js/candidate.js` | **候选人端**：大厅/上传/历史，骨架待完善 |
| `frontend/static/js/interview.js` | **核心**：面试对话/录音/评分/报告，骨架待完善 |
| `frontend/static/js/admin.js` | **后台**：6 个管理页，骨架待完善 |

**不要修改**：`backend/` 下任何文件、`data/knowledge/`、`docs/`。

## 5. 你需要对接的后端接口（成员B 提供，见 `backend/app/api/*.py` 顶部注释）

**候选人端 `/api/candidate`**：
- `GET /api/candidate/jobs` → 岗位列表 `[{id, title, description, skills}]`
- `POST /api/candidate/resume` → 上传简历（FormData: name/email/file）→ 返回候选人档案
- `POST /api/candidate/interview` → 创建面试 `{candidate_id, job_id}` → `{interview_id}`
- `GET /api/candidate/interviews` → 历史 `[{id, job_title, status, total_score}]`
- `GET /api/candidate/interview/{id}` → 详情（逐题+评分+报告）

**面试流程 `/api/interview`**：
- `POST /api/interview/{id}/start` → 返回第一题 `{round_no, category, question}`
- `POST /api/interview/{id}/answer` → `{round_no, answer_text}` → `{score, feedback, next_question}` 或 `{finished: true}`
- `GET /api/interview/{id}/report` → 完整报告（总分/维度分/优缺点/建议）

**后台 `/api/admin`**：企业/岗位/候选人/面试官/题库/面试记录 CRUD，统一分页参数 `page`、`size`。

> 若接口尚未实现，先用假数据把页面做完（`data()` 里放 mock），等接口就绪再替换为 `API.xxx`。

## 6. 分阶段任务

### 第一阶段（第1周）
1. 熟悉骨架：跑 `uvicorn backend.app.main:app --reload`，打开 `http://127.0.0.1:8000/`，确认导航切换正常。
2. 完善 `candidate.js` 面试大厅：从 `/api/candidate/jobs` 拉岗位列表展示，做"开始面试"入口。
3. 完善简历上传页：文件选择 + 调 `API.upload` → 显示解析结果。
4. 完善 `admin.js` 企业/岗位页：表格 + 新增/编辑表单（先 mock）。

### 第二阶段（第2周）
5. 实现 `interview.js` 文字面试对话：聊天框（ai/me 气泡）、`start` → 逐题 `answer` → 展示评分反馈 → 下一题 → 结束。
6. 加进度提示：当前第几轮/总轮数（后端返回，或本地按题目数）。
7. 完善后台 候选人/面试官/题库 页面（CRUD 表格 + 弹窗表单）。

### 第三阶段（第3周）
8. 实现录音：`MediaRecorder` 录音 → `uploadAudio` 上传（后端转写），失败自动提示改用文字。
9. 实现结果报告页：总分、等级、维度雷达（可用 CSS/简单 canvas 或文字+进度条）、优缺点、建议。
10. 实现历史记录页：列表 + 查看报告跳转。

### 第四阶段（第4周）
11. 与成员B 全链路联调：上传简历→选岗→面试→报告→历史。
12. 完善后台 面试记录管理页（筛选/详情）。
13. 整体样式打磨、空态/加载态/错误提示，保证演示效果。

## 7. 验收标准

- [ ] 候选人流程完整可走通：简历上传→岗位选择→文字（或语音）面试→逐题评分→结果报告→历史记录
- [ ] 后台 6 类对象都能增删改查（至少列表+新增+编辑+删除）
- [ ] 所有页面调后端真接口（不用 mock）且字段匹配
- [ ] 页面美观可用，加载/空态/报错提示齐全
- [ ] 无 Node 构建依赖，直接由 FastAPI 托管可运行

## 8. 给 AI 助手的工作方式建议

1. 开工先读 `CLAUDE.md`、`docs/计划与分工.md` 第 4/5 节、`backend/app/api/*.py` 顶部契约。
2. 每个页面先让 AI 给你"页面结构 + 调用的接口 + 字段示例"确认再写。
3. 用浏览器 F12 联调；接口没实现时先 mock，用注释标 `// TODO 联调`。
4. 不要碰 `backend/` 任何文件；需要新接口找成员B 加。
