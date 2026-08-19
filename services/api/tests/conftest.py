"""
Set required environment variables *before* any app module is imported.

conftest.py is processed by pytest before test collection, so os.environ
mutations here are visible when config.py and main.py are first imported by
test modules. Without this, config.py's startup guard raises RuntimeError
because JWT_SECRET is absent from the CI environment.
"""
import os

# Tell config.py's startup guard to skip the secret-length check.
os.environ.setdefault("ENV", "test")

# Provide a fake-but-valid JWT secret so security.py functions work in tests.
os.environ.setdefault(
    "JWT_SECRET", "pytest-only-fake-secret-never-use-in-production-32x"
)

# Satisfy the CORS_ORIGINS startup check added in main.py.
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

# Demo-reset key — must match what test_demo_reset.py sends in X-Reset-Key.
os.environ.setdefault("DEMO_RESET_KEY", "pytest-demo-reset-key")
