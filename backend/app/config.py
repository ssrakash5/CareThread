from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://carethread:carethread@localhost:5434/carethread"
    storage_dir: str = str(Path(__file__).resolve().parents[2] / "storage" / "artifacts")
    embedding_dim: int = 128

    class Config:
        env_prefix = "CARETHREAD_"


settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
