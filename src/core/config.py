"""
Configuration — loaded from environment variables. Never hardcode secrets.
"""

import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent1.db")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AGENT3_BASE_URL: str = os.getenv("AGENT3_BASE_URL", "http://localhost:8003")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))


settings = Settings()
