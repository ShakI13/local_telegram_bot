# 03: Agentic Loop, Skill Catalog, and skill loads

**What to build:** The Agent runs a Harness Agentic Loop (Max Steps = 8) with the prompt-parsed Tool Protocol. Each turn injects a fresh Skill Catalog; `<skill>name</skill>` loads that Skill’s markdown from the runtime skills directory; text outside tool tags is the final user-facing answer; hitting Max Steps without a final answer yields a clear user message. A Type A wttr.in Skill is checked into the runtime skills directory.

**Blocked by:** 02 Durable Chat and /new

**Status:** done

- [x] Each Agent turn rescans the runtime skills directory and injects a Skill Catalog (name + one-line description) into the prompt
- [x] Adding or editing a Skill file is picked up on the next turn without restarting the bot
- [x] `<skill>skill_name</skill>` loads the Skill body from the runtime skills directory into the Chat for that turn’s loop (not via exec)
- [x] Unknown Skill names return a tool error to the model; path traversal / names outside the skills directory are rejected
- [x] Text outside tool tags ends the loop as the final user-facing answer
- [x] Agentic Loop stops at Max Steps = 8; if no final answer, the user gets a clear “gave up safely” style message
- [x] Failing tool parses or empty tool bodies do not crash the poll loop
- [x] At least one Type A Skill (curl → wttr.in) is present under the runtime skills directory for graders
- [x] Tests use fake Inference and a temporary skills directory; no live network required
