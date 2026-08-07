# 示例知识库说明

本目录存放 RAG 检索用的文档，按类别分子目录（成员A 提供格式规范，三人共同补充内容）：

| 子目录 | 内容 | 来源 |
|---|---|---|
| `jobs/` | 岗位 JD（含任职要求、技能） | 成员A/B 从后台岗位同步 |
| `questions/` | 面试题库（含评分要点、优秀回答） | 成员B 后台题库录入 |
| `companies/` | 企业资料（规模、文化、业务） | 成员B 后台企业录入 |
| `standards/` | 评分标准与规则 | 成员A 制定 |
| `samples/` | 优秀回答样例 | 成员A/指导教师 |

## 文件格式

支持 `.json` / `.md` / `.txt`。

JSON 格式统一为：

```json
{
  "title": "文档标题",
  "content": "正文内容……",
  "meta": { "任意": "附加信息，如 category: technical" }
}
```

> 说明：`knowledge_base.build_index()` 在服务启动时自动把本目录文档灌入 BM25 检索器；
> 也可以运行 `python -m backend.scripts.seed_knowledge` 手动重建。成员只需往对应子目录放文件即可。
