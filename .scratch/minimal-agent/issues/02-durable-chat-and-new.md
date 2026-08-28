# 02: Durable Chat and /new

**What to build:** Each Telegram chat_id gets a durable Chat in the Chat Store. Later messages remember earlier ones; `/new` clears only that user’s Chat in memory and on disk so a restart cannot resurrect it; a turn that is only `/new` acknowledges reset without calling tools.

**Blocked by:** 01 Prefactor: Agent seam behind Orchestrator

**Status:** done

- [x] Agent loads and saves Chat per chat_id under the Chat Store (`.scratch/chats/`), surviving process restart
- [x] Without `/new`, a second message’s prompt includes earlier turns so the reply can use prior context
- [x] `/new` (whitespace-trimmed exact match) clears that chat_id’s Chat in memory and in the Chat Store; other chat_ids are unaffected
- [x] A turn that is only `/new` returns a reset acknowledgment and does not invoke Inference or tools
- [x] Concurrent different chat_ids keep separate Chat Store entries (contexts never mix)
- [x] Tests assert persisted Chat effects at the Agent seam with a temporary Chat Store directory
