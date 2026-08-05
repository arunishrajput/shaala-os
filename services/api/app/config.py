import os


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    vision_provider: str = os.getenv("VISION_PROVIDER", "fixture")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_id: str = os.getenv("GEMINI_MODEL_ID", "")
    cors_origins: list[str] = _split_csv(os.getenv("CORS_ORIGINS", ""))
    env: str = os.getenv("ENV", "development")


settings = Settings()
