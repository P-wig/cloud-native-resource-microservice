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
from typing import Any, Literal
from urllib.parse import quote_plus

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

    # Database / MongoDB
    database_url: str = Field(default="", alias="DATABASE_URL")
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_username: str = Field(default="", alias="USERNAME")
    mongodb_password: str = Field(default="", alias="PASSWORD")
    mongodb_database: str = Field(default="hardware_db", alias="MONGODB_DATABASE")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")

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

    @field_validator("database_url", "mongodb_uri")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            return value

        if not value.strip():
            raise ValueError("Database URI cannot be empty")

        if "://" not in value:
            raise ValueError(
                "Database URI must include URI scheme, e.g. mongodb+srv://<username>:<password>@<cluster-url>/<dbname>"
            )

        if not (value.startswith("mongodb://") or value.startswith("mongodb+srv://")):
            raise ValueError("Database URI must start with mongodb:// or mongodb+srv://")

        return value

    @field_validator("mongodb_database")
    @classmethod
    def validate_mongodb_database(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("MONGODB_DATABASE cannot be empty")
        return value.strip()

    @model_validator(mode="after")
    def validate_tls_files(self) -> "Settings":
        if not self.mongodb_uri and not self.database_url:
            raise ValueError("Either MONGODB_URI or DATABASE_URL must be set")

        if not self.mongodb_uri and self.database_url:
            self.mongodb_uri = self.database_url

        if not self.database_url and self.mongodb_uri:
            self.database_url = self.mongodb_uri

        username = self._normalize_credential(self.mongodb_username)
        password = self._normalize_credential(self.mongodb_password)
        self.mongodb_username = username
        self.mongodb_password = password

        if (username and not password) or (password and not username):
            raise ValueError("Both USERNAME and PASSWORD must be set together")

        if username and password:
            encoded_password = quote_plus(password)
            self.mongodb_uri = self._inject_credentials(self.mongodb_uri, username, encoded_password)
            self.database_url = self._inject_credentials(self.database_url, username, encoded_password)

        if self.enable_tls:
            if not self.cert_file or not self.key_file:
                raise ValueError("CERT_FILE and KEY_FILE are required when ENABLE_TLS=true")

            cert_exists = os.path.exists(self.cert_file)
            key_exists = os.path.exists(self.key_file)
            if not cert_exists or not key_exists:
                raise ValueError("CERT_FILE and KEY_FILE must point to existing files")
        return self

    @staticmethod
    def _normalize_credential(value: str) -> str:
        normalized = value.strip()
        if (
            len(normalized) >= 2
            and ((normalized[0] == '"' and normalized[-1] == '"') or (normalized[0] == "'" and normalized[-1] == "'"))
        ):
            normalized = normalized[1:-1]
        return normalized

    @staticmethod
    def _inject_credentials(uri: str, username: str, encoded_password: str) -> str:
        if not uri or "://" not in uri:
            return uri

        scheme, remainder = uri.split("://", 1)
        host_and_path = remainder

        if "@" in host_and_path:
            host_and_path = host_and_path.rsplit("@", 1)[1]

        return f"{scheme}://{username}:{encoded_password}@{host_and_path}"

    @property
    def mongo_client_uri(self) -> str:
        return self.mongodb_uri or self.database_url

    @property
    def mongo_client_options(self) -> dict[str, Any]:
        return {"maxPoolSize": self.database_pool_size}

    @property
    def mongo_database_name(self) -> str:
        return self.mongodb_database


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()