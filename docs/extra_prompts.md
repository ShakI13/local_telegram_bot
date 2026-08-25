# Extra prompts

Все user-промпты эксперимента + вспомогательные вопросы агента при подготовке спеки.

«Файл с дополнительными промптами» — это этот файл: что человек отправил сверх исходного брифа, и какие уточняющие вопросы понадобились, чтобы спека стала однозначной.

Итого user-промптов: **9**.

---

## 1. Spec prepare — промпт 1

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

````
I have the following task:
```txt
Цель задания:
Разработать простейшего Telegram-бота (на TypeScript/JavaScript или Python), интегрированного с API языковой модели.
Требования к функционалу:

Интеграция с Telegram и LLM:

Бот должен принимать текстовое сообщение от пользователя в Telegram.

Отправлять этот текст в качестве запроса в API нейросети (локальная модель через Ollama / VLLM). Рекомендуемые модели: qwen3:1.7b, tinyllama

Возвращать ответ модели обратно пользователю в чат Telegram.

Одноразовый контекст (Без памяти):

Бот работает по схеме User Message → LLM → Bot Reply.

На этом этапе сохранять историю диалога не нужно: каждое новое сообщение обрабатывается как независимый одноразовый запрос.

Технологический стек и рекомендации спикера:

Язык на выбор: TypeScript / JavaScript (Node.js) или Python.

Библиотеки:

Для Python: aiogram или telebot

Для JS/TS: telegraf или grammy

Опционально: Попробовать сделать работу с Telegram Bot API без сторонних библиотек (на чистых HTTP-запросах), чтобы понять устройство Bot API изнутри и избегать рисков supply chain атак.

Безопасность и конфигурация:

TELEGRAM_BOT_TOKEN обязательно хранить в .env-файле и передавать через переменные окружения (не зашивать ключи в код и не пушить в git).

Расширяемая архитектура

инфиренс как плагин

вызов агента (обращение к ллм) - независимый процесс)

...
```

Python version should be: Python 3.11
you need to create virtual env in venv
env vars should be stored in .env file
should be created folder src, tests, docs
use unittest for making tests
do we need not built-in python libs for the task?

Also we need to make some preparations. I have Docker installed. I have WSL installed. You need to get other server information. Server is running Windows 11.

We need to understand what llm provider to use. I have installed vllm and ollama. And how much hardware resources we have and what can we run on it.

Also I'm not familiar with Telegram bots and llm providers. Please prepare user instructions how to create telegram bot, run llm models, setup llm providers.

What do you think about the task? Ask questions if you have don't make assumptions.
````

---

## Вспомогательные запросы агента (spec prepare)

Это как раз поле **«качество вспомогательных запросов»**: уточнения до кода, одним блоком, 8 пунктов.

1. Language: Python only, as above — confirmed?
2. Telegram client: raw HTTP (stdlib) or `aiogram` / `telebot`?
3. LLM provider for v1: Ollama only, with a plugin slot for vLLM later?
4. Where is vLLM? Docker image, another PC, Conda env, or “planned to install”?
5. Python version: must be 3.11, or is 3.12 OK?
6. Where should the bot run? Windows host (talks to Windows Ollama), or WSL?
7. “Agent as independent process”: separate Python process + HTTP between bot and agent, or just a separate module/package in one process for now?
8. Scope for docs: user setup guide only, or also architecture notes for the course?

Ответы пользователя шли несколькими промптами того же чата (ниже). Итог до спеки: Python **3.12**, Windows, long polling, **in-process** channel/inference plugins, stdlib HTTP + `python-dotenv`, Ollama + `qwen3:1.7b`, Telegram first (другие каналы — контракт позже), без webhook/typing/memory. «vLLM» → **LM Studio**.

---

## 2. Spec prepare — промпт 2

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

````
```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
vLLM
```

I mean lmstudio :)

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
Opinion on the task
```

And telegram is only of supported providers. So that also should be swappable: WA, Twilio, Tyntec, dialog in a website. Do we really need to make them as separate processes? Anyway after getting user message we need to wait while llm will generate response. How much time we can wait? How fast we should return response to Telegram? Can we return status ok immidiately and return response when it's ready via some callback?

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
I’d lean stdlib HTTP for Telegram + Ollama, maybe only python-dotenv
```

Ok
````

---

## 3. Spec prepare — промпт 3

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

````
Python 3.11

I think for now we can run it on Windows

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
Windows vs WSL,
```

What do you mean "vs"?

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
in-process plugins vs separate agent process
```

in-process plugins

Does telegram support message status updates? Like message delivered, read, responder is writing?
How to setup webhook?
````

---

## 4. Spec prepare — промпт 4

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

````
```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
Or ask the course if 3.12 is acceptable (you already have it)
```

Lets use it if I have :D

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
That only meant where the Python process runs.
```

Windows

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
So: you can show writing, not WhatsApp-style delivered/read.
```

Not now

```chat_selection
agent_id: 68a1a49d-1cd1-4c3d-be5f-44fb237a655c
selected_text:
How webhooks work (setup overview)
```

I have no static constant API, so lets forget about it for now.
````

---

## 5. Spec prepare — промпт 5

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

```
What about llm model? Which model and where it simpler to setup?
```

---

## 6. Spec prepare — промпт 6

Чат: `68a1a49d-1cd1-4c3d-be5f-44fb237a655c`

```
prepare spec file
```

После этого агент записал `docs/spec.md` и остановился. Реализации в этом чате не было.

---

## 7. Spec implement — единственный промпт реализации

Чат: `3554930c-b410-40fd-b5f3-7dae195fbff8`

Пустой контекст, только спека в репозитории.

```
implement according to docs/spec.md
```

Follow-up в этом чате не было. Unit-тесты прошли (12 OK). Живой Telegram-прогон — уже в следующем чате.

---

## 8. Bug fix message too long — follow-up после impl (2 промпта)

Чат: `d8ed71db-12d6-44b1-bf63-726225a5ba53`

**Промпт 1** — ошибка с живого прогона (scratch / terminal):

```
I got error:
C:\Users\user\AppData\Roaming\JetBrains\PyCharm2026.1\scratches\scratch_356.txt
```

Содержимое ошибки:

```
RuntimeError: Telegram API HTTP 400: {"ok":false,"error_code":400,"description":"Bad Request: message is too long"}
```

Агент предложил split ≤4096 + unit-тест.

**Промпт 2** — подтверждение фикса:

```
Yes
```

Баг: ответ Ollama длиннее лимита Telegram `sendMessage` (4096). Фикс: `_chunk_text` в `src/channels/telegram.py` + `test_send_splits_long_messages`. Тесты: **13** OK.

---

## По чатам

| Чат | Промптов | Tokens |
| --- | ---: | ---: |
| Spec prepare | 6 | 388 562 |
| Spec implement | 1 | 266 315 |
| Fix issue | 2 | 428 409 |
| **Итого** | **9** | **1 083 286** |
