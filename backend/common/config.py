"""Environment-backed settings shared by backend processes."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "ForgeJudge API"
    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://forgejudge:local-development-only@localhost:5432/forgejudge",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    submission_stream: str = "forgejudge:submissions"
    submission_consumer_group: str = "forgejudge-workers"
    worker_consumer_name: str = "forgejudge-worker"
    judge_python_image: str = "python:3.12-slim"
    judge_workspace_volume: str = "forgejudge_judge_workspaces"
    judge_workspace_path: str = "/judge-workspaces"

    model_config = SettingsConfigDict(env_prefix="FORGEJUDGE_", extra="ignore")


settings = Settings()
