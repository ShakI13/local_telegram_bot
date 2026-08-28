# Spec: Minimal Agent

Status: ready-for-agent

Feature slug: `minimal-agent`

## Problem Statement

The existing Telegram bot only does one-shot replies: each message goes to the local model and back, with no memory, no tools, and no reusable instructions. For the homework, that is not enough. The operator needs the same bot to behave as a small autonomous agent: keep a long Chat per Telegram user, reset it with `/new`, follow Skill instructions, and run real CLI actions (starting with curl to wttr.in) through a bounded Agentic Loop—without the process hanging in an endless tool cycle or blowing the model’s Context Budget.

## Solution

Evolve the current bot in place. Keep Telegram I/O and Ollama as adapters. Replace the one-shot “generate and reply” path with a deep **Agent** module: load/save Chat from a Chat Store, inject a fresh Skill Catalog each turn, run an Agentic Loop (Max Steps = 8) that understands the Tool Protocol (`<exec>…</exec>`, `<skill>skill_name</skill>`), enforce `exec` allowlisting and jail, apply Context Budget (Summary, then trim), and return one final user-facing answer to Telegram.

## User Stories

1. As a Telegram user, I want to send a normal text message and get a useful reply, so that the bot still works as a conversational assistant.
2. As a Telegram user, I want later messages in the same chat to remember earlier ones, so that I do not have to repeat context every turn.
3. As a Telegram user, I want `/new` to start a fresh Chat, so that I can discard old context when I change topic.
4. As a Telegram user, I want `/new` to clear only my Chat, so that other people’s conversations are unaffected.
5. As a Telegram user, I want the bot to ignore or no-op non-text updates the same way as today, so that stickers and photos do not break the agent.
6. As an allowlisted operator, I want only my chat IDs to reach the Agent, so that strangers cannot run `exec` on my machine.
7. As an allowlisted operator, I want the agent to call `curl` for weather via wttr.in when asked, so that I get live data instead of a hallucinated forecast.
8. As an allowlisted operator, I want the agent to follow a Type A Skill for wttr.in, so that curl flags and URLs stay consistent.
9. As an allowlisted operator, I want a Skill Catalog refreshed every turn, so that adding or editing a Skill file is picked up without restarting the bot.
10. As an allowlisted operator, I want the model to load a Skill only when it emits `<skill>skill_name</skill>`, so that full Skill bodies do not waste Context Budget every turn.
11. As an allowlisted operator, I want `<exec>…</exec>` to run only allowlisted binaries (curl), so that the model cannot launch arbitrary programs.
12. As an allowlisted operator, I want `exec` to run inside a working-directory jail with a timeout, so that runaway or path-escaping commands fail safely.
13. As an allowlisted operator, I want stdout and stderr from `exec` fed back into the Agentic Loop, so that the model can use real command output.
14. As an allowlisted operator, I want rejected `exec` attempts to return a clear tool error to the model, so that it can recover or explain failure instead of hanging.
15. As an allowlisted operator, I want the Agentic Loop to stop at Max Steps = 8, so that a confused model cannot loop forever.
16. As an allowlisted operator, I want a clear user-facing message when Max Steps is hit without a final answer, so that I know the agent gave up safely.
17. As an allowlisted operator, I want text outside tool tags treated as the final answer, so that ordinary replies still work when no tool is needed.
18. As an allowlisted operator, I want multiple tool round-trips in one user turn (skill load then curl then answer), so that Skills plus `exec` compose.
19. As an allowlisted operator, I want Chat history to survive bot restarts, so that I do not lose context when I restart the process.
20. As an allowlisted operator, I want `/new` to clear the persisted Chat Store entry as well as memory, so that restart does not resurrect a cleared Chat.
21. As an allowlisted operator, I want old turns summarized when the prompt would exceed the Context Budget, so that long Chats keep working.
22. As an allowlisted operator, I want an oversized Summary trimmed from the oldest part, so that even a fat Summary cannot blow the window.
23. As an allowlisted operator, I want recent turns kept verbatim when summarizing, so that the latest instructions stay exact.
24. As a course grader, I want at least one Type A Skill checked into the runtime skills directory, so that the homework Skill requirement is visible.
25. As a course grader, I want to see a Harness / Agentic Loop with a hard step cap, so that the “minimal agent” requirement is demonstrable.
26. As a course grader, I want `exec` available as a universal CLI tool, so that the agent can perform real system actions.
27. As a developer, I want Telegram polling/sending unchanged at the channel seam, so that agent work does not rewrite Bot API code.
28. As a developer, I want the Orchestrator to stay a thin allowlist → Agent → send path, so that routing stays simple.
29. As a developer, I want to test the Agent with fake inference and fake command runners, so that CI does not need Telegram, Ollama, or network curl.
30. As a developer, I want failing tool parses or empty tool bodies to be handled without crashing the poll loop, so that one bad model reply does not kill the bot.
31. As a developer, I want Skill names in `<skill>…</skill>` resolved only inside the runtime skills directory, so that path traversal cannot read arbitrary files.
32. As a developer, I want unknown Skill names to return a tool error, so that the model can correct itself.
33. As a developer, I want non-allowlisted `exec` commands rejected before subprocess start, so that safety checks are not racey.
34. As a Telegram user, I want long model replies still chunked by the channel if needed, so that Telegram length limits do not break delivery.
35. As an allowlisted operator, I want the agent to use the same local Ollama model configuration as today, so that I do not need a new provider to try the homework.
36. As an allowlisted operator, I want a turn with only `/new` to acknowledge reset without calling tools, so that reset stays cheap and predictable.
37. As a developer, I want Context Budget measured on the assembled prompt (characters), so that overflow handling is deterministic in tests.
38. As a developer, I want Summary creation to be replaceable/fakeable in tests, so that budget tests do not require a real LLM summarizer every time.
39. As an allowlisted operator, I want tool results to become part of the Chat history for that turn’s loop, so that the model sees what it just did.
40. As an allowlisted operator, I want concurrent chats from different `chat_id`s to keep separate Chat Stores, so that contexts never mix.

