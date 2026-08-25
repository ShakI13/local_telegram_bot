# Spec: local_telegram_bot

## Goal

Build a simple Telegram bot that forwards each user text message to a local LLM and returns the model reply. No dialog memory on this stage.

```text
User message → Channel → Orchestrator → Inference → Channel reply
```

## Scope (v1)

### In scope

- Accept text messages from Telegram (long polling).
- Call a local LLM (Ollama) with that text as a one-shot request.
- Send the model reply back to the same chat.
- Store secrets and settings in `.env` (not in code / not in git).
- Extensible layout: **channel** and **inference** as in-process plugins.
- Project layout: `src/`, `tests/`, `docs/`, `venv/`.
- Tests with `unittest`.

### Out of scope (v1)

- Conversation history / multi-turn memory.
- Telegram webhooks (no stable public HTTPS URL).
- Typing / delivery / read status indicators.
- WhatsApp, Twilio, Tyntec, web chat (interfaces only if needed; no full adapters).
- Separate OS process for the agent/LLM caller.
- vLLM.

## Runtime environment

| Item | Choice |
|------|--------|
| OS for bot process | Windows |
| Python | 3.12 (already installed; course asked 3.11 — 3.12 is acceptable substitute) |
| Virtualenv | `venv/` at repo root |
| LLM host | Local machine |
| Telegram mode | Long polling (`getUpdates`) |

## Technology choices

| Concern | Choice | Notes |
|---------|--------|--------|
| Language | Python 3.12 | |
| Telegram client | stdlib HTTP only | No aiogram / telebot / telegraf |
| LLM client | stdlib HTTP only | Talk to Ollama REST API |
| Config | `.env` + `python-dotenv` | Only third-party runtime dependency planned |
| Tests | `unittest` (+ `unittest.mock`) | |
| Packaging extras | none required for Telegram/LLM | |

## Default LLM setup

| Item | Value |
|------|--------|
| Provider (v1) | **Ollama** |
| Model | **`qwen3:1.7b`** |
| Why | Already installed on Windows; simplest HTTP setup; model fits GTX 1060 6 GB |
| Fallback model | `tinyllama` if Qwen is too slow / fails to pull |
| Future provider | LM Studio (installed; OpenAI-compatible local server) as second inference plugin |

Hardware context (dev machine): Intel i7-8700K, 32 GB RAM, NVIDIA GTX 1060 6 GB.

### Operator steps (Ollama)

1. Start Ollama on Windows.
2. `ollama pull qwen3:1.7b`
3. Smoke test: `ollama run qwen3:1.7b "Hello"`
4. API base: `http://127.0.0.1:11434`

## Architecture

In-process plugins (one Python process).

```text
┌─────────────────────────────────────────────────────────┐
│  Bot process                                            │
│                                                         │
│  Channel plugin (Telegram)                              │
│       │ inbound text                                    │
│       ▼                                                 │
│  Orchestrator  ──►  Inference plugin (Ollama)           │
│       │                   │                             │
│       │◄── reply text ────┘                             │
│       ▼                                                 │
│  Channel plugin.send(reply)                             │
└─────────────────────────────────────────────────────────┘
```

### Channel plugin contract (conceptual)

- `poll()` / receive normalized inbound messages: `chat_id`, `text`, `raw` (optional).
- `send(chat_id, text)`.
- v1 implementation: Telegram Bot API via HTTPS.
- Later (not v1): WhatsApp, Twilio, Tyntec, website dialog — same contract.

### Inference plugin contract (conceptual)

- `generate(prompt: str) -> str` (stateless; no history).
- v1 implementation: Ollama (`/api/generate` or `/api/chat` with a single user message).
- Later: LM Studio plugin behind the same interface.

### Orchestrator

- One path: inbound text → `inference.generate` → `channel.send`.
- No session store, no memory.

## Configuration

File: `.env` (gitignored). Provide `.env.example` without secrets.

| Variable | Required | Example / default |
|----------|----------|-------------------|
| `TELEGRAM_BOT_TOKEN` | yes | from @BotFather |
| `TELEGRAM_ALLOWED_CHAT_IDS` | no | empty = allow all; else comma-separated chat IDs |
| `OLLAMA_BASE_URL` | no | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | no | `qwen3:1.7b` |

## Telegram (v1 behavior)

- Create bot via @BotFather; put token only in `.env`.
- Use **long polling** (`getUpdates`), not webhooks.
- Handle text messages only (ignore other update types or no-op).
- No `sendChatAction` / typing indicator in v1.
- No delivery or read receipts (Bot API does not expose WhatsApp-style status for bots).

## Security

- Never hardcode `TELEGRAM_BOT_TOKEN`.
- Never commit `.env`.
- Ensure `.gitignore` covers `.env`, `venv/`, caches.
- Optional: set `TELEGRAM_ALLOWED_CHAT_IDS` so only listed chats get LLM replies.

## Proposed layout

```text
local_telegram_bot/
  .env.example
  .gitignore
  README.md
  docs/
    spec.md
  src/
    ...
  tests/
    ...
  venv/
```

Exact module names are left to implementation; must respect channel/inference plugin split.

## Acceptance criteria (v1)

1. With Ollama running and `qwen3:1.7b` pulled, and a valid bot token in `.env`, starting the bot allows a Telegram user to send text and receive an LLM reply.
2. A second message does not use the first message as context (stateless).
3. Token is not present in source files tracked by git.
4. Unit tests cover orchestration / plugin contracts with mocked HTTP (no live Telegram/Ollama required for CI-style runs).
5. Adding a new inference backend means a new plugin implementing the same interface, without rewriting the Telegram adapter.

## Open for later versions

- LM Studio inference plugin.
- Additional channel adapters.
- Optional typing indicator while generating.
- Webhook mode when a public HTTPS URL exists.
- Dialog memory.
- Split agent/inference into a separate process if deploy needs isolation.
