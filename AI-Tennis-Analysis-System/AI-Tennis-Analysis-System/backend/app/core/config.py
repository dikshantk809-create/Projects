from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TENNIS_", env_file=".env", extra="ignore")
    app_name: str = "AI Tennis Analysis"
    database_url: str = "postgresql+asyncpg://tennis:tennis@db:5432/tennis"
    jwt_secret: str = "change-me"; jwt_alg: str = "HS256"; jwt_expire_min: int = 120
    ingest_token: str = "change-me"
    cors_origins: list[str] = ["http://localhost:5176"]
@lru_cache
def get_settings(): return Settings()
