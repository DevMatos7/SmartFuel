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
    minio_quote_evidence_bucket: str = Field(
        default="quote-evidences",
        alias="MINIO_QUOTE_EVIDENCE_BUCKET",
    )
    signed_url_expire_seconds: int = Field(default=300, alias="SIGNED_URL_EXPIRE_SECONDS")

    quote_evidence_max_size_mb: int = Field(default=10, alias="QUOTE_EVIDENCE_MAX_SIZE_MB")
    quote_ai_max_file_size_mb: int = Field(default=10, alias="QUOTE_AI_MAX_FILE_SIZE_MB")
    quote_ai_max_batch_files: int = Field(default=20, alias="QUOTE_AI_MAX_BATCH_FILES")
    quote_ai_max_batch_size_mb: int = Field(default=50, alias="QUOTE_AI_MAX_BATCH_SIZE_MB")
    quote_ai_max_pdf_pages: int = Field(default=20, alias="QUOTE_AI_MAX_PDF_PAGES")
    quote_ai_max_image_pixels: int = Field(default=40_000_000, alias="QUOTE_AI_MAX_IMAGE_PIXELS")
    quote_expiration_interval_minutes: int = Field(
        default=15,
        alias="QUOTE_EXPIRATION_INTERVAL_MINUTES",
    )
    quote_duplicate_warning_window_minutes: int = Field(
        default=60,
        alias="QUOTE_DUPLICATE_WARNING_WINDOW_MINUTES",
    )
    quote_expiration_batch_size: int = Field(default=500, alias="QUOTE_EXPIRATION_BATCH_SIZE")
    quote_expiration_lock_timeout_seconds: int = Field(
        default=300,
        alias="QUOTE_EXPIRATION_LOCK_TIMEOUT_SECONDS",
    )
    object_storage_allow_memory_fallback: bool = Field(
        default=False,
        alias="OBJECT_STORAGE_ALLOW_MEMORY_FALLBACK",
    )

    @property
    def quote_evidence_max_bytes(self) -> int:
        return self.quote_evidence_max_size_mb * 1024 * 1024

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
    xpert_odbc_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        alias="XPERT_ODBC_DRIVER",
    )
    xpert_connection_timeout_seconds: int = Field(default=10, alias="XPERT_CONNECTION_TIMEOUT_SECONDS")
    xpert_query_timeout_seconds: int = Field(default=120, alias="XPERT_QUERY_TIMEOUT_SECONDS")
    xpert_sync_poll_interval_seconds: int = Field(default=15, alias="XPERT_SYNC_POLL_INTERVAL_SECONDS")
    xpert_sync_default_batch_size: int = Field(default=1000, alias="XPERT_SYNC_DEFAULT_BATCH_SIZE")
    xpert_sync_default_overlap_seconds: int = Field(default=300, alias="XPERT_SYNC_DEFAULT_OVERLAP_SECONDS")
    xpert_sync_max_retries: int = Field(default=3, alias="XPERT_SYNC_MAX_RETRIES")
    xpert_sync_retry_base_seconds: int = Field(default=60, alias="XPERT_SYNC_RETRY_BASE_SECONDS")
    xpert_staging_retention_days: int = Field(default=30, alias="XPERT_STAGING_RETENTION_DAYS")
    xpert_error_retention_days: int = Field(default=180, alias="XPERT_ERROR_RETENTION_DAYS")
    xpert_allow_unsafe_privileges: bool = Field(default=False, alias="XPERT_ALLOW_UNSAFE_PRIVILEGES")
    xpert_worker_heartbeat_timeout_seconds: int = Field(
        default=300,
        alias="XPERT_WORKER_HEARTBEAT_TIMEOUT_SECONDS",
    )

    jwt_secret_key: str = Field(
        default="change-me-in-production-use-long-random-secret",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_cookie_name: str = Field(default="refresh_token", alias="REFRESH_COOKIE_NAME")
    refresh_cookie_secure: bool = Field(default=False, alias="REFRESH_COOKIE_SECURE")
    refresh_cookie_samesite: str = Field(default="lax", alias="REFRESH_COOKIE_SAMESITE")
    password_min_length: int = Field(default=8, alias="PASSWORD_MIN_LENGTH")
    login_rate_limit: int = Field(default=5, alias="LOGIN_RATE_LIMIT")
    login_rate_window_seconds: int = Field(default=60, alias="LOGIN_RATE_WINDOW_SECONDS")
    login_rate_allow_memory_fallback: bool = Field(
        default=True,
        alias="LOGIN_RATE_ALLOW_MEMORY_FALLBACK",
    )

    default_supplier_allowed: bool = Field(default=False, alias="DEFAULT_SUPPLIER_ALLOWED")
    default_minimum_volume_liters: str = Field(
        default="5000.000",
        alias="DEFAULT_MINIMUM_VOLUME_LITERS",
    )
    master_data_import_max_bytes: int = Field(
        default=5_242_880,
        alias="MASTER_DATA_IMPORT_MAX_BYTES",
    )

    test_database_url: str = Field(default="", alias="TEST_DATABASE_URL")
    test_database_url_sync: str = Field(default="", alias="TEST_DATABASE_URL_SYNC")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
