# 05: Context Budget — Summary then trim

**What to build:** When the assembled prompt would exceed the Context Budget (~12k characters), older Chat turns are folded into a Summary while recent turns stay verbatim; if the Summary is still too large, its oldest portion is trimmed. Long Chats keep working without blowing the model window; summarization is stubbable in tests.

**Blocked by:** 04 Allowlisted exec (curl) in the Agentic Loop

**Status:** done

- [x] Context Budget is measured in characters on the assembled prompt (Chat + Skill Catalog + tool results as applicable)
- [x] Over budget → summarize older turns into a Summary; keep recent turns verbatim
- [x] If Summary is still too large → forget/trim the oldest portion of the Summary before dropping recent verbatim turns
- [x] Chat Store persists Summary along with history so restart does not wipe compression state incorrectly
- [x] Summarizer is replaceable/fakeable so budget tests do not require a real LLM every time
- [x] Tests assert external Agent behavior (reply still produced; history/Summary effects) with a temporary Chat Store
