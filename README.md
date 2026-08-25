# local_telegram_bot

Simple Telegram bot that forwards each text message to a local Ollama LLM and
sends the reply back. No conversation memory (v1).

## Requirements

- Python 3.12
- [Ollama](https://ollama.com/) running locally with `qwen3:1.7b` (or set another model)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

```powershell
py -3.12 -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
copy .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN
```

Operator steps for Ollama:

1. Start Ollama on Windows.
2. `ollama pull qwen3:1.7b`
3. Smoke test: `ollama run qwen3:1.7b "Hello"`

## Run

```powershell
.\venv\Scripts\python.exe -m src.main
```

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Layout

- `src/channels/` — channel plugins (Telegram long polling)
- `src/inference/` — inference plugins (Ollama)
- `src/orchestrator.py` — inbound text → generate → send
- `docs/spec.md` — product/architecture spec

Secrets live in `.env` (gitignored). See `.env.example` for variable names.
