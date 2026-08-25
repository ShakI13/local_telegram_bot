"""Entry point: wire Telegram + Ollama plugins and run the orchestrator."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow `python src/main.py` and `python -m src.main` from repo root.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.channels.telegram import TelegramChannel
from src.config import load_settings
from src.inference.ollama import OllamaInference
from src.orchestrator import Orchestrator


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    channel = TelegramChannel(settings.telegram_bot_token)
    inference = OllamaInference(
        settings.ollama_model,
        base_url=settings.ollama_base_url,
    )
    Orchestrator(channel, inference).run()


if __name__ == "__main__":
    main()
