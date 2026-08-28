"""Agent: Chat, Harness Agentic Loop, tools, and Context Budget."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from .exec_runner import AllowlistedExecRunner
from .inference.base import Inference

NEW_ACK = "Chat reset. Starting a fresh conversation."
MAX_STEPS = 8
DEFAULT_CONTEXT_BUDGET = 12_000
DEFAULT_EXEC_TIMEOUT = 30.0
DEFAULT_RECENT_KEEP = 4
MAX_STEPS_MESSAGE = (
    "I reached my step limit without a final answer. "
    "Please try again or simplify the request."
)

TOOL_INSTRUCTIONS = """You are a helpful assistant with tools.

Tool Protocol (emit exactly one tool request per step, or a final answer):
- Load a skill: <skill>skill_name</skill>
- Run an allowlisted CLI command: <exec>command</exec>
- Final answer to the user: plain text with no tool tags.

Available skills are listed in the Skill Catalog below. Load a skill before using it.
Only curl.exe is allowed for exec.
"""

Summarizer = Callable[[str], str]
ExecRunner = Callable[[str], str]

_ANY_TOOL_RE = re.compile(
    r"<(skill|exec)>.*?</\1>", re.DOTALL | re.IGNORECASE
)


def _default_summarizer(blob: str) -> str:
    """Deterministic fallback summarizer (tests/prod can inject an LLM)."""
    compact = " ".join(blob.split())
    return compact[:2000]


class Agent:
    """Deep module: Orchestrator calls handle(chat_id, text) → final reply."""

    def __init__(
        self,
        inference: Inference,
        *,
        chat_store_dir: Path | str | None = None,
        skills_dir: Path | str | None = None,
        exec_runner: ExecRunner | None = None,
        summarizer: Summarizer | None = None,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
        recent_keep: int = DEFAULT_RECENT_KEEP,
        max_steps: int = MAX_STEPS,
        exec_timeout: float = DEFAULT_EXEC_TIMEOUT,
        exec_cwd: Path | str | None = None,
    ) -> None:
        self._inference = inference
        self._chat_store_dir = Path(chat_store_dir or ".scratch/chats")
        self._skills_dir = Path(
            skills_dir or Path(__file__).resolve().parent / "skills"
        )
        self._exec_timeout = exec_timeout
        self._exec_cwd = Path(exec_cwd) if exec_cwd is not None else Path.cwd()
        self._exec_runner = exec_runner or AllowlistedExecRunner(
            cwd=self._exec_cwd,
            timeout=self._exec_timeout,
        )
        self._summarizer = summarizer or _default_summarizer
        self._context_budget = context_budget
        self._recent_keep = max(1, recent_keep)
        self._max_steps = max_steps

    def handle(self, chat_id: int | str, text: str) -> str:
        if text.strip() == "/new":
            self._clear_chat(chat_id)
            return NEW_ACK

        chat = self._load_chat(chat_id)
        chat["messages"].append({"role": "user", "content": text})
        # Index of this turn's user message — never fold it (or later loop rows) away.
        turn_start_index = len(chat["messages"]) - 1

        final = self._run_agentic_loop(chat, turn_start_index=turn_start_index)
        self._save_chat(chat_id, chat)
        return final

    def _run_agentic_loop(
        self, chat: dict[str, Any], *, turn_start_index: int
    ) -> str:
        for _ in range(self._max_steps):
            turn_start_index = self._enforce_context_budget(
                chat, turn_start_index=turn_start_index
            )
            prompt = self._assemble_prompt(chat)
            model_text = self._inference.generate(prompt)
            chat["messages"].append({"role": "assistant", "content": model_text})

            tools = self._parse_tools(model_text)
            if not tools:
                return model_text.strip() or model_text

            # One tool per model step (further tags ignored until the next step).
            kind, body = tools[0]
            result = self._dispatch_tool(kind, body)
            chat["messages"].append({"role": "tool", "content": result})

        chat["messages"].append({"role": "assistant", "content": MAX_STEPS_MESSAGE})
        return MAX_STEPS_MESSAGE

    def _enforce_context_budget(
        self, chat: dict[str, Any], *, turn_start_index: int
    ) -> int:
        """Summarize older turns, then trim Summary, until under budget.

        Returns an updated turn_start_index after message list changes.
        """
        for _ in range(1000):
            if len(self._assemble_prompt(chat)) <= self._context_budget:
                return turn_start_index

            messages = chat["messages"]
            protected_tail = max(1, len(messages) - turn_start_index)
            min_keep = max(self._recent_keep, protected_tail)

            if len(messages) > min_keep:
                older = messages[:-min_keep]
                recent = messages[-min_keep:]
                parts: list[str] = []
                existing = (chat.get("summary") or "").strip()
                if existing:
                    parts.append(existing)
                for msg in older:
                    parts.append(
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    )
                chat["summary"] = self._summarizer("\n".join(parts))
                chat["messages"] = recent
                turn_start_index = len(chat["messages"]) - protected_tail
                continue

            summary = chat.get("summary") or ""
            if summary:
                drop = max(len(summary) // 4, 1)
                chat["summary"] = summary[drop:]
                continue

            # Nothing left to fold/trim without dropping the current turn.
            return turn_start_index

        return turn_start_index

    def _parse_tools(self, model_text: str) -> list[tuple[str, str]]:
        if not _ANY_TOOL_RE.search(model_text):
            return []
        tools: list[tuple[str, str]] = []
        for match in re.finditer(
            r"<(skill|exec)>(.*?)</\1>",
            model_text,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            tools.append((match.group(1).lower(), match.group(2)))
        if not tools:
            return [("error", "")]
        return tools

    def _dispatch_tool(self, kind: str, body: str) -> str:
        if kind == "skill":
            return self._load_skill(body.strip())
        if kind == "exec":
            return self._run_exec(body.strip())
        return "Tool error: unknown tool."

    def _load_skill(self, name: str) -> str:
        if not name:
            return "Tool error: empty skill name."
        if "/" in name or "\\" in name or ".." in name or name.startswith("."):
            return f"Tool error: invalid skill name {name!r}."
        stem = name.removesuffix(".md")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", stem):
            return f"Tool error: invalid skill name {name!r}."

        skills_root = self._skills_dir.resolve()
        path = (skills_root / f"{stem}.md").resolve()
        try:
            path.relative_to(skills_root)
        except ValueError:
            return f"Tool error: skill {name!r} is outside the skills directory."

        if not path.is_file():
            return f"Tool error: unknown skill {stem!r}."

        body = path.read_text(encoding="utf-8")
        return f"Skill `{stem}` contents:\n{body}"

    def _run_exec(self, command: str) -> str:
        if not command:
            return "Tool error: empty exec command."
        try:
            return self._exec_runner(command)
        except Exception as exc:  # noqa: BLE001 — surface to model as tool error
            return f"Tool error: exec failed: {exc}"

    def _scan_skill_catalog(self) -> str:
        if not self._skills_dir.is_dir():
            return "(no skills available)"
        lines: list[str] = []
        for path in sorted(self._skills_dir.glob("*.md")):
            name = path.stem
            description = self._skill_one_liner(path)
            lines.append(f"- {name}: {description}")
        return "\n".join(lines) if lines else "(no skills available)"

    def _skill_one_liner(self, path: Path) -> str:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return "(unreadable)"
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            return line[:120]
        return "(no description)"

    def _chat_path(self, chat_id: int | str) -> Path:
        safe = re.sub(r"[^\w.-]", "_", str(chat_id))
        return self._chat_store_dir / f"{safe}.json"

    def _load_chat(self, chat_id: int | str) -> dict[str, Any]:
        path = self._chat_path(chat_id)
        if not path.exists():
            return {"messages": [], "summary": ""}
        data = json.loads(path.read_text(encoding="utf-8"))
        messages = data.get("messages")
        if not isinstance(messages, list):
            messages = []
        summary = data.get("summary") or ""
        return {"messages": messages, "summary": summary}

    def _save_chat(self, chat_id: int | str, chat: dict[str, Any]) -> None:
        self._chat_store_dir.mkdir(parents=True, exist_ok=True)
        path = self._chat_path(chat_id)
        path.write_text(
            json.dumps(chat, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _clear_chat(self, chat_id: int | str) -> None:
        path = self._chat_path(chat_id)
        if path.exists():
            path.unlink()

    def _assemble_prompt(self, chat: dict[str, Any]) -> str:
        catalog = self._scan_skill_catalog()
        parts: list[str] = [
            TOOL_INSTRUCTIONS,
            f"Skill Catalog:\n{catalog}",
        ]
        summary = (chat.get("summary") or "").strip()
        if summary:
            parts.append(f"Summary of earlier conversation:\n{summary}")
        for msg in chat["messages"]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)
