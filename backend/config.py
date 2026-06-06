from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: str = "http://localhost:3000"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    wandb_api_key: str | None = None
    wandb_entity: str | None = None
    weave_project: str = "opsroom-ai"
    weave_disabled: bool = False
    stream_block_ms: int = 2_000
    stream_batch_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()

