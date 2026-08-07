"""全局配置。所有环境变量在 .env 中配置，禁止在代码里写死密钥。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 = backend/app/config.py 向上三级 = SITAS/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SITAS 智能面试官与人才评估系统"
    debug: bool = True

    # ===== DeepSeek / LLM =====
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    # 预留：本地语义检索嵌入模型（成员A如需升级 RAG 可配置，例如 bge-small-zh）
    embedding_model: str = ""

    # ===== 数据库 =====
    database_url: str = f"sqlite:///{(DATA_DIR / 'sitas.db').as_posix()}"

    # ===== 上传目录（简历 / 语音）=====
    upload_dir: str = str(DATA_DIR / "uploads")


settings = Settings()

# 确保必要目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
