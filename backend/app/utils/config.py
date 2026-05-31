"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Centralized app configuration used across backend modules."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
		case_sensitive=False,
	)

	app_name: str = Field(default="AI Health Companion API", alias="APP_NAME")
	app_env: str = Field(default="development", alias="APP_ENV")
	app_debug: bool = Field(default=True, alias="APP_DEBUG")

	host: str = Field(default="0.0.0.0", alias="HOST")
	port: int = Field(default=8000, alias="PORT")

	database_url: str = Field(
		default="mysql+pymysql://root:root@localhost:3306/ai_health_db",
		alias="DATABASE_URL",
	)

	jwt_secret_key: str = Field(
		default="replace_with_a_long_random_secret", alias="JWT_SECRET_KEY"
	)
	jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
	jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

	# Gemini AI
	gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

	# CORS — JSON array of allowed origins (e.g. '["http://localhost","http://localhost:4200"]')
	cors_origins: List[str] = Field(
		default=["http://localhost", "http://localhost:4200"],
		alias="CORS_ORIGINS",
	)



@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Cache settings instance so env parsing runs once per process."""
	return Settings()

