from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    tutor_model: str = "openrouter:anthropic/claude-haiku-5.5"
    grader_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    author_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    judge_model: str = "openrouter:anthropic/claude-sonnet-5.5"
    openrouter_zdr: bool = False
    openrouter_app_title: str = "hint-kata"
    hintkata_db_path: str = "data/hintkata.db"
    practice_repo: str = ""
    logfire_token: str = ""
    desired_retention: float = 0.9


settings = Settings()
