"""
Application configuration settings.

This file should contain:
- Environment variable definitions and their defaults
- Configuration classes using pydantic or similar
- Settings validation logic
- Different config profiles (dev, prod, test)

Example structure:
- Database connection settings
- Service ports and hosts
- Feature flags
- API keys and secrets
- Logging levels
"""

# DONE: Imported required libraries (pydantic, pydantic-settings, os, functools, typing).
# DONE: Implemented Settings class with env-backed fields for server, database, logging,
# DONE: monitoring/tracing, TLS, and runtime environment.
# DONE: Added get_settings() factory function with lru_cache.
# DONE: Added validation for critical settings:
# DONE: - Port ranges (1-65535)
# DONE: - Positive max_workers/database_pool_size
# DONE: - Non-empty DATABASE_URL with scheme
# DONE: - TLS cert/key presence and file existence when ENABLE_TLS=true

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=50051, alias="SERVER_PORT")
    max_workers: int = Field(default=10, alias="MAX_WORKERS")

    # Database (placeholder - replace with MongoDB-specific settings during integration)
    database_url: str = Field(..., alias="DATABASE_URL")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")

    # TODO (mongodb integration): Replace generic database settings with MongoDB-specific config
    # once Azure container + MongoDB are linked.
    # Proposed fields:
    # - mongodb_uri (alias="MONGODB_URI")               # e.g. mongodb+srv://...
    # - mongodb_database (alias="MONGODB_DATABASE")     # target DB name
    # - mongodb_max_pool_size (alias="MONGODB_MAX_POOL_SIZE", default=100)
    # - mongodb_min_pool_size (alias="MONGODB_MIN_POOL_SIZE", default=0)
    # Update repository wiring to construct Motor/PyMongo client from these settings.
    # Keep DATABASE_URL as backward-compatible fallback during migration, then remove it.

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    log_format: Literal["json", "text"] = Field(default="json", alias="LOG_FORMAT")

    # Monitoring / tracing
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=8080, alias="METRICS_PORT")
    enable_tracing: bool = Field(default=True, alias="ENABLE_TRACING")
    jaeger_endpoint: str = Field(default="http://localhost:14268", alias="JAEGER_ENDPOINT")

    # Security
    enable_tls: bool = Field(default=False, alias="ENABLE_TLS")
    cert_file: str = Field(default="", alias="CERT_FILE")
    key_file: str = Field(default="", alias="KEY_FILE")

    # Runtime environment
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, alias="DEBUG")

    @field_validator("server_port", "metrics_port")
    @classmethod
    def validate_port_range(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return value

    @field_validator("max_workers", "database_pool_size")
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than 0")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        if "://" not in value:
            raise ValueError("DATABASE_URL must include URI scheme, e.g. mongodb+srv://<username>:<password>@<cluster-url>/<dbname>")
        return value

    @model_validator(mode="after")
    def validate_tls_files(self) -> "Settings":
        if self.enable_tls:
            if not self.cert_file or not self.key_file:
                raise ValueError("CERT_FILE and KEY_FILE are required when ENABLE_TLS=true")

            cert_exists = os.path.exists(self.cert_file)
            key_exists = os.path.exists(self.key_file)
            if not cert_exists or not key_exists:
                raise ValueError("CERT_FILE and KEY_FILE must point to existing files")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()