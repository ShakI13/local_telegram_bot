# Отчёт: minimal-agent (`simple_agent`)

## Метрики

| Метрика | Значение |
| --- | --- |
| Размер SPEC (токенов, o200k_base) | 2740 (12066 символов; на момент impl и сейчас — без изменений) |
| Успешный first-run (живой Telegram→Agent→Ollama+tools) | нет (после двух фикс-чатов — да: weather via skill+exec) |
| Качество уточняющих вопросов | хорошее |
| Количество промптов (task-чаты) | 25 |
| Количество багов | 3 |
| Общее количество потраченных токенов | **7 778 165** |

Spent = Usage Total Tokens по JSONL-интервалам user-промптов − scaffolding × turns (Context Usage без Conversation). Cloud Agent rows исключены. Часовой пояс транскриптов: UTC+3.

## Артефакты

| Артефакт | Путь / ссылка |
| --- | --- |
| Terminal / run log | `docs/run_log.txt` — **отсутствует** (не изобретать) |
| SPEC | `docs/spec_agent.md` |
| Extra prompts | `docs/extra_prompts_agent.md` |
| Counts | этот файл (`docs/REPORT_AGENT.md`) |

## SPEC

Написан в чате Spec agent prepare (сохранён по запросу в `docs/spec_agent.md`). На момент реализации и сейчас: **2740** токенов (`tiktoken` `o200k_base`). Содержание не менялось после impl.

## First-run

1. Impl-чат: пять тикетов `minimal-agent` закрыты; `unittest` — 37 OK; README обновлён.
2. Живой прогон: Ollama выключен → traceback в логе, **тишина в Telegram** (баг 1).
3. После старта Ollama: запрос погоды — модель **выдала наративом** skill/curl/результат текстом без тегов (баг 2).
4. После фикса протокола: `exec` падал на UTF-8 stdout (баг 3).
5. После обоих фикс-чатов: `/new` + «Какая погода в Москве?» → `<skill>wttr</skill>` → `<exec>curl…</exec>` → ответ с реальной погодой.

## Уточняющие вопросы

Prep-чат (grill) закрыл до кода: evolve in place; Chat per `chat_id` + `/new`; Type A wttr Skill; Skill Catalog каждый ход; Summary-then-trim; prompt-parsed `<exec>`/`<skill>`; allowlist `curl.exe` only; Chat Store `.scratch/chats/`; Max Steps = 8; ADRs на Tool Protocol и Context Budget. Полный список: `docs/extra_prompts_agent.md`.

## Баги

1. **Тишина при падении Inference.** Ollama `ConnectionRefused` логировался в Orchestrator, `send` не вызывался. Фикс: Turn Failure Notices (Agent возвращает текст; Orchestrator catch-all) + INFO-логи по швам; commit `b9e1b0e`.
2. **Наратив вместо Tool Protocol.** Модель писала «Loading skill… Running CLI…» без `<skill>`/`<exec>` — harness считал это финальным ответом. Фикс: отклонять наратив tool-use. Commit `4e4d5f8`.
3. **`UnicodeDecodeError` на stdout `exec`.** `subprocess` читал pipe в cp1251; wttr.in отдавал UTF-8. Фикс: decode stdout/stderr как UTF-8. Commit `4e4d5f8`.

## По чатам

| Чат | Промптов | Turns | Tokens |
| --- | ---: | ---: | ---: |
| Spec agent prepare | 8 | 9 | 897 436 |
| Spec agent tickets | 2 | 3 | 296 995 |
| Spec agent implementation | 2 | 4 | 3 096 214 |
| Fixing bugs | 8 | 11 | 2 310 024 |
| Agent tool usage analysis | 5 | 5 | 1 177 496 |
| **Итого** | **25** | **32** | **7 778 165** |
