"""Inbound text → Agent → channel reply (allowlist at this seam)."""

from __future__ import annotations

import logging

from .agent import GENERIC_FAILURE_NOTICE, Agent
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
            logger.info(
                "Ignoring message from non-allowlisted chat_id=%s",
                message.chat_id,
            )
            return
        logger.info(
            "orchestrator inbound chat_id=%s text_chars=%d",
            message.chat_id,
            len(message.text),
        )
        reply = self._agent.handle(message.chat_id, message.text)
        self._channel.send(message.chat_id, reply)
        logger.info(
            "orchestrator sent chat_id=%s reply_chars=%d",
            message.chat_id,
            len(reply),
        )

    def run_once(self) -> int:
        """Poll once and process all inbound messages. Returns how many were handled."""
        messages = self._channel.poll()
        for message in messages:
            try:
                self.handle_message(message)
            except Exception:
                logger.info(
                    "Failed to handle message for chat_id=%s; sending backstop reply",
                    message.chat_id,
                    exc_info=True,
                )
                try:
                    self._channel.send(message.chat_id, GENERIC_FAILURE_NOTICE)
                except Exception:
                    logger.info(
                        "Failed to send backstop reply for chat_id=%s",
                        message.chat_id,
                        exc_info=True,
                    )
        return len(messages)

    def run(self) -> None:
        logger.info("Orchestrator started (allowlist → Agent → send)")
        while True:
            self.run_once()