## Implementation Decisions

- Evolve the existing bot in place; do not start a parallel project.
- **Primary seam: Agent.** Orchestrator calls Agent with chat id + user text and receives the final reply string. Agent owns Chat load/save, `/new`, Skill Catalog, Context Budget / Summary, Agentic Loop, Tool Protocol, `exec`, and Skill file loads.
- Orchestrator remains responsible for channel poll/send and chat-id allowlisting; it does not implement the loop.
- Channel adapters stay as they are (Telegram long polling, send, chunking).
- Inference stays behind the existing inference plugin idea; widen only as needed so the Agent can send a multi-message / multi-turn prompt string (or message list) assembled from Chat + catalog + tool results. Prefer keeping a single “complete this prompt / messages” call surface rather than leaking loop details into the Ollama adapter.
- Tool calling is **prompt-parsed**, not Ollama native `tool_calls` (see ADR 0001). Wire format:
  - `<exec>…</exec>` — command body for the exec runner
  - `<skill>skill_name</skill>` — harness loads that Skill’s markdown from the runtime skills directory
  - Text outside tags — final user-facing answer when the loop should stop
- Max Steps = 8 per user message (one Agentic Loop).
- `exec`: allowlist **curl.exe only**; working-directory jail; timeout (~30s); capture stdout/stderr; reject path escape and non-allowlisted binaries before start.
- Skill load is **not** via shell: `<skill>` is handled by the harness reading a file under the runtime skills directory (`src/skills/`).
- Each Agent turn rescans the runtime skills directory and injects a **Skill Catalog** (name + one-line description) into the prompt; full bodies only after `<skill>`.
- First shipping Skill: Type A — curl → wttr.in.
- Chat identity = Telegram `chat_id`. `/new` (whitespace-trimmed exact match) clears that Chat in memory and in the Chat Store.
- Chat Store: on-disk JSON per chat id under `.scratch/chats/`, surviving process restart (gitignored scratch).
- Context Budget: character budget on the assembled prompt (default ~12k). Over budget → summarize older turns into a Summary, keep recent turns verbatim; if Summary still too large → forget/trim oldest portion of the Summary (see ADR 0002).
- Summarization may call the model or a dedicated summarizer function behind the Agent; tests must be able to stub it.
- Domain vocabulary from `CONTEXT.md` is normative for names (Chat, Harness, Agentic Loop, Max Steps, exec, Skill, Skill Catalog, Context Budget, Summary, Tool Protocol, Chat Store).

## Testing Decisions

- Good tests assert **external behavior** at the Agent seam (and thin Orchestrator wiring): given inbound text and scripted model outputs / command results, assert the user-visible reply, persisted Chat effects, and whether `exec` was attempted—not private helper structure.
- Prefer the highest seam: **Agent** with fake Inference, fake/stub exec runner, and temporary directories for Chat Store and skills.
- Orchestrator tests keep using FakeChannel-style doubles; swap FakeInference for a fake Agent or keep Inference fake only where the Orchestrator path stays trivial.
- Prior art: `tests/test_bot.py` (unittest, mocks for HTTP, FakeChannel / FakeInference). Stay on unittest; no live Telegram/Ollama required for the suite.
- Suggested behavior slices (not exhaustive): `/new` clears store; second message sees first without `/new`; catalog lists a dropped-in Skill file; `<skill>` returns file body; `<exec>` with curl allowlist invoked; non-curl `exec` rejected; Max Steps stops the loop; Context Budget triggers Summary then trim; unknown skill name errors; path traversal in skill name rejected.
- Do not require real network curl in unit tests; stub the exec runner. Optional manual smoke: allowlisted Telegram chat + Ollama + wttr.in.

## Out of Scope

- Native Ollama `tool_calls` / `/api/chat` tools API (may revisit later).
- Type B Skills (morning routine, gog cli, mail) in this delivery—only Type A wttr.in is required now.
- Extra `exec` binaries beyond curl.exe (no `type`, no arbitrary PowerShell).
- Prompt-injection hardening beyond allowlist/jail/timeout and skills-directory confinement.
- Webhooks, typing indicators, non-Telegram channels, LM Studio provider.
- Separate OS process for the agent.
- Multi-user admin UI, auth beyond existing allowlist.
- Vector memory / RAG.
- Streaming tokens to Telegram.
- Summarize-only or forget-only strategies (hybrid is in scope; pure alternatives are not).
- Changing the Matt/Cursor `.agents/skills` tree (unrelated to runtime Skills).

## Further Notes

- Paper trail: `CONTEXT.md`, `docs/adr/0001-prompt-parsed-tool-protocol.md`, `docs/adr/0002-context-budget-summarize-then-trim.md`.
- v1 product spec for the one-shot bot remains `docs/spec.md`; this document supersedes it for agent behavior where they conflict (memory, tools, loop).
- After this spec: split into tracer-bullet tickets with `/to-tickets` (blockers first), then `/implement` per ticket in fresh context.
- Defaults locked in grilling unless revisited: Context Budget ~12k characters; exec timeout ~30s; `/new` exact match after trim.
