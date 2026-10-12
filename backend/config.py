"""Application configuration and environment settings for BankSim."""

from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine absolute paths to project directories to guarantee reliable .env loading
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

ENV_FILES = (
    str(PROJECT_ROOT / ".env"),
    str(BACKEND_DIR / ".env"),
    ".env",
    "backend/.env",
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "BankSim: Blue-Team AI Firewall"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment mode: development, testing, or production",
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug flag. Must remain False in production for security.",
    )
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Restrictive CORS allowlist for local development
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database configuration for SQLite (safe local default under backend/data/)
    DATABASE_URL: str = "sqlite:///./backend/data/banksim.db"

    # Authentication & Security
    SECRET_KEY: str = Field(
        default="banksim-dev-secret-key-replace-in-production-abcdef123456",
        description="Cryptographic secret key for signing authentication tokens",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MAX_LOGIN_ATTEMPTS: int = 5

    # Mandatory Login OTP Configuration
    LOGIN_OTP_EXPIRE_MINUTES: int = 5
    LOGIN_OTP_MAX_ATTEMPTS: int = 3
    LOGIN_OTP_RESEND_COOLDOWN_SECONDS: int = 30
    LOGIN_OTP_MAX_RESENDS: int = 3

    # Adaptive Risk Engine Thresholds
    RISK_HIGH_AMOUNT_THRESHOLD_PAISE: int = 5000000  # 50,000 INR in paise
    RISK_VELOCITY_WINDOW_MINUTES: int = 60
    RISK_VELOCITY_TX_COUNT_THRESHOLD: int = 3
    RISK_BURST_WINDOW_SECONDS: int = 60
    RISK_BURST_REQUEST_COUNT_THRESHOLD: int = 5
    RISK_THRESHOLD_ALLOW: int = 25
    RISK_THRESHOLD_STEP_UP: int = 60
    RISK_THRESHOLD_RESTRICT: int = 80

    # Banking Transfer Limits
    MAX_TRANSFER_AMOUNT_PAISE: int = 1000000000  # 10,000,000 INR (1 crore paise max single transfer)


    # AI Threat Analyzer Configuration
    AI_PROVIDER: str = Field(
        default="gemini",
        description="Explicit AI provider selector: 'gemini', 'openai', or 'mock'",
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for OpenAI LLM provider (optional)",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model identifier used for OpenAI LLM threat analysis",
    )
    OPENAI_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="Request timeout in seconds for OpenAI provider calls",
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        description="API key for Google Gemini LLM provider (optional)",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "GOOGLE_MODEL"),
        description="Model identifier used for Gemini threat analysis",
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="Request timeout in seconds for Gemini provider calls",
    )

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> List[str]:
        """Support comma-separated strings or JSON arrays for CORS configuration."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json

                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the cached settings instance to force reloading from environment or disk."""
    get_settings.cache_clear()

