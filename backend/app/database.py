"""SQLAlchemy 引擎与会话。统一在此处管理数据库连接。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args, echo=settings.debug)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI 依赖：请求级数据库会话。所有路由通过此依赖取 session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
