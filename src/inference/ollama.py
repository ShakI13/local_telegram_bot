"""Ollama REST inference via stdlib HTTP."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class OllamaInference:
    """Stateless calls to Ollama `/api/generate`."""

    def __init__(
        self,
        model: str = "qwen3:1.7b",
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 300.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def generate(self, prompt: str) -> str:
        url = f"{self._base_url}/api/generate"
        body = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        reply = payload.get("response")
        if reply is None:
            raise RuntimeError(f"Ollama response missing 'response': {payload}")
        return str(reply)
