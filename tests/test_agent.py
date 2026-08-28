"""Agent seam tests: Chat Store, /new, loop, skills, exec, Context Budget."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.agent import (
    Agent,
    GENERIC_FAILURE_NOTICE,
    INFERENCE_FAILURE_NOTICE,
    MAX_STEPS_MESSAGE,
)


class ScriptedInference:
    """Returns scripted replies in order; records every prompt."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise AssertionError(f"Unexpected generate call with prompt={prompt!r}")
        return self._replies.pop(0)


class AgentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        self.store = root / "chats"
        self.skills = root / "skills"
        self.store.mkdir()
        self.skills.mkdir()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _agent(self, inference: ScriptedInference, **kwargs: object) -> Agent:
        return Agent(
            inference,
            chat_store_dir=self.store,
            skills_dir=self.skills,
            **kwargs,  # type: ignore[arg-type]
        )


class DurableChatTests(AgentTestCase):
    def test_second_message_prompt_includes_earlier_turns(self) -> None:
        inference = ScriptedInference(["first-reply", "second-reply"])
        agent = self._agent(inference)

        self.assertEqual(agent.handle(1, "hello"), "first-reply")
        self.assertEqual(agent.handle(1, "remember?"), "second-reply")

        self.assertEqual(len(inference.prompts), 2)
        self.assertIn("hello", inference.prompts[1])
        self.assertIn("first-reply", inference.prompts[1])
        self.assertIn("remember?", inference.prompts[1])

    def test_chat_survives_new_agent_instance(self) -> None:
        inference1 = ScriptedInference(["saved-reply"])
        self._agent(inference1).handle(7, "persist me")

        inference2 = ScriptedInference(["after-restart"])
        self._agent(inference2).handle(7, "still there?")

        self.assertIn("persist me", inference2.prompts[0])
        self.assertIn("saved-reply", inference2.prompts[0])

    def test_new_clears_only_that_chat_and_skips_inference(self) -> None:
        inference = ScriptedInference(
            ["a-reply", "b-reply", "a-after", "b-after"]
        )
        agent = self._agent(inference)

        agent.handle(1, "alpha")
        agent.handle(2, "beta")
        ack = agent.handle(1, "  /new  ")
        agent.handle(1, "fresh")

        self.assertIn("reset", ack.lower())
        self.assertEqual(len(inference.prompts), 3)  # no call for /new

        self.assertNotIn("alpha", inference.prompts[2])
        self.assertIn("fresh", inference.prompts[2])

        agent.handle(2, "still beta?")
        self.assertIn("beta", inference.prompts[3])
        self.assertIn("b-reply", inference.prompts[3])

        store_file = self.store / "1.json"
        if store_file.exists():
            data = json.loads(store_file.read_text(encoding="utf-8"))
            history = data.get("messages") or []
            texts = " ".join(m.get("content", "") for m in history)
            self.assertNotIn("alpha", texts)

    def test_new_alone_does_not_invoke_inference(self) -> None:
        inference = ScriptedInference([])
        agent = self._agent(inference)
        reply = agent.handle(99, "/new")
        self.assertIn("reset", reply.lower())
        self.assertEqual(inference.prompts, [])


