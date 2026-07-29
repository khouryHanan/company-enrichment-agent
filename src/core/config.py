"""
Configuration — loaded from environment variables (via a .env file in
development). Never hardcode secrets.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into the process environment, if present


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent1.db")

    # LangChain's init_chat_model accepts "provider:model" strings — the
    # provider prefix determines which integration package and API key
    # env var is used. No hardcoded fallback here on purpose: which model
    # to use is a team/deployment decision, not something to silently
    # assume. Set this in your .env, e.g.:
    #   AI_MODEL=google_genai:gemini-2.0-flash
    #   AI_MODEL=anthropic:claude-sonnet-4-6
    #   AI_MODEL=groq:llama-3.3-70b-versatile
    AI_MODEL: str = os.getenv("AI_MODEL", "")

    AGENT3_BASE_URL: str = os.getenv("AGENT3_BASE_URL", "http://localhost:8003")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))


settings = Settings()