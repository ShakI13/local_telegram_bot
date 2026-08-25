"""Channel plugin contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class InboundMessage:
    chat_id: int | str
    text: str
    raw: Any = None


class Channel(Protocol):
    def poll(self) -> list[InboundMessage]:
        """Receive normalized inbound text messages (may block briefly)."""

    def send(self, chat_id: int | str, text: str) -> None:
        """Send a text reply to the given chat."""
