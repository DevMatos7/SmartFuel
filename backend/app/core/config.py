from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Inteligência Auto Postos", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_port: int = Field(default=3000, alias="FRONTEND_PORT")

    api_prefix: str = "/api/v1"
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="smartfuel", alias="POSTGRES_DB")
    postgres_user: str = Field(default="smartfuel", alias="POSTGRES_USER")
    postgres_password: str = Field(default="smartfuel", alias="POSTGRES_PASSWORD")

    database_url: str = Field(
        default="postgresql+asyncpg://smartfuel:smartfuel@localhost:5432/smartfuel",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://smartfuel:smartfuel@localhost:5432/smartfuel",
        alias="DATABASE_URL_SYNC",
    )

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="evidences", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Preparado para Sprint 5 — não usado nesta sprint
    xpert_sqlserver_host: str = Field(default="", alias="XPERT_SQLSERVER_HOST")
    xpert_sqlserver_port: int = Field(default=1433, alias="XPERT_SQLSERVER_PORT")
    xpert_sqlserver_database: str = Field(default="", alias="XPERT_SQLSERVER_DATABASE")
    xpert_sqlserver_user: str = Field(default="", alias="XPERT_SQLSERVER_USER")
    xpert_sqlserver_password: str = Field(default="", alias="XPERT_SQLSERVER_PASSWORD")
    xpert_sqlserver_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        alias="XPERT_SQLSERVER_DRIVER",
    )
    xpert_sqlserver_encrypt: bool = Field(default=True, alias="XPERT_SQLSERVER_ENCRYPT")
    xpert_sqlserver_trust_certificate: bool = Field(
        default=True,
        alias="XPERT_SQLSERVER_TRUST_CERTIFICATE",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
