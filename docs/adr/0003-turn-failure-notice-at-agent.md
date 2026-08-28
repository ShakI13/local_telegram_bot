# Turn Failure Notice owned by the Agent

When a turn cannot finish (Inference down, unexpected Harness error), the Agent appends a Turn Failure Notice (keeping any partial Agentic Loop rows), saves the Chat, and returns that string so the Orchestrator sends it on the normal path. The Orchestrator’s exception handler remains a backstop only for failures outside a successful `handle` return (e.g. channel `send`), so the user is never left with silence. We rejected Orchestrator-only catch-and-send without Chat persistence because it left failed user turns missing from the Chat Store.
