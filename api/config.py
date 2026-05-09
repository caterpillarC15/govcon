from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    sam_api_key: str = Field("", alias="SAM_API_KEY")
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    hermes_home: str = Field("~/.hermes", alias="HERMES_HOME")
    hermes_model: str = Field("claude-sonnet-4-6", alias="HERMES_MODEL")

    llm_dev_model: str = Field("claude-haiku-4-5-20251001", alias="LLM_DEV_MODEL")
    llm_synth_model: str = Field("claude-sonnet-4-6", alias="LLM_SYNTH_MODEL")

    run_budget_usd: float = Field(0.50, alias="RUN_BUDGET_USD")
    run_budget_steps: int = Field(40, alias="RUN_BUDGET_STEPS")
    run_budget_seconds: int = Field(360, alias="RUN_BUDGET_SECONDS")

    demo_use_seeded_only: bool = Field(False, alias="DEMO_USE_SEEDED_ONLY")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
