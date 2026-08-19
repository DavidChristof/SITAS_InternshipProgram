"""SITAS 后端入口。运行：uvicorn backend.app.main:app --reload"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  确保所有 ORM 模型被注册
from .api import admin, candidate, interview, knowledge
from .config import FRONTEND_DIR, settings
from .database import Base, engine
from .rag import knowledge_base

# ===== 应用工厂 =====


def create_app() -> FastAPI:
    # 启动时建表（正式开发可迁移到 alembic）
    Base.metadata.create_all(bind=engine)
    # 启动时灌入 RAG 知识库索引（面试出题/评分依赖其检索依据）
    knowledge_base.build_index()

    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # 业务路由
    app.include_router(candidate.router)
    app.include_router(admin.router)
    app.include_router(interview.router)
    app.include_router(knowledge.router)

    # 静态资源与前端入口
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
