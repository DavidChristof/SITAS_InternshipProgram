"""知识库构建与对外检索接口（成员A维护）。

数据来源：data/knowledge/ 下按类别存放文档：
    jobs/       岗位 JD（.json/.md/.txt）
    questions/  面试题库
    companies/  企业资料
    standards/  评分标准
    samples/    优秀回答样例
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..config import DATA_DIR
from .retriever import retriever

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
# 子目录 -> 来源标签
_SUBDIRS: dict[str, str] = {
    "jobs": "岗位JD",
    "questions": "面试题库",
    "companies": "企业资料",
    "standards": "评分标准",
    "samples": "优秀回答",
}


def load_json_docs(subdir: str, source: str) -> list[dict]:
    """读取某子目录下的 .json/.md/.txt 文件为文档。"""
    docs: list[dict] = []
    d = KNOWLEDGE_DIR / subdir
    if not d.exists():
        return docs
    for fp in sorted(d.iterdir()):
        if fp.suffix == ".json":
            data = json.loads(fp.read_text(encoding="utf-8"))
            docs.append(
                {
                    "id": f"{subdir}/{fp.stem}",
                    "title": data.get("title", fp.stem),
                    "content": data.get("content", ""),
                    "source": source,
                    "meta": data.get("meta", {}),
                }
            )
        elif fp.suffix in (".md", ".txt"):
            docs.append(
                {
                    "id": f"{subdir}/{fp.stem}",
                    "title": fp.stem,
                    "content": fp.read_text(encoding="utf-8"),
                    "source": source,
                    "meta": {},
                }
            )
    return docs


def build_index() -> int:
    """重建全部知识库索引。服务启动时调用一次；管理员可手动重灌。返回文档条数。"""
    docs: list[dict] = []
    for subdir, source in _SUBDIRS.items():
        docs.extend(load_json_docs(subdir, source))
    retriever.add_documents(docs)
    logger.info("[knowledge_base] 已灌入 %d 条知识文档", len(docs))
    return len(docs)


def search(query: str, top_k: int = 5) -> list[dict]:
    """对外检索接口。供 services/interview_agent.py 与 api/knowledge.py 使用。"""
    return retriever.retrieve(query, top_k)
