# Context Budget: summarize, then trim the Summary

When a Chat’s prompt would exceed the Context Budget, older turns are compressed into a Summary before the next model call. If that Summary itself is still too large, its oldest portion is forgotten (trimmed). We rejected pure sliding-window forget-only (loses long-range intent too early) and summarize-only (a bloated Summary can still blow the window). Persistence of Chat + Summary lives in `.scratch/chats/<chat_id>.json` so a bot restart does not wipe context.
