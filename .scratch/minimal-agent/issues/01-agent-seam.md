# 01: Prefactor: Agent seam behind Orchestrator

**What to build:** Same one-shot Telegram replies as today, but the Orchestrator only does allowlist → Agent → send. Channel and Inference stay adapters; the Agent owns the brain call so later tickets can add Chat, tools, and the Agentic Loop without rewriting poll/send.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Orchestrator no longer calls Inference directly; it calls Agent with chat id + user text and sends the returned reply string
- [x] Agent performs a single Inference completion for ordinary text (behavior parity with the pre-agent bot)
- [x] Allowlisting, non-text ignore/no-op, and channel chunking remain unchanged at the Orchestrator/Channel seam
- [x] Tests cover the Orchestrator → Agent path with fakes (no live Telegram or Ollama)