class AgenticLoopSkillTests(AgentTestCase):
    def test_catalog_lists_dropped_in_skill_file(self) -> None:
        (self.skills / "demo.md").write_text(
            "# Demo\n\nOne-line: does demo things.\n\nBody here.\n",
            encoding="utf-8",
        )
        inference = ScriptedInference(["plain answer"])
        agent = self._agent(inference)

        agent.handle(1, "hi")

        catalog_prompt = inference.prompts[0]
        self.assertIn("demo", catalog_prompt.lower())
        self.assertNotIn("Body here", catalog_prompt)

    def test_catalog_picks_up_new_skill_without_restart(self) -> None:
        inference = ScriptedInference(["a1", "a2"])
        agent = self._agent(inference)

        agent.handle(1, "before")
        self.assertNotIn("weather", inference.prompts[0].lower())

        (self.skills / "weather.md").write_text(
            "# Weather\n\nFetch weather via curl.\n",
            encoding="utf-8",
        )
        agent.handle(1, "after")
        self.assertIn("weather", inference.prompts[1].lower())

    def test_skill_tag_loads_body_into_loop(self) -> None:
        (self.skills / "wttr.md").write_text(
            "# wttr\n\nUse curl for wttr.in.\n\nFULL SKILL BODY SECRET\n",
            encoding="utf-8",
        )
        inference = ScriptedInference(
            [
                "<skill>wttr</skill>",
                "Weather skill loaded.",
            ]
        )
        agent = self._agent(inference)

        reply = agent.handle(1, "load skill")

        self.assertEqual(reply, "Weather skill loaded.")
        self.assertEqual(len(inference.prompts), 2)
        self.assertIn("FULL SKILL BODY SECRET", inference.prompts[1])

    def test_unknown_skill_returns_tool_error(self) -> None:
        inference = ScriptedInference(
            [
                "<skill>missing</skill>",
                "Could not load that skill.",
            ]
        )
        agent = self._agent(inference)

        reply = agent.handle(1, "load missing")

        self.assertEqual(reply, "Could not load that skill.")
        self.assertIn("error", inference.prompts[1].lower())
        self.assertIn("missing", inference.prompts[1].lower())

    def test_skill_path_traversal_rejected(self) -> None:
        inference = ScriptedInference(
            [
                "<skill>../secrets</skill>",
                "Nope.",
            ]
        )
        agent = self._agent(inference)

        reply = agent.handle(1, "hack")

        self.assertEqual(reply, "Nope.")
        self.assertIn("error", inference.prompts[1].lower())

    def test_plain_text_is_final_answer(self) -> None:
        inference = ScriptedInference(["Just a normal reply."])
        agent = self._agent(inference)
        self.assertEqual(agent.handle(1, "hi"), "Just a normal reply.")
        self.assertEqual(len(inference.prompts), 1)

    def test_max_steps_stops_loop_with_clear_message(self) -> None:
        inference = ScriptedInference(
            ["<skill>nope</skill>"] * 20
        )
        agent = self._agent(inference, max_steps=8)

        reply = agent.handle(1, "loop forever")

        self.assertEqual(reply, MAX_STEPS_MESSAGE)
        self.assertEqual(len(inference.prompts), 8)

    def test_empty_skill_body_does_not_crash(self) -> None:
        inference = ScriptedInference(
            [
                "<skill></skill>",
                "Recovered.",
            ]
        )
        agent = self._agent(inference)
        self.assertEqual(agent.handle(1, "empty"), "Recovered.")
        self.assertIn("error", inference.prompts[1].lower())


