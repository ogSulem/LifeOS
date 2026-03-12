from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="dev", validation_alias="ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    bot_token: str = Field(validation_alias="BOT_TOKEN")
    database_url: str = Field(validation_alias="DATABASE_URL")

    tz: str = Field(default="Europe/Moscow", validation_alias="TZ")

    admin_id: int | None = Field(default=None, validation_alias="ADMIN_ID")
    admin_support_chat_id: int | None = Field(default=None, validation_alias="ADMIN_SUPPORT_CHAT_ID")

    price_month: int = Field(default=299, validation_alias="PRICE_MONTH")

    payments_provider_token: str | None = Field(default=None, validation_alias="PAYMENTS_PROVIDER_TOKEN")
    yookassa_shop_id: str | None = Field(default=None, validation_alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str | None = Field(default=None, validation_alias="YOOKASSA_SECRET_KEY")
    yookassa_return_url: str = Field(default="https://t.me/", validation_alias="YOOKASSA_RETURN_URL")

    ai_token: str | None = Field(default=None, validation_alias="AI_TOKEN")

    openrouter_enabled: bool = Field(default=False, validation_alias="OPENROUTER_ENABLED")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", validation_alias="OPENROUTER_MODEL")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")


settings = Settings()
