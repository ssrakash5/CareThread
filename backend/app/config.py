from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://carethread:carethread@localhost:5434/carethread"
    storage_dir: str = str(_BACKEND_DIR.parent / "storage" / "artifacts")

    # AI provider: "bedrock" (Claude + Titan embeddings via Amazon Bedrock) or
    # "local" (deterministic regex/hash stand-ins, no network). Every Bedrock
    # call falls back to the local implementation on error so ingestion never
    # hard-fails.
    ai_provider: str = "local"
    aws_region: str = "us-east-1"
    # Optional explicit AWS credentials. Leave empty to use the standard AWS
    # credential chain (env vars, ~/.aws/credentials, instance/role creds).
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    # Titan v2 supports 256 / 512 / 1024. Changing this changes the pgvector
    # column width — re-run seed.py (which drops and recreates tables).
    embedding_dim: int = 256

    # Raw artifact storage: S3 when a bucket is set, local disk otherwise.
    s3_bucket: str = ""
    s3_prefix: str = "artifacts"

    model_config = SettingsConfigDict(
        env_prefix="CARETHREAD_",
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)


def aws_credential_kwargs() -> dict:
    """boto3 client kwargs: explicit keys from .env if set, otherwise empty so
    the default AWS credential chain is used."""
    if not settings.aws_access_key_id:
        return {}
    kw = {"aws_access_key_id": settings.aws_access_key_id,
          "aws_secret_access_key": settings.aws_secret_access_key}
    if settings.aws_session_token:
        kw["aws_session_token"] = settings.aws_session_token
    return kw


def anthropic_bedrock_kwargs() -> dict:
    """Same, but with the Anthropic SDK's parameter names (AnthropicBedrock)."""
    if not settings.aws_access_key_id:
        return {}
    kw = {"aws_access_key": settings.aws_access_key_id,
          "aws_secret_key": settings.aws_secret_access_key}
    if settings.aws_session_token:
        kw["aws_session_token"] = settings.aws_session_token
    return kw
