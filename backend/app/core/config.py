from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(
        default="TeumSeoul API",
        validation_alias=AliasChoices("TEUMSEOUL_APP_NAME", "APP_NAME"),
    )
    app_env: Literal["local", "development", "test", "production"] = Field(
        default="local",
        validation_alias=AliasChoices("TEUMSEOUL_APP_ENV", "APP_ENV"),
    )
    debug: bool = Field(default=False, validation_alias="TEUMSEOUL_DEBUG")
    api_prefix: str = Field(
        default="/api",
        validation_alias=AliasChoices("API_PREFIX", "TEUMSEOUL_API_PREFIX"),
    )
    database_url: str = Field(
        default="sqlite:///./localhub.db",
        validation_alias=AliasChoices("DATABASE_URL", "TEUMSEOUL_DATABASE_URL"),
    )
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "TEUMSEOUL_ALLOWED_ORIGINS"),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "TEUMSEOUL_OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-5-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "TEUMSEOUL_OPENAI_MODEL"),
    )
    openai_timeout_seconds: float = Field(
        default=8,
        gt=0,
        validation_alias=AliasChoices(
            "OPENAI_TIMEOUT_SECONDS", "TEUMSEOUL_OPENAI_TIMEOUT_SECONDS"
        ),
    )
    openai_max_candidates: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias=AliasChoices(
            "OPENAI_MAX_CANDIDATES", "TEUMSEOUL_OPENAI_MAX_CANDIDATES"
        ),
    )
    recommendation_timeout_seconds: float = Field(
        default=30,
        gt=0,
        validation_alias=AliasChoices(
            "RECOMMENDATION_TIMEOUT_SECONDS",
            "TEUMSEOUL_RECOMMENDATION_TIMEOUT_SECONDS",
        ),
    )
    recommendation_candidate_limit: int = Field(
        default=18,
        ge=9,
        le=30,
        validation_alias=AliasChoices(
            "RECOMMENDATION_CANDIDATE_LIMIT",
            "TEUMSEOUL_RECOMMENDATION_CANDIDATE_LIMIT",
        ),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "TEUMSEOUL_LOG_LEVEL"),
    )

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        normalized = f"/{value.strip('/')}"
        return normalized.rstrip("/")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
