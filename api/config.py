from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    sam_api_key: str = Field("", alias="SAM_API_KEY")

    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Supabase project (PRD v1.2.4 §7.5).
    supabase_url: str = Field("", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field("", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: str = Field("", alias="SUPABASE_ANON_KEY")
    supabase_storage_bucket: str = Field(
        "govcapture-attachments", alias="SUPABASE_STORAGE_BUCKET"
    )

    llm_dev_model: str = Field("claude-haiku-4-5-20251001", alias="LLM_DEV_MODEL")
    llm_synth_model: str = Field("claude-sonnet-4-6", alias="LLM_SYNTH_MODEL")

    run_budget_usd: float = Field(0.50, alias="RUN_BUDGET_USD")
    run_budget_steps: int = Field(40, alias="RUN_BUDGET_STEPS")
    run_budget_seconds: int = Field(360, alias="RUN_BUDGET_SECONDS")

    internal_api_key: str = Field("", alias="INTERNAL_API_KEY")
    cors_allowed_origins: str = Field(
        "http://localhost:3000,http://localhost:3001,http://localhost:5173",
        alias="CORS_ALLOWED_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
