from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OFFICE_", env_file=".env", extra="ignore")
    app_name: str = "AI Office Surveillance"
    database_url: str = "postgresql+asyncpg://office:office@db:5432/office"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    jwt_expire_min: int = 60
    ingest_token: str = "change-me"          # edge → backend bearer
    cors_origins: list[str] = ["http://localhost:5174"]
    # notification creds (optional)
    twilio_sid: str = ""; twilio_token: str = ""
    twilio_from_sms: str = ""; twilio_from_wa: str = ""
    smtp_host: str = ""; smtp_user: str = ""; smtp_pass: str = ""
    fcm_credentials_path: str = ""

@lru_cache
def get_settings() -> Settings:
    return Settings()
