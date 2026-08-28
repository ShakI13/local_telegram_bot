# Minimal Telegram Agent

Domain language for the Telegram bot evolving into a minimal tool-using agent (homework: harness, `exec`, Skills, long-context chats).

## Language

**Chat**:
A durable conversation tied to one Telegram `chat_id`, whose message history is one long context until reset.
_Avoid_: Session (unless we later mean a named sub-conversation), thread

**/new**:
A user command that starts a fresh Chat for that Telegram `chat_id` by clearing its history.
_Avoid_: reset (as a product term), clear history (as the user-facing name)

**Chat Store**:
On-disk persistence of each Chat’s history (and Summary) at `.scratch/chats/<chat_id>.json`, so context survives bot restarts.
_Avoid_: database (unless we later choose one), session file

**Harness**:
The code that runs the Agentic Loop: call the model, run tools, feed results back, until a final answer or a step limit.
_Avoid_: orchestrator (keep for the outer Telegram poll/send wiring), runner

**Agentic Loop**:
One turn’s cycle of model ↔ tool calls until the model returns a final user-facing reply or hits Max Steps.
_Avoid_: conversation loop (that is Chat history across turns)

**Max Steps**:
Hard cap on model↔tool iterations inside one Agentic Loop; fixed at **8** for this homework.
_Avoid_: Max Retries (unless we mean failed HTTP retries, which are separate)

**exec**:
The universal tool that runs a shell/CLI command and returns its output to the model. v1 allowlist is **`curl.exe` only**, plus working-directory jail, timeout, and captured stdout/stderr.
_Avoid_: shell, terminal, subprocess (as the tool’s public name)

**Skill**:
A markdown instruction file the agent can use (Type A: how to use a CLI/API; Type B: a multi-step routine). Runtime Skills live under `src/skills/` and are rediscovered each turn.
_Avoid_: prompt file, AGENTS.md, `.agents/skills` (those are for Cursor engineers, not the runtime agent)

**Skill Catalog**:
The short per-turn listing of available Skills (name + one-line description/path) injected into the prompt. Full Skill bodies are not injected; the harness loads a Skill file when the model requests it (not via `exec`).
_Avoid_: skill index (unless we mean the same thing later), system prompt dump

**Type A Skill**:
A Skill that teaches rules for calling a specific CLI or HTTP/API. First homework Skill: **curl → wttr.in** (`src/skills/…`).
_Avoid_: tool definition (tools are code; Skills are instructions)

**Type B Skill**:
A Skill that teaches a fixed sequence of actions (e.g. weather → calendar → summary).
_Avoid_: workflow, playbook (unless we adopt one later)

**Context Budget**:
The soft character-budget limit on how much prompt (Chat history + catalog + tool results) may be sent to the model in one call. When over budget, older turns are folded into a Summary; if the Summary is still too large, its oldest portion is forgotten.

**Summary**:
A compressed stand-in for older Chat turns, produced when history would exceed the Context Budget. If the Summary itself is still too large, its oldest portion is forgotten (trimmed) before recent verbatim turns are dropped.
_Avoid_: memory compression, RAG

**Tool Protocol**:
Prompt-parsed XML-ish tags (not Ollama native `tool_calls`). `exec` is requested with `<exec>...</exec>`; a Skill is requested with `<skill>skill_name</skill>` (harness reads `src/skills/<skill_name>.md`). Text outside tool tags is the final user-facing answer.
_Avoid_: function calling, native tools (rejected for v1 of the agent homework)

**Turn Failure Notice**:
A fixed assistant message persisted on the Chat (and sent to the user) when a turn cannot finish normally — e.g. Inference unavailable, or an unexpected Harness error — including any partial Agentic Loop rows already produced.
_Avoid_: error reply (vague), exception message (raw stacks are not user-facing)
