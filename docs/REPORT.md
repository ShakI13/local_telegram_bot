# Отчёт: local_telegram_bot

## Метрики

| Метрика | Значение |
| --- | --- |
| Размер SPEC (токенов, ≈chars/4) | ~1411 (на момент impl и сейчас — без изменений) |
| Успешный first-run (живой Telegram→Ollama) | нет |
| Качество уточняющих вопросов | хорошее |
| Количество промптов (task-чаты) | 9 |
| Количество багов | 1 |
| Общее количество потраченных токенов | **1 083 286** |

## Артефакты

| Артефакт | Путь / ссылка |
| --- | --- |
| Terminal / run log | `docs/run_log.txt` (приложить лог финального прогона) |
| SPEC | `docs/spec.md` |
| Extra prompts | `docs/extra_prompts.md` |
| Counts | этот файл (`docs/REPORT.md`) |

## SPEC

Написан в чате prep (14:50 UTC+3). На момент реализации и сейчас: **~1411** токенов (5644 символа, оценка chars/4). Содержание не менялось после impl.

## First-run

1. Impl-чат: `unittest` — 12 тестов OK; код по `docs/spec.md` собран.
2. Живой прогон: ответ Ollama длиннее лимита Telegram → ошибка `message is too long` (см. баг).
3. После фикса чанкинга — повторный прогон (лог → `docs/run_log.txt`).

## Уточняющие вопросы

Prep-чат закрыл до кодирования: Python 3.12, Windows, long polling, in-process plugins, stdlib HTTP + `python-dotenv`, Ollama + `qwen3:1.7b`, Telegram как первый channel-плагин, без webhook/typing/memory. Вопросы по стеку и архитектуре — по делу, без лишней воды. Полный список: `docs/extra_prompts.md`.

## Баги

1. **Telegram `message is too long` (лимит 4096).** Длинный ответ модели уходил одним `sendMessage`. Фикс: `_chunk_text` + последовательная отправка чанков; unit-тест на split.

## По чатам

| Чат | Промптов | Tokens |
| --- | ---: | ---: |
| Spec prepare | 6 | 388 562 |
| Spec implement | 1 | 266 315 |
| Fix issue | 2 | 428 409 |
| **Итого** | **9** | **1 083 286** |
