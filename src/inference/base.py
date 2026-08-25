"""Inference plugin contract."""

from __future__ import annotations

from typing import Protocol


class Inference(Protocol):
    def generate(self, prompt: str) -> str:
        """Return a one-shot model reply for `prompt` (no conversation memory)."""
