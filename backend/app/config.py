from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/briefwave.db"
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # External APIs (forwarded from .env)
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""
    CROSSREF_MAILTO: str = ""
    KCI_API_KEY: str = ""
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = ""
    PAPAGO_CLIENT_ID: str = ""
    PAPAGO_CLIENT_SECRET: str = ""
    LIBRETRANSLATE_URL: str = ""
    LIBRETRANSLATE_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
