from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Inteligência Auto Postos"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = Field(
        default="postgresql+asyncpg://smartfuel:smartfuel@localhost:5432/smartfuel",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://smartfuel:smartfuel@localhost:5432/smartfuel",
        alias="DATABASE_URL_SYNC",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="smartfuel", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Preparado para Sprint 5 — não usado na Sprint 0
    xpert_sqlserver_host: str = Field(default="", alias="XPERT_SQLSERVER_HOST")
    xpert_sqlserver_port: int = Field(default=1433, alias="XPERT_SQLSERVER_PORT")
    xpert_sqlserver_database: str = Field(default="atxdados", alias="XPERT_SQLSERVER_DATABASE")
    xpert_sqlserver_user: str = Field(default="", alias="XPERT_SQLSERVER_USER")
    xpert_sqlserver_password: str = Field(default="", alias="XPERT_SQLSERVER_PASSWORD")
    xpert_sqlserver_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        alias="XPERT_SQLSERVER_DRIVER",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
