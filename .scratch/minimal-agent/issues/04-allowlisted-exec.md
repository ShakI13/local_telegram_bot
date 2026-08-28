# 04: Allowlisted exec (curl) in the Agentic Loop

**What to build:** `<exec>…</exec>` runs only allowlisted curl.exe inside a working-directory jail with a timeout; stdout/stderr (and clear rejection errors) feed back into the Chat for that turn’s loop so Skill load + curl + final answer can compose in one user turn.

**Blocked by:** 03 Agentic Loop, Skill Catalog, and skill loads

**Status:** done

- [x] `<exec>` invokes only the allowlisted curl binary; non-allowlisted commands are rejected before subprocess start with a clear tool error to the model
- [x] exec runs in a working-directory jail with a timeout (~30s); path escape and runaway commands fail safely
- [x] Captured stdout and stderr are appended into the Chat history for that turn’s Agentic Loop
- [x] Rejected or failed exec attempts return a tool error the model can recover from (no hang, no poll-loop crash)
- [x] One user turn can compose multiple tool round-trips (e.g. skill load then curl then final answer)
- [x] Tests stub the exec runner (no real network curl required); assert whether exec was attempted and what the user-visible reply is
