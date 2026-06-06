from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from sarvam_cli import cli


WAV_BYTES = (
    b"RIFF$\x00\x00\x00WAVEfmt "
    b"\x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00"
    b"\x02\x00\x10\x00data\x00\x00\x00\x00"
)


class MockSarvamHandler(BaseHTTPRequestHandler):
    server_version = "MockSarvam/1.0"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.server.requests.append(  # type: ignore[attr-defined]
            {
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": body,
            }
        )

        expected_key = self.server.api_key  # type: ignore[attr-defined]
        if self.headers.get("api-subscription-key") != expected_key:
            self._write_json(403, {"error": {"code": "invalid_api_key_error", "message": "Invalid API key"}})
            return

        if self.path == "/v1/chat/completions":
            payload = json.loads(body.decode("utf-8"))
            messages = payload["messages"]
            self.assert_message_list(messages)
            message = messages[-1]["content"]
            history_size = len(messages) - 1
            model = payload["model"]
            self._write_json(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": f"chat:{model}:{history_size}:{message}",
                            }
                        }
                    ]
                },
            )
            return

        if self.path == "/translate":
            payload = json.loads(body.decode("utf-8"))
            translated = f"{payload['target_language_code']}::{payload['input']}"
            self._write_json(200, {"translated_text": translated})
            return

        if self.path == "/text-lid":
            payload = json.loads(body.decode("utf-8"))
            language = "hi-IN" if "namaste" in payload["input"].lower() else "en-IN"
            self._write_json(200, {"language_code": language, "script_code": "Deva"})
            return

        if self.path == "/speech-to-text":
            if b'filename="sample.wav"' not in body and b'filename="voice.wav"' not in body:
                self._write_json(400, {"error": "missing file"})
                return
            self._write_json(200, {"transcript": "mock transcript"})
            return

        if self.path == "/text-to-speech":
            payload = json.loads(body.decode("utf-8"))
            if not payload["text"]:
                self._write_json(400, {"error": "missing text"})
                return
            self._write_json(200, {"audios": [base64.b64encode(WAV_BYTES).decode("ascii")]})
            return

        self._write_json(404, {"error": "not found"})

    def log_message(self, format: str, *args: object) -> None:
        return None

    def _write_json(self, status: int, payload: dict[str, object]) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def assert_message_list(self, messages: object) -> None:
        if not isinstance(messages, list) or not messages:
            raise AssertionError("messages must be a non-empty list")


class MockSarvamServer(HTTPServer):
    def __init__(self, server_address: tuple[str, int], api_key: str) -> None:
        super().__init__(server_address, MockSarvamHandler)
        self.api_key = api_key
        self.requests: list[dict[str, object]] = []


class EndToEndCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = MockSarvamServer(("127.0.0.1", 0), api_key="test-key")
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        self.env["SARVAM_CONFIG_DIR"] = str(self.config_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            [sys.executable, "-m", "sarvam_cli", *args],
            cwd=Path(__file__).resolve().parents[1],
            env=self.env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and process.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={process.stdout}\nstderr={process.stderr}")
        return process

    def make_text_file(self, name: str, content: str) -> Path:
        path = self.workspace / name
        path.write_text(content, encoding="utf-8")
        return path

    def make_wav_file(self, name: str) -> Path:
        path = self.workspace / name
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 160)
        return path

    def test_config_commands_persist_per_user(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        show = self.run_cli("config", "show")
        path_result = self.run_cli("config", "path")

        config_file = self.config_dir / "config.json"
        saved = json.loads(config_file.read_text(encoding="utf-8"))

        self.assertEqual(saved["api_key"], "test-key")
        self.assertEqual(saved["base_url"], self.base_url)
        self.assertIn("api_key", show.stdout)
        self.assertIn("set", show.stdout)
        self.assertIn(self.base_url, show.stdout)
        self.assertEqual(path_result.stdout.strip(), str(config_file))

    def test_home_screen(self) -> None:
        result = self.run_cli()
        self.assertIn("SARVAM  CLI", result.stdout)
        self.assertIn("Command Center", result.stdout)
        self.assertIn("sarvam help", result.stdout)
        self.assertIn("sarvam chat", result.stdout)
        self.assertIn("sarvam config set-api-key", result.stdout)

    def test_help_screen(self) -> None:
        result = self.run_cli("help")
        self.assertIn("Guided command overview", result.stdout)
        self.assertIn("Command Guide", result.stdout)
        self.assertIn("sarvam chat", result.stdout)
        self.assertIn("sarvam config set-api-key", result.stdout)

    def test_one_off_chat_uses_configured_api(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        result = self.run_cli("chat", "--lang", "hi-IN", "hello")
        self.assertIn("chat:sarvam-30b:0:hello", result.stdout)

    def test_interactive_chat_session(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        result = self.run_cli("chat", input_text="first\nsecond\n")
        self.assertIn("SARVAM  CLI", result.stdout)
        self.assertIn("Workspace", result.stdout)
        self.assertIn("Compose", result.stdout)
        self.assertIn("chat:sarvam-30b:0:first", result.stdout)
        self.assertIn("chat:sarvam-30b:2:second", result.stdout)

    def test_translate_from_file_and_stdin(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        file_path = self.make_text_file("notes.txt", "hello world")

        from_file = self.run_cli("translate", str(file_path), "--to", "kn-IN")
        from_stdin = self.run_cli("translate", "--to", "hi-IN", input_text="stdin text")

        self.assertIn("kn-IN::hello world", from_file.stdout)
        self.assertIn("hi-IN::stdin text", from_stdin.stdout)

    def test_detect_language(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        file_path = self.make_text_file("detect.txt", "namaste duniya")

        result = self.run_cli("detect-language", str(file_path))
        self.assertIn("hi-IN", result.stdout)

    def test_transcribe_audio_file(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        wav_path = self.make_wav_file("sample.wav")

        result = self.run_cli("transcribe", str(wav_path))
        self.assertIn("mock transcript", result.stdout)

    def test_speak_writes_audio_file(self) -> None:
        self.run_cli("config", "set-api-key", "--value", "test-key")
        self.run_cli("config", "set-base-url", self.base_url)
        output_path = self.workspace / "speech.wav"

        result = self.run_cli("speak", "hello", "--lang", "en-IN", "--output", str(output_path))

        self.assertIn(str(output_path), result.stdout)
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.read_bytes(), WAV_BYTES)

    def test_runtime_overrides_work_without_saved_config(self) -> None:
        result = self.run_cli(
            "--api-key",
            "test-key",
            "--base-url",
            self.base_url,
            "chat",
            "override call",
        )
        self.assertIn("chat:sarvam-30b:0:override call", result.stdout)
        self.assertFalse((self.config_dir / "config.json").exists())

    def test_voice_chat_handler(self) -> None:
        voice_wav = self.make_wav_file("voice.wav")

        args = cli.build_parser().parse_args(["chat", "--voice", "--lang", "hi-IN", "--record-seconds", "1"])
        stdout = io.StringIO()

        with (
            mock.patch.dict(
                os.environ,
                {
                    "SARVAM_API_KEY": "test-key",
                    "SARVAM_BASE_URL": self.base_url,
                    "SARVAM_CONFIG_DIR": str(self.config_dir),
                },
                clear=False,
            ),
            mock.patch("sarvam_cli.cli.record_wav", side_effect=[voice_wav, KeyboardInterrupt()]),
            mock.patch("sarvam_cli.cli.play_audio"),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = cli.handle_chat(args)

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("VOICE", output)
        self.assertIn("Recording 1s per turn", output)
        self.assertIn("mock transcript", output)
        self.assertIn("chat:sarvam-30b:0:mock transcript", output)


if __name__ == "__main__":
    unittest.main()
