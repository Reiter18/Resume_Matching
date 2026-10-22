from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://jobmatch:jobmatch@localhost:5432/jobmatch"
    redis_url: str = "redis://localhost:6379/0"
    user_agent: str = "jobmatch-student-project/0.1"
    http_timeout: float = 15.0
    http_retries: int = 3
    ingest_interval_seconds: int = 1800  
    breaker_threshold: int = 5  
    breaker_cooldown_seconds: int = 3600
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
