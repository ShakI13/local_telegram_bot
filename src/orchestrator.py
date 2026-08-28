"""Inbound text → Agent → channel reply (allowlist at this seam)."""

from __future__ import annotations

import logging

from .agent import Agent
from .channels.base import Channel, InboundMessage

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        channel: Channel,
        agent: Agent,
        *,
        allowed_chat_ids: frozenset[str] | None = None,
    ) -> None:
        self._channel = channel
        self._agent = agent
        # None/empty = allow all chats (backward-compatible default).
        self._allowed_chat_ids = allowed_chat_ids or frozenset()

    def _is_allowed(self, chat_id: int | str) -> bool:
        if not self._allowed_chat_ids:
            return True
        return str(chat_id) in self._allowed_chat_ids

    def handle_message(self, message: InboundMessage) -> None:
        if not self._is_allowed(message.chat_id):
            logger.warning(
                "Ignoring message from non-allowlisted chat_id=%s",
                message.chat_id,
            )
            return
        reply = self._agent.handle(message.chat_id, message.text)
        self._channel.send(message.chat_id, reply)

    def run_once(self) -> int:
        """Poll once and process all inbound messages. Returns how many were handled."""
        messages = self._channel.poll()
        for message in messages:
            try:
                self.handle_message(message)
            except Exception:
                logger.exception(
                    "Failed to handle message for chat_id=%s", message.chat_id
                )
        return len(messages)

    def run(self) -> None:
        logger.info("Orchestrator started (allowlist → Agent → send)")
        while True:
            self.run_once()