class AllowlistedExecTests(AgentTestCase):
    def test_non_curl_exec_rejected_before_run(self) -> None:
        from src.exec_runner import AllowlistedExecRunner

        real = AllowlistedExecRunner(cwd=self.store, timeout=1)
        with mock.patch("src.exec_runner.subprocess.run") as mock_run:
            inference = ScriptedInference(
                [
                    "<exec>powershell.exe -Command Get-Process</exec>",
                    "Blocked.",
                ]
            )
            agent = self._agent(inference, exec_runner=real)
            reply = agent.handle(1, "hack")

        self.assertEqual(reply, "Blocked.")
        mock_run.assert_not_called()
        self.assertIn("not allowlisted", inference.prompts[1].lower())

    def test_curl_exec_output_fed_back_into_loop(self) -> None:
        calls: list[str] = []

        def fake_exec(command: str) -> str:
            calls.append(command)
            return "exit_code=0\nstdout:\nLondon: +12C\nstderr:\n"

        inference = ScriptedInference(
            [
                '<exec>curl.exe -s "https://wttr.in/London?format=3"</exec>',
                "It is 12C in London.",
            ]
        )
        agent = self._agent(inference, exec_runner=fake_exec)

        reply = agent.handle(1, "weather in London?")

        self.assertEqual(reply, "It is 12C in London.")
        self.assertEqual(len(calls), 1)
        self.assertIn("curl.exe", calls[0])
        self.assertIn("London: +12C", inference.prompts[1])

    def test_skill_then_curl_then_answer_composes(self) -> None:
        (self.skills / "wttr.md").write_text(
            "# wttr\n\nUse curl for wttr.in.\n",
            encoding="utf-8",
        )
        calls: list[str] = []

        def fake_exec(command: str) -> str:
            calls.append(command)
            return "exit_code=0\nstdout:\nParis: +8C\nstderr:\n"

        inference = ScriptedInference(
            [
                "<skill>wttr</skill>",
                '<exec>curl.exe -s "https://wttr.in/Paris?format=3"</exec>',
                "Paris is +8C.",
            ]
        )
        agent = self._agent(inference, exec_runner=fake_exec)

        reply = agent.handle(1, "weather Paris")

        self.assertEqual(reply, "Paris is +8C.")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(inference.prompts), 3)
        self.assertIn("Use curl for wttr.in", inference.prompts[1])
        self.assertIn("Paris: +8C", inference.prompts[2])

    def test_path_escape_argument_rejected(self) -> None:
        from src.exec_runner import AllowlistedExecRunner

        real = AllowlistedExecRunner(cwd=self.store, timeout=1)
        with mock.patch("src.exec_runner.subprocess.run") as mock_run:
            inference = ScriptedInference(
                [
                    "<exec>curl.exe -o ..\\out.txt https://example.com</exec>",
                    "Blocked path.",
                ]
            )
            agent = self._agent(inference, exec_runner=real)
            reply = agent.handle(1, "escape")

        self.assertEqual(reply, "Blocked path.")
        mock_run.assert_not_called()
        self.assertIn("jail", inference.prompts[1].lower())

    def test_empty_exec_does_not_crash(self) -> None:
        inference = ScriptedInference(
            [
                "<exec></exec>",
                "Recovered from empty exec.",
            ]
        )
        agent = self._agent(inference, exec_runner=lambda _c: "nope")
        self.assertEqual(agent.handle(1, "empty exec"), "Recovered from empty exec.")
        self.assertIn("error", inference.prompts[1].lower())


