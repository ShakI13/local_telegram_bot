"""Load settings from environment / `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:1.7b"


def load_settings(*, env_file: str | None = ".env") -> Settings:
    """Load settings; `TELEGRAM_BOT_TOKEN` is required."""
    if env_file:
        load_dotenv(env_file)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required (set it in .env)")

    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
    model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b").strip()
    return Settings(
        telegram_bot_token=token,
        ollama_base_url=base_url.rstrip("/"),
        ollama_model=model or "qwen3:1.7b",
    )
