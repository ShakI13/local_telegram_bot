"""Unit tests for config, orchestrator, and channel/inference plugins."""

from __future__ import annotations

import io
import json
import os
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

from src.channels.base import InboundMessage
from src.channels.telegram import TelegramChannel
from src.config import load_settings
from src.inference.ollama import OllamaInference
from src.orchestrator import Orchestrator


class FakeChannel:
    def __init__(self, messages: list[InboundMessage] | None = None) -> None:
        self._messages = list(messages or [])
        self.sent: list[tuple[int | str, str]] = []

    def poll(self) -> list[InboundMessage]:
        messages = self._messages
        self._messages = []
        return messages

    def send(self, chat_id: int | str, text: str) -> None:
        self.sent.append((chat_id, text))


class FakeInference:
    def __init__(self, reply: str = "model-reply") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


class ConfigTests(unittest.TestCase):
    def test_load_settings_requires_token(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                load_settings(env_file=None)

    def test_load_settings_defaults(self) -> None:
        env = {"TELEGRAM_BOT_TOKEN": "test-token"}
        with mock.patch.dict(os.environ, env, clear=True):
            settings = load_settings(env_file=None)
        self.assertEqual(settings.telegram_bot_token, "test-token")
        self.assertEqual(settings.ollama_base_url, "http://127.0.0.1:11434")
        self.assertEqual(settings.ollama_model, "qwen3:1.7b")

    def test_load_settings_custom_ollama(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "tok",
            "OLLAMA_BASE_URL": "http://localhost:11434/",
            "OLLAMA_MODEL": "tinyllama",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            settings = load_settings(env_file=None)
        self.assertEqual(settings.ollama_base_url, "http://localhost:11434")
        self.assertEqual(settings.ollama_model, "tinyllama")


class OrchestratorTests(unittest.TestCase):
    def test_handle_message_is_stateless_one_shot(self) -> None:
        channel = FakeChannel()
        inference = FakeInference(reply="pong")
        orch = Orchestrator(channel, inference)

        orch.handle_message(InboundMessage(chat_id=1, text="hello"))
        orch.handle_message(InboundMessage(chat_id=1, text="again"))

        self.assertEqual(inference.prompts, ["hello", "again"])
        self.assertEqual(channel.sent, [(1, "pong"), (1, "pong")])

    def test_run_once_polls_and_replies(self) -> None:
        channel = FakeChannel(
            [
                InboundMessage(chat_id=42, text="hi"),
                InboundMessage(chat_id=7, text="yo"),
            ]
        )
        inference = FakeInference(reply="ok")
        orch = Orchestrator(channel, inference)

        handled = orch.run_once()

        self.assertEqual(handled, 2)
        self.assertEqual(inference.prompts, ["hi", "yo"])
        self.assertEqual(channel.sent, [(42, "ok"), (7, "ok")])

    def test_run_once_continues_after_handler_error(self) -> None:
        channel = FakeChannel(
            [
                InboundMessage(chat_id=1, text="bad"),
                InboundMessage(chat_id=2, text="good"),
            ]
        )

        class FlakyInference:
            def generate(self, prompt: str) -> str:
                if prompt == "bad":
                    raise RuntimeError("boom")
                return "fine"

        orch = Orchestrator(channel, FlakyInference())
        with self.assertLogs("src.orchestrator", level="ERROR"):
            handled = orch.run_once()

        self.assertEqual(handled, 2)
        self.assertEqual(channel.sent, [(2, "fine")])


class TelegramChannelTests(unittest.TestCase):
    def test_poll_extracts_text_and_advances_offset(self) -> None:
        payload = {
            "ok": True,
            "result": [
                {
                    "update_id": 10,
                    "message": {
                        "message_id": 1,
                        "chat": {"id": 100},
                        "text": "hello",
                    },
                },
                {
                    "update_id": 11,
                    "message": {
                        "message_id": 2,
                        "chat": {"id": 200},
                        "photo": [],
                    },
                },
            ],
        }
        channel = TelegramChannel("secret-token", poll_timeout=1)
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = json.dumps(payload).encode("utf-8")
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = False

        with mock.patch(
            "src.channels.telegram.urllib.request.urlopen",
            return_value=fake_resp,
        ) as urlopen:
            messages = channel.poll()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].chat_id, 100)
        self.assertEqual(messages[0].text, "hello")
        self.assertEqual(channel._offset, 12)

        called_url = urlopen.call_args[0][0].full_url
        self.assertIn("/botsecret-token/getUpdates", called_url)
        self.assertNotIn("offset=", called_url)

        # Second poll should include offset.
        with mock.patch(
            "src.channels.telegram.urllib.request.urlopen",
            return_value=fake_resp,
        ) as urlopen2:
            fake_resp.read.return_value = json.dumps({"ok": True, "result": []}).encode(
                "utf-8"
            )
            channel.poll()
        called_url2 = urlopen2.call_args[0][0].full_url
        self.assertIn("offset=12", called_url2)

    def test_send_posts_send_message(self) -> None:
        channel = TelegramChannel("tok")
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = json.dumps({"ok": True, "result": {}}).encode(
            "utf-8"
        )
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = False

        with mock.patch(
            "src.channels.telegram.urllib.request.urlopen",
            return_value=fake_resp,
        ) as urlopen:
            channel.send(55, "reply text")

        req = urlopen.call_args[0][0]
        self.assertIn("/bottok/sendMessage", req.full_url)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body, {"chat_id": 55, "text": "reply text"})

    def test_poll_raises_on_http_error(self) -> None:
        channel = TelegramChannel("tok", poll_timeout=1)
        err = HTTPError(
            "https://api.telegram.org",
            401,
            "Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"ok":false}'),
        )
        with mock.patch(
            "src.channels.telegram.urllib.request.urlopen",
            side_effect=err,
        ):
            with self.assertRaises(RuntimeError):
                channel.poll()


class OllamaInferenceTests(unittest.TestCase):
    def test_generate_posts_prompt_and_returns_response(self) -> None:
        inference = OllamaInference("qwen3:1.7b", base_url="http://127.0.0.1:11434")
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = json.dumps(
            {"response": "Hello from model", "done": True}
        ).encode("utf-8")
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = False

        with mock.patch(
            "src.inference.ollama.urllib.request.urlopen",
            return_value=fake_resp,
        ) as urlopen:
            reply = inference.generate("Say hi")

        self.assertEqual(reply, "Hello from model")
        req = urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/generate")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(
            body,
            {"model": "qwen3:1.7b", "prompt": "Say hi", "stream": False},
        )

    def test_generate_raises_on_connection_error(self) -> None:
        inference = OllamaInference("qwen3:1.7b")
        with mock.patch(
            "src.inference.ollama.urllib.request.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaises(RuntimeError):
                inference.generate("hi")

    def test_generate_raises_when_response_missing(self) -> None:
        inference = OllamaInference("qwen3:1.7b")
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = json.dumps({"done": True}).encode("utf-8")
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.__exit__.return_value = False

        with mock.patch(
            "src.inference.ollama.urllib.request.urlopen",
            return_value=fake_resp,
        ):
            with self.assertRaises(RuntimeError):
                inference.generate("hi")


if __name__ == "__main__":
    unittest.main()
