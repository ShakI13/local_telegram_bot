"""Inbound text → inference → channel reply (no memory)."""

from __future__ import annotations

import logging

from .channels.base import Channel, InboundMessage
from .inference.base import Inference

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, channel: Channel, inference: Inference) -> None:
        self._channel = channel
        self._inference = inference

    def handle_message(self, message: InboundMessage) -> None:
        reply = self._inference.generate(message.text)
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
        logger.info("Orchestrator started (stateless one-shot replies)")
        while True:
            self.run_once()
