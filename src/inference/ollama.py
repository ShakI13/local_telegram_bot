"""Ollama REST inference via stdlib HTTP."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_LOG_PREVIEW_CHARS = 200


def _preview(text: str, limit: int = _LOG_PREVIEW_CHARS) -> str:
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


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
        logger.info(
            "ollama generate start url=%s model=%s prompt_chars=%d preview=%r",
            url,
            self._model,
            len(prompt),
            _preview(prompt),
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw)
        except urllib.error.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            detail = exc.read().decode("utf-8", errors="replace")
            logger.info(
                "ollama generate HTTP %s after %.0fms detail_preview=%r",
                exc.code,
                elapsed_ms,
                _preview(detail),
            )
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "ollama generate URLError after %.0fms: %s",
                elapsed_ms,
                exc,
            )
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "ollama generate failed after %.0fms",
                elapsed_ms,
                exc_info=True,
            )
            raise

        reply = payload.get("response")
        if reply is None:
            logger.info(
                "ollama generate missing 'response' payload_preview=%r",
                _preview(str(payload)),
            )
            raise RuntimeError(f"Ollama response missing 'response': {payload}")
        reply_text = str(reply)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "ollama generate done ms=%.0f reply_chars=%d preview=%r",
            elapsed_ms,
            len(reply_text),
            _preview(reply_text),
        )
        return reply_text
