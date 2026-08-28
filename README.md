# local_telegram_bot

Minimal Telegram agent: durable Chat per user, Skill Catalog, and an Agentic Loop
that can load Skills and run allowlisted `curl.exe` (e.g. weather via wttr.in)
against a local Ollama model.

## Requirements

- Python 3.12
- [Ollama](https://ollama.com/) running locally with `qwen3:1.7b` (or set another model)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- `curl.exe` on `PATH` (Windows) for weather / HTTP tool use

## Setup

```powershell
py -3.12 -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
copy .env.example .env
# Edit .env: TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_CHAT_IDS
```

Set `TELEGRAM_ALLOWED_CHAT_IDS` to your Telegram chat id(s) before enabling the
bot — `exec` runs on the host, so strangers should not reach the Agent.

Operator steps for Ollama:

1. Start Ollama on Windows.
2. `ollama pull qwen3:1.7b`
3. Smoke test: `ollama run qwen3:1.7b "Hello"`

## Run

```powershell
.\venv\Scripts\python.exe -m src.main
```

Useful Telegram commands:

- Normal text — Agent turn (memory + optional tools)
- `/new` — clear this chat’s history (Chat Store too)

Chat history is stored under `.scratch/chats/` (gitignored). Runtime Skills live
in `src/skills/` and are rescanned every turn.

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

No live Telegram, Ollama, or network curl required for the suite.

## Layout

- `src/agent.py` — Chat Store, Agentic Loop, Tool Protocol, Context Budget
- `src/exec_runner.py` — allowlisted `curl.exe` with cwd jail and timeout
- `src/skills/` — runtime Skills (Type A: `wttr.md`)
- `src/channels/` — Telegram long polling / send / chunking
- `src/inference/` — Ollama inference plugin
- `src/orchestrator.py` — allowlist → Agent → send
- `docs/spec_agent.md` — agent product spec (supersedes one-shot `docs/spec.md` where they conflict)
- `CONTEXT.md` — domain vocabulary

Secrets live in `.env` (gitignored). See `.env.example` for variable names.
