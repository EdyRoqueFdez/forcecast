import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Forcecast API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_ENABLED: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/forcecast"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # External APIs
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_SITE_KEY: str = ""
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@forcecast.app"
    FRONTEND_URL: str = "http://localhost:5173"

    # Email Verification
    EMAIL_VERIFICATION_EXPIRY_HOURS: int = 24
    EMAIL_VERIFICATION_MAX_RESEND: int = 3

    # PostHog (Feature Flags)
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://app.posthog.com"

    # Feature Flags
    FEATURE_CAPTCHA_REGISTRATION: bool = False
    FEATURE_CAPTCHA_FIRST_VOTE: bool = False
    FEATURE_CAPTCHA_BURST_VOTE: bool = False

    # OAuth — Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # OAuth — GitHub
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # JWT — RS256
    JWT_PRIVATE_KEY_PATH: str = "secrets/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "secrets/jwt_public.pem"
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "forcecast"

    # Rate limiting
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_REGISTER_PER_MINUTE: int = 5
    RATE_LIMIT_USER_PER_MINUTE: int = 300
    RATE_LIMIT_ADMIN_PER_MINUTE: int = 1000

    # Sentry
    SENTRY_DSN: str = ""


settings = Settings()