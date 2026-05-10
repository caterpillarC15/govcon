from functools import lru_cache

from pydantic import Field, model_validator
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

    # PRD §5.14 — Weekly opportunity email (Resend HTTP API).
    resend_api_key: str = Field("", alias="RESEND_API_KEY")
    resend_from_email: str = Field(
        "GovCapture <onboarding@resend.dev>", alias="RESEND_FROM_EMAIL"
    )
    resend_reply_to: str = Field("", alias="RESEND_REPLY_TO")
    email_public_base_url: str = Field(
        "http://localhost:8000", alias="EMAIL_PUBLIC_BASE_URL"
    )
    email_unsubscribe_secret: str = Field("", alias="EMAIL_UNSUBSCRIBE_SECRET")
    email_legal_footer_address: str = Field(
        "", alias="EMAIL_LEGAL_FOOTER_ADDRESS"
    )
    email_dry_run: bool = Field(True, alias="EMAIL_DRY_RUN")
    email_require_double_opt_in: bool = Field(
        False, alias="EMAIL_REQUIRE_DOUBLE_OPT_IN"
    )
    email_auto_pick_enabled: bool = Field(True, alias="EMAIL_AUTO_PICK_ENABLED")
    email_auto_pick_min_score: int = Field(60, alias="EMAIL_AUTO_PICK_MIN_SCORE")
    email_auto_pick_max_candidates: int = Field(
        20, alias="EMAIL_AUTO_PICK_MAX_CANDIDATES"
    )
    email_naics_allowlist: str = Field("", alias="EMAIL_NAICS_ALLOWLIST")
    email_use_fixtures_for_auto_pick: bool = Field(
        False, alias="EMAIL_USE_FIXTURES_FOR_AUTO_PICK"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def email_naics_allowlist_set(self) -> set[str]:
        return {
            n.strip()
            for n in self.email_naics_allowlist.split(",")
            if n.strip()
        }

    @model_validator(mode="after")
    def _refuse_if_dry_run_disabled_without_secrets(self) -> "Settings":
        """PRD §5.14 production gate.

        When EMAIL_DRY_RUN=false, the send path will hit Resend with real
        credentials and emit emails to real subscribers. Refuse to start
        unless every prerequisite for that flow is set: API key for the
        outbound channel, HMAC secret for unsubscribe links, and the
        CAN-SPAM physical mailing address required in the footer.
        """
        if self.email_dry_run:
            return self
        missing: list[str] = []
        if not self.resend_api_key:
            missing.append("RESEND_API_KEY")
        if not self.email_unsubscribe_secret:
            missing.append("EMAIL_UNSUBSCRIBE_SECRET")
        if not self.email_legal_footer_address:
            missing.append("EMAIL_LEGAL_FOOTER_ADDRESS")
        if missing:
            raise ValueError(
                "EMAIL_DRY_RUN=false but the following env vars are empty: "
                + ", ".join(missing)
                + ". Either set them or keep EMAIL_DRY_RUN=true. (PRD §5.14)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
