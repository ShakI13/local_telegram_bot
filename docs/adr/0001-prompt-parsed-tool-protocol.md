# Prompt-parsed XML Tool Protocol (not Ollama native tools)

For the minimal agent homework we drive `exec` by parsing XML-ish tags (`<exec>...</exec>`) from the model text, instead of Ollama native `/api/chat` `tool_calls`. Native tools are available on Ollama but Qwen3 tool-calling is brittle (especially with thinking), and a tiny prompt protocol is easier to debug and grade on `qwen3:1.7b`. We can add a native-tools adapter later without changing the Harness’s outer loop shape.
