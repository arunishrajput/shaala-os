import os
from datetime import date


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


# The demo's fixed "today" (PROMPT.md §11: "Fixed RNG seed everywhere, so the
# deployed app looks identical to your video"). seed.py generates 90 days of
# attendance/absence history ending the day before this date. Every
# date-relative computation (signals, the staffing forecast, "mark absent
# today") must anchor to this constant rather than the real wall-clock date,
# or results silently drift the day after the demo video is recorded. Not
# env-configurable on purpose — changing it without re-seeding would desync
# the app from its own data.
DEMO_ANCHOR_DATE = date(2026, 8, 5)


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
    # Local/CI hardware comfortably solves within the default; free-tier deploy
    # hosts can be CPU-constrained enough to need more — tunable per environment
    # without touching the tested default (see tests/test_solver.py).
    solver_time_limit_s: float = float(os.getenv("SOLVER_TIME_LIMIT_S", "8.0"))


settings = Settings()
