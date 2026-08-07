"""把 data/knowledge 下的文档灌入检索器（打印统计）。

用法（项目根目录执行）：
    python -m backend.scripts.seed_knowledge
（服务启动时也会自动构建一次索引，见 main.py / knowledge_base.build_index）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.rag.knowledge_base import build_index


def main() -> None:
    count = build_index()
    print(f"[seed_knowledge] 知识库构建完成，共 {count} 条文档")


if __name__ == "__main__":
    main()