class ContextBudgetTests(AgentTestCase):
    def test_over_budget_summarizes_older_keeps_recent(self) -> None:
        summarized_blobs: list[str] = []

        def fake_summarizer(blob: str) -> str:
            summarized_blobs.append(blob)
            return "SUMMARY_OF_OLD"

        long_a = "AAAA_OLD1_" + ("a" * 400)
        long_b = "BBBB_OLD2_" + ("b" * 400)
        long_c = "CCCC_RECENT_" + ("c" * 50)

        inference = ScriptedInference(["ack1", "ack2", "final"])
        agent = self._agent(
            inference,
            context_budget=900,
            recent_keep=2,
            summarizer=fake_summarizer,
        )

        agent.handle(1, long_a)
        agent.handle(1, long_b)
        reply = agent.handle(1, long_c)

        self.assertEqual(reply, "final")
        self.assertTrue(summarized_blobs)
        last_prompt = inference.prompts[-1]
        self.assertIn("SUMMARY_OF_OLD", last_prompt)
        self.assertIn("CCCC_RECENT_", last_prompt)
        self.assertNotIn("AAAA_OLD1_", last_prompt)

        data = json.loads((self.store / "1.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("summary"), "SUMMARY_OF_OLD")

    def test_oversized_summary_is_trimmed_from_oldest(self) -> None:
        # Seed a persisted Chat whose Summary alone blows a modest budget.
        fat = "OLDPART_" + ("X" * 600) + "_NEWPART"
        (self.store / "1.json").write_text(
            json.dumps(
                {
                    "summary": fat,
                    "messages": [
                        {"role": "user", "content": "hello"},
                        {"role": "assistant", "content": "hi"},
                    ],
                }
            ),
            encoding="utf-8",
        )

        inference = ScriptedInference(["still ok"])
        agent = self._agent(
            inference,
            context_budget=700,
            recent_keep=4,
            summarizer=lambda blob: blob,  # should not need to fold more
        )
        reply = agent.handle(1, "next")

        self.assertEqual(reply, "still ok")
        prompt = inference.prompts[0]
        self.assertNotIn("OLDPART_", prompt)
        data = json.loads((self.store / "1.json").read_text(encoding="utf-8"))
        summary = data.get("summary", "")
        self.assertTrue(summary)
        self.assertFalse(summary.startswith("OLDPART_"))
        self.assertIn("NEWPART", summary)

    def test_summarizer_not_required_when_under_budget(self) -> None:
        def boom(_blob: str) -> str:
            raise AssertionError("summarizer should not run under budget")

        inference = ScriptedInference(["short"])
        agent = self._agent(
            inference,
            context_budget=50_000,
            summarizer=boom,
        )
        self.assertEqual(agent.handle(1, "hi"), "short")


class TurnFailureNoticeTests(AgentTestCase):
    def test_inference_failure_returns_notice_and_persists_chat(self) -> None:
        class BoomInference:
            def generate(self, prompt: str) -> str:
                raise RuntimeError("Ollama request failed: connection refused")

        agent = self._agent(BoomInference())
        reply = agent.handle(42, "Какая погода в Москве ?")

        self.assertEqual(reply, INFERENCE_FAILURE_NOTICE)
        data = json.loads((self.store / "42.json").read_text(encoding="utf-8"))
        messages = data["messages"]
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Какая погода в Москве ?")
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertEqual(messages[-1]["content"], INFERENCE_FAILURE_NOTICE)

    def test_inference_failure_keeps_partial_loop_rows(self) -> None:
        (self.skills / "wttr.md").write_text("# wttr\n\nWeather.\n", encoding="utf-8")

        class PartialThenBoom:
            def __init__(self) -> None:
                self.n = 0

            def generate(self, prompt: str) -> str:
                self.n += 1
                if self.n == 1:
                    return "<skill>wttr</skill>"
                raise RuntimeError("Ollama request failed")

        agent = self._agent(PartialThenBoom())
        reply = agent.handle(1, "weather please")

        self.assertEqual(reply, INFERENCE_FAILURE_NOTICE)
        data = json.loads((self.store / "1.json").read_text(encoding="utf-8"))
        roles = [m["role"] for m in data["messages"]]
        self.assertEqual(roles[0], "user")
        self.assertIn("assistant", roles[1:-1])
        self.assertIn("tool", roles[1:-1])
        self.assertEqual(data["messages"][-1]["content"], INFERENCE_FAILURE_NOTICE)

    def test_unexpected_error_returns_generic_notice_and_persists(self) -> None:
        class ExplodingBudgetAgent(Agent):
            def _enforce_context_budget(
                self, chat: dict, *, turn_start_index: int
            ) -> int:
                raise RuntimeError("budget boom")

        inference = ScriptedInference(["should-not-run"])
        agent = ExplodingBudgetAgent(
            inference,
            chat_store_dir=self.store,
            skills_dir=self.skills,
        )
        reply = agent.handle(7, "hello")

        self.assertEqual(reply, GENERIC_FAILURE_NOTICE)
        data = json.loads((self.store / "7.json").read_text(encoding="utf-8"))
        self.assertEqual(data["messages"][0]["content"], "hello")
        self.assertEqual(data["messages"][-1]["content"], GENERIC_FAILURE_NOTICE)


if __name__ == "__main__":
    unittest.main()
