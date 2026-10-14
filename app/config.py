from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]  # repo root; keeps paths cwd-independent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    openrouter_api_key: str = ""
    tutor_model: str = "openrouter:anthropic/claude-haiku-5.5"
    grader_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    author_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    judge_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    embed_model: str = "openrouter:openai/text-embedding-3-small"
    embed_dims: int = 1536  # must equal the chunks.embedding column in app/pg_schema.sql
    rag_enabled: bool = True  # false: the tutor uses the lesson text only
    rag_k: int = 6  # docs chunks the tutor gets per turn; clamped to 1..10
    openrouter_zdr: bool = False
    openrouter_app_title: str = "hint-kata"
    hintkata_db_path: str = "data/hintkata.db"
    database_url: str = ""
    database_url_unpooled: str = ""
    practice_repo: str = ""
    logfire_token: str = ""
    desired_retention: float = 0.9
    content_root: str = str(ROOT / "content")
    mastery_quiz_threshold: float = 0.8
    mastery_recalls_required: int = 2

    @field_validator("rag_k")
    @classmethod
    def _clamp_rag_k(cls, v: int) -> int:
        return min(max(v, 1), 10)  # 0 would turn RAG off by accident; 100 would flood the prompt


settings = Settings()
