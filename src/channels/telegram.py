"""Telegram Bot API channel via stdlib HTTPS (long polling)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .base import InboundMessage

logger = logging.getLogger(__name__)

# Telegram Bot API limit for sendMessage text.
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
_LOG_PREVIEW_CHARS = 200


def _preview(text: str, limit: int = _LOG_PREVIEW_CHARS) -> str:
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _chunk_text(text: str, limit: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into chunks of at most `limit` characters.

    Prefers breaks after newlines, then spaces; hard-splits only when needed.
    Joining the returned chunks recreates the original string.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        if length - start <= limit:
            chunks.append(text[start:])
            break
        end = start + limit
        window = text[start:end]
        rel = window.rfind("\n")
        if rel <= 0:
            rel = window.rfind(" ")
        if rel > 0:
            end = start + rel + 1
        chunks.append(text[start:end])
        start = end
    return chunks


class TelegramChannel:
    """Long-polling Telegram channel (`getUpdates` / `sendMessage`)."""

    def __init__(
        self,
        token: str,
        *,
        poll_timeout: int = 25,
        api_base: str = "https://api.telegram.org",
    ) -> None:
        if not token:
            raise ValueError("Telegram bot token is required")
        self._token = token
        self._poll_timeout = poll_timeout
        self._api_base = api_base.rstrip("/")
        self._offset: int | None = None

    def _url(self, method: str) -> str:
        return f"{self._api_base}/bot{self._token}/{method}"

    def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        url = self._url(method)
        data = None
        headers = {"Accept": "application/json"}
        if params is not None:
            body = json.dumps(params).encode("utf-8")
            data = body
            headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method="GET")

        wait = timeout if timeout is not None else max(30.0, float(self._poll_timeout) + 5.0)
        logger.info("telegram %s start", method)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=wait) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.info(
                "telegram %s HTTP %s after %.0fms detail_preview=%r",
                method,
                exc.code,
                (time.perf_counter() - started) * 1000,
                _preview(detail),
            )
            raise RuntimeError(f"Telegram API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            logger.info(
                "telegram %s URLError after %.0fms: %s",
                method,
                (time.perf_counter() - started) * 1000,
                exc,
            )
            raise RuntimeError(f"Telegram API request failed: {exc}") from exc

        if not payload.get("ok"):
            logger.info(
                "telegram %s API not ok payload_preview=%r",
                method,
                _preview(str(payload)),
            )
            raise RuntimeError(f"Telegram API error: {payload}")
        logger.info(
            "telegram %s done ms=%.0f",
            method,
            (time.perf_counter() - started) * 1000,
        )
        return payload

    def poll(self) -> list[InboundMessage]:
        params: dict[str, Any] = {"timeout": self._poll_timeout}
        if self._offset is not None:
            params["offset"] = self._offset

        # getUpdates accepts query params; POST JSON also works on Bot API.
        url = self._url("getUpdates")
        query = urllib.parse.urlencode(params)
        full_url = f"{url}?{query}"
        req = urllib.request.Request(
            full_url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        wait = max(30.0, float(self._poll_timeout) + 5.0)
        logger.info("telegram getUpdates start offset=%s", self._offset)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=wait) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.info(
                "telegram getUpdates HTTP %s after %.0fms detail_preview=%r",
                exc.code,
                (time.perf_counter() - started) * 1000,
                _preview(detail),
            )
            raise RuntimeError(f"Telegram API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            logger.info(
                "telegram getUpdates URLError after %.0fms: %s",
                (time.perf_counter() - started) * 1000,
                exc,
            )
            raise RuntimeError(f"Telegram API request failed: {exc}") from exc

        if not payload.get("ok"):
            logger.info(
                "telegram getUpdates API not ok payload_preview=%r",
                _preview(str(payload)),
            )
            raise RuntimeError(f"Telegram API error: {payload}")

        messages: list[InboundMessage] = []
        for update in payload.get("result") or []:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._offset = update_id + 1

            message = update.get("message") or update.get("edited_message")
            if not isinstance(message, dict):
                continue
            text = message.get("text")
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if not text or chat_id is None:
                continue
            messages.append(
                InboundMessage(chat_id=chat_id, text=str(text), raw=update)
            )
        logger.info(
            "telegram getUpdates done ms=%.0f inbound=%d",
            (time.perf_counter() - started) * 1000,
            len(messages),
        )
        return messages

    def send(self, chat_id: int | str, text: str) -> None:
        chunks = _chunk_text(text)
        logger.info(
            "telegram sendMessage chat_id=%s text_chars=%d chunks=%d preview=%r",
            chat_id,
            len(text),
            len(chunks),
            _preview(text),
        )
        for chunk in chunks:
            self._request(
                "sendMessage",
                {"chat_id": chat_id, "text": chunk},
                timeout=60.0,
            )
