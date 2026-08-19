# SITAS 代码版本管理问题说明（给组长 A）

> 成员B 在开始第三阶段前检查仓库时发现的问题，需要组长协调处理。
> 检查时间：2026-08-19

---

## 一句话结论

三位成员都在各自的功能分支上开发，但 **`main` 一直停在最初的骨架提交，没有任何分支合并回 `main`**。导致成员B 开发第三阶段时，拿不到成员A（组长）的最新服务层代码。

---

## 一、当前仓库状态

| 分支 | 最新提交 | 相对 main | 是否已合入 main |
|---|---|---|---|
| `main` | `94eb80e`（初始骨架提交） | — | 基准，**从未被更新** |
| `feature/A-ai-core`（组长） | `15fcbc2` | **+8 提交** | ❌ 未合并 |
| `feature/C-frontend` | `c555e3e` | +4 提交 | ❌ 未合并 |
| `feature/B-backend`（我） | `4d6641b` | +2 提交 | ❌ 未合并 |

即：`main` 仍停留在项目骨架，A、B、C 三人的工作都还各自待在自己的分支上。

---

## 二、具体问题

### 问题 1：main 未合并任何成员代码

按照 `docs/计划与分工.md` §7 的协作流程（"完成后合并回 main"），各成员完成功能后应把分支合回 `main`。目前三个功能分支都领先 `main`，但都未合并。

**影响**：三人各写各的，缺少一条统一的集成基线，联调时容易"我的代码里没有你的最新改动"。

### 问题 2：成员B 第三阶段依赖成员A 的最新服务层，但拿不到

成员B 的第三阶段要实现「评分 + 报告」，需要调用 A 的：
- `interview_agent.evaluate_answer(...)`
- `scoring.aggregate(...)`
- `report.generate_report(...)`

但 B 的 `feature/B-backend` 是从 **`main`（骨架版）** 拉出来的，所以 B 本地拿到的是**旧骨架版**服务层，而不是 A 在 `feature/A-ai-core` 上的最新版（比骨架版多了 **10 个文件 / +718 行** 增强）。

### 问题 3（关键）：`utils/llm.py` 的超时修复只在 A 的分支上

A 的提交 `f3591a4`「增强 llm.py：超时+重试+JSON健壮解析」给 LLM 调用加了**超时 + 重试**。而 B 分支（=main 骨架）的 `llm.py` **没有超时设置**（openai SDK 默认超时 600 秒）。

**风险**：如果 DeepSeek 网络慢或不可达，评分/报告接口可能**长时间卡住**（而非快速降级），影响端到端演示的「无 key 也能跑通」承诺。

---

## 三、文件重叠情况（合并无冲突）

两个分支改的文件**完全不重叠**，合并不会有冲突：

| 成员 | 改动的目录 |
|---|---|
| 成员B（我） | `backend/app/models/`、`backend/app/schemas/`、`backend/app/api/`、`backend/tests/` |
| 成员A（组长） | `backend/app/services/`、`backend/app/rag/`、`backend/app/utils/`、`data/knowledge/` |

---

## 四、建议处理方案（请组长选择其一）

### 方案 1（推荐，符合规范）

组长把 `feature/A-ai-core` 合并到 `main`（因为 A 是 B、C 的依赖方，A 应先合），然后通知 B、C 各自同步：

```bash
# 组长执行
git checkout main
git pull --rebase origin main
git merge feature/A-ai-core
git push origin main

# B 和 C 各自执行
git checkout 自己的分支
git pull --rebase origin main
```

### 方案 2（快速，不依赖组长 merge）

直接允许 B 把 A 的分支合并进自己的分支：

```bash
# 成员B 执行
git checkout feature/B-backend
git merge origin/feature/A-ai-core
git push
```

> 由于文件零重叠，两种方案都不会有冲突。

---

## 五、对成员B 的影响

- B 的第三阶段（`answer` 评分 + `report` 报告）需要依赖 A 的最新服务层。
- **B 会暂停第三阶段开发，等 A 处理完上述合并问题后再继续。**
- 处理完成后请通知 B，B 会 `git pull`/`merge` 同步最新代码，再开始第三阶段。
