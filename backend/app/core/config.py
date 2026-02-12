"""
Application configuration settings
"""

import secrets
import sys
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )

    # Application
    APP_NAME: str = "VoiceAI Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/voiceai"
    DATABASE_POOL_SIZE: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # JWT - No default for SECRET_KEY, must be set in environment
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OpenAI - No default, must be set in environment
    OPENAI_API_KEY: str = ""
    OPENAI_ORGANIZATION: Optional[str] = None

    # Ultravox
    ULTRAVOX_API_KEY: str = ""
    ULTRAVOX_BASE_URL: str = "https://api.ultravox.ai/api"
    ULTRAVOX_WEBHOOK_URL: str = ""  # Public URL for Ultravox webhook callbacks

    # xAI (Grok Voice Agent)
    XAI_API_KEY: str = ""

    # Cloud Pipeline API Keys
    GROQ_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""

    # SIP Trunk
    SIP_TRUNK_HOST: str = ""
    SIP_TRUNK_PORT: int = 5060
    SIP_TRUNK_TRANSPORT: str = "udp"
    SIP_TRUNK_USERNAME: str = ""
    SIP_TRUNK_PASSWORD: str = ""
    SIP_TRUNK_CALLER_ID: str = ""

    # Asterisk ARI - Credentials from environment
    ASTERISK_HOST: str = "localhost"
    ASTERISK_ARI_PORT: int = 8088
    ASTERISK_ARI_USER: str = ""
    ASTERISK_ARI_PASSWORD: str = ""

    # Asterisk SIP Bridge (for Ultravox → Asterisk → SIP trunk routing)
    ASTERISK_EXTERNAL_HOST: str = ""  # Public IP/hostname for Asterisk SIP
    ASTERISK_SIP_PORT: int = 5043
    ULTRAVOX_SIP_USERNAME: str = "ultravox"  # Must match pjsip.conf [ultravox-auth]
    ULTRAVOX_SIP_PASSWORD: str = ""  # Must be set in .env, must match pjsip.conf

    # MinIO - Credentials from environment
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "voiceai-recordings"
    MINIO_BUCKET_RECORDINGS: str = "recordings"
    MINIO_BUCKET_EXPORTS: str = "exports"

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_CONCURRENT_CALLS: int = 50

    # File Upload Limits
    MAX_UPLOAD_SIZE_MB: int = 10  # Maximum file upload size in MB

    # WebSocket Limits
    MAX_WEBSOCKET_CONNECTIONS: int = 100
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # seconds

    # Webhook
    WEBHOOK_SECRET: str = ""

    # SMTP / Email - Admin approval system
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    ADMIN_APPROVAL_EMAIL: str = ""  # Admin email for new user approval notifications
    APP_BASE_URL: str = "https://one.speakmaxi.com"  # Public URL for approval links

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is set and secure. Fails hard if not set."""
        insecure_defaults = [
            "your-super-secret-jwt-key-change-in-production",
            "CHANGE_THIS_TO_A_SECURE_RANDOM_KEY_IN_PRODUCTION",
            "secret",
            "changeme",
            "",
        ]
        if v in insecure_defaults:
            raise ValueError(
                "SECRET_KEY must be set to a secure value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY is too short. Use at least 32 characters.")
        return v

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Warn if OpenAI API key is not set"""
        if not v or v.startswith("sk-your-"):
            print(
                "\n⚠️  WARNING: OPENAI_API_KEY is not set or using placeholder.\n"
                "   Get your API key from: https://platform.openai.com/api-keys\n"
            )
        return v

    @field_validator("ULTRAVOX_API_KEY")
    @classmethod
    def validate_ultravox_key(cls, v: str) -> str:
        """Warn if Ultravox API key is not set"""
        if not v:
            print(
                "\n⚠️  WARNING: ULTRAVOX_API_KEY is not set.\n"
                "   Get your API key from: https://app.ultravox.ai\n"
            )
        return v


# Create settings instance
settings = Settings()


def validate_production_settings() -> bool:
    """
    Validate that all required production settings are configured.
    Call this at application startup in production.
    """
    errors = []

    # Check critical settings
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your-"):
        errors.append("OPENAI_API_KEY is not configured (needed for OpenAI provider)")

    if not settings.ULTRAVOX_API_KEY:
        errors.append("ULTRAVOX_API_KEY is not configured (needed for Ultravox provider)")

    if len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY is too short (minimum 32 characters)")

    if not settings.DEBUG:
        # Production-only checks
        if not settings.ASTERISK_ARI_USER or not settings.ASTERISK_ARI_PASSWORD:
            errors.append("ASTERISK_ARI credentials are not configured")

        if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
            errors.append("MinIO credentials are not configured")

    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"   - {error}")
        print()
        return False

    return True
