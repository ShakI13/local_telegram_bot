# wttr

Fetch current weather from wttr.in using curl.

## How to call

Use the exec tool with curl only. Prefer a concise one-line forecast:

```text
curl.exe -s "https://wttr.in/London?format=3"
```

Replace `London` with the city the user asked about (URL-encode spaces as `+`).

For a short multi-line report:

```text
curl.exe -s "https://wttr.in/London?0q"
```

## Rules

- Use `curl.exe` only (no other binaries).
- Do not invent weather numbers; run curl and base the reply on stdout.
- After you have the output, answer the user in plain text (no tool tags).
