"""基于 BM25 的中文检索器（成员A维护）。

选型说明：DeepSeek 官方暂未开放 embedding 接口，故本项目先用 BM25（jieba 分词 + rank_bm25）
做词法检索，零外部服务、离线可用，足以支撑学生项目。后续若接入 bge/text2vec 等本地嵌入模型，
替换本模块内部实现即可，保持 retrieve(query, top_k) 接口不变。
"""
from __future__ import annotations

import jieba
from rank_bm25 import BM25Okapi


class Retriever:
    """内存版 BM25 检索器。服务启动时从 data/knowledge 加载文档构建索引。"""

    def __init__(self) -> None:
        self._docs: list[dict] = []  # [{id, title, content, source, meta}]
        self._tokenized: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    @property
    def doc_count(self) -> int:
        return len(self._docs)

    def add_documents(self, docs: list[dict]) -> None:
        """docs: [{id, title, content, source, meta}]

        title 一并参与分词索引，保证"行为面试""岗位JD"等标题关键词也能被检索命中。
        """
        self._docs.extend(docs)
        self._tokenized = [list(jieba.cut(f"{d.get('title', '')} {d['content']}")) for d in self._docs]
        self._bm25 = BM25Okapi(self._tokenized)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """按相关度返回命中文档，附带 score 与检索依据说明。"""
        if not self._bm25 or not self._docs:
            return []
        tokens = list(jieba.cut(query))
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        hits = [
            {**self._docs[i], "score": round(float(scores[i]), 4)}
            for i in ranked
            if scores[i] > 0
        ]
        return hits


# 模块级单例，供知识库构建与检索共用
retriever = Retriever()
