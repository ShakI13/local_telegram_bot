"""Allowlisted exec runner: curl.exe only, cwd jail, timeout."""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

ALLOWED_BINARIES = frozenset({"curl.exe"})
_LOG_PREVIEW_CHARS = 200


def _preview(text: str, limit: int = _LOG_PREVIEW_CHARS) -> str:
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


class AllowlistedExecRunner:
    """Run allowlisted CLI commands inside a working-directory jail."""

    def __init__(
        self,
        *,
        cwd: Path | str | None = None,
        timeout: float = 30.0,
        allowed: frozenset[str] = ALLOWED_BINARIES,
    ) -> None:
        self._cwd = Path(cwd) if cwd is not None else Path.cwd()
        self._timeout = timeout
        self._allowed = {name.lower() for name in allowed}

    def __call__(self, command: str) -> str:
        return self.run(command)

    def run(self, command: str) -> str:
        if not command.strip():
            return "Tool error: empty exec command."

        try:
            argv = shlex.split(command, posix=True)
        except ValueError as exc:
            return f"Tool error: could not parse command: {exc}"

        if not argv:
            return "Tool error: empty exec command."

        raw_binary = argv[0]
        if "/" in raw_binary or "\\" in raw_binary or ".." in raw_binary:
            return (
                "Tool error: exec binary must be an allowlisted bare name "
                f"(got {raw_binary!r})."
            )

        binary = Path(raw_binary).name.lower()
        if binary not in self._allowed:
            return (
                f"Tool error: binary {raw_binary!r} is not allowlisted. "
                f"Allowed: {', '.join(sorted(self._allowed))}."
            )

        for arg in argv[1:]:
            if _looks_like_path_escape(arg):
                return (
                    "Tool error: exec argument escapes the working-directory "
                    f"jail ({arg!r})."
                )

        argv = [binary, *argv[1:]]

        if not self._cwd.is_dir():
            self._cwd.mkdir(parents=True, exist_ok=True)

        logger.info(
            "exec start argv=%r cwd=%s timeout=%s",
            argv,
            self._cwd,
            self._timeout,
        )
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                argv,
                cwd=str(self._cwd.resolve()),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info("exec timeout after %.0fms argv=%r", elapsed_ms, argv)
            return (
                f"Tool error: exec timed out after {self._timeout}s "
                f"(cwd jail: {self._cwd})."
            )
        except OSError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "exec OSError after %.0fms argv=%r: %s",
                elapsed_ms,
                argv,
                exc,
            )
            return f"Tool error: failed to start process: {exc}"

        elapsed_ms = (time.perf_counter() - started) * 1000
        result = (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        logger.info(
            "exec done ms=%.0f exit_code=%s result_chars=%d preview=%r",
            elapsed_ms,
            completed.returncode,
            len(result),
            _preview(result),
        )
        return result


def _looks_like_path_escape(arg: str) -> bool:
    """Reject local path escapes; allow normal URLs and curl flags."""
    if arg.startswith("-"):
        return False
    lower = arg.lower()
    if lower.startswith(("http://", "https://", "ftp://")):
        return False
    if ".." in arg:
        return True
    if re.match(r"^[A-Za-z]:[\\/]", arg):
        return True
    if arg.startswith("\\\\") or arg.startswith("//"):
        return True
    return False
