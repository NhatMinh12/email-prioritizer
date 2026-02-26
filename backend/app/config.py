from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")

    gmail_client_id: str = Field(..., alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(..., alias="GMAIL_CLIENT_SECRET")
    gmail_redirect_uri: str = Field(..., alias="GMAIL_REDIRECT_URI")

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    secret_key: str = Field(..., alias="SECRET_KEY")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")

    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="ALLOWED_ORIGINS",
    )

    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    cache_ttl: int = Field(default=604800, alias="CACHE_TTL")  # 7 days

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()