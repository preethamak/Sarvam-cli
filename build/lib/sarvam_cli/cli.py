from __future__ import annotations

import argparse
import getpass
import os
import sys
import tempfile
from pathlib import Path

from sarvam_cli.api import SarvamAPIError, SarvamClient
from sarvam_cli.audio import AudioSupportError, play_audio, record_wav
from sarvam_cli.config import AppConfig, ConfigError, config_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sarvam",
        description="Developer-first command-line interface for Sarvam AI.",
    )
    parser.add_argument("--api-key", help="Override the configured API key for this invocation.")
    parser.add_argument("--base-url", help="Override the configured API base URL for this invocation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat = subparsers.add_parser("chat", help="Start a chat session.")
    chat.add_argument("--lang", help="Language code, for example hi-IN.")
    chat.add_argument("--model", default="sarvam-30b", help="Chat model. Default: sarvam-30b.")
    chat.add_argument("--voice", action="store_true", help="Use microphone input and spoken responses.")
    chat.add_argument(
        "--record-seconds",
        type=int,
        default=5,
        help="Seconds to record for each voice turn.",
    )
    chat.add_argument("message", nargs="?", help="Optional one-off chat message.")
    chat.set_defaults(handler=handle_chat)

    transcribe = subparsers.add_parser("transcribe", help="Transcribe an audio file.")
    transcribe.add_argument("audio_file", type=Path)
    transcribe.add_argument("--model", default="saaras:v3", help="Speech-to-text model. Default: saaras:v3.")
    transcribe.add_argument(
        "--mode",
        default="transcribe",
        choices=["transcribe", "translate", "verbatim", "translit", "codemix"],
        help="Speech-to-text mode. Default: transcribe.",
    )
    transcribe.set_defaults(handler=handle_transcribe)

    translate = subparsers.add_parser("translate", help="Translate a text file or stdin.")
    translate.add_argument("input", nargs="?", help="Path to a text file. Reads stdin if omitted.")
    translate.add_argument("--to", required=True, dest="target_language", help="Target language code.")
    translate.add_argument("--from-lang", dest="source_language", default="auto", help="Source language code. Default: auto.")
    translate.add_argument("--speaker-gender", choices=["Male", "Female"], help="Optional speaker gender hint.")
    translate.add_argument("--model", help="Translation model, for example sarvam-translate:v1.")
    translate.add_argument("--mode", help="Translation mode, for example formal.")
    translate.set_defaults(handler=handle_translate)

    speak = subparsers.add_parser("speak", help="Convert text into speech.")
    speak.add_argument("text", help="Text to synthesize.")
    speak.add_argument("--lang", required=True, help="Language code, for example hi-IN.")
    speak.add_argument("--output", type=Path, help="Write audio to a specific file.")
    speak.add_argument("--model", default="bulbul:v3", help="Text-to-speech model. Default: bulbul:v3.")
    speak.add_argument("--speaker", default="shubh", help="Voice speaker. Default: shubh.")
    speak.add_argument("--pace", type=float, help="Speech pace.")
    speak.add_argument("--sample-rate", type=int, dest="sample_rate", help="Output sample rate in Hz.")
    speak.add_argument("--play", action="store_true", help="Play the generated audio after synthesis.")
    speak.set_defaults(handler=handle_speak)

    detect = subparsers.add_parser("detect-language", help="Detect the language of a text file or stdin.")
    detect.add_argument("input", nargs="?", help="Path to a text file. Reads stdin if omitted.")
    detect.set_defaults(handler=handle_detect_language)

    config = subparsers.add_parser("config", help="Manage CLI configuration.")
    config_subparsers = config.add_subparsers(dest="config_command", required=True)

    set_api_key = config_subparsers.add_parser("set-api-key", help="Persist an API key locally.")
    set_api_key.add_argument("--value", help="Set the API key non-interactively.")
    set_api_key.set_defaults(handler=handle_set_api_key)

    set_base_url = config_subparsers.add_parser("set-base-url", help="Persist a custom API base URL.")
    set_base_url.add_argument("url", help="Base URL, for example https://api.sarvam.ai.")
    set_base_url.set_defaults(handler=handle_set_base_url)

    path_cmd = config_subparsers.add_parser("path", help="Show the config file path.")
    path_cmd.set_defaults(handler=handle_config_path)

    show = config_subparsers.add_parser("show", help="Show current configuration.")
    show.set_defaults(handler=handle_show_config)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _apply_runtime_overrides(args)
    try:
        return args.handler(args)
    except (ConfigError, SarvamAPIError, AudioSupportError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def handle_chat(args: argparse.Namespace) -> int:
    if args.voice:
        return _handle_voice_chat(args)
    if args.message:
        return _send_one_off_chat(args.message, model=args.model)
    return _run_interactive_chat(model=args.model)


def handle_transcribe(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        print(client.transcribe(args.audio_file, model=args.model, mode=args.mode))
    return 0


def handle_translate(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    text = _read_text_input(args.input)
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        translated = client.translate(
            text,
            target_language=args.target_language,
            source_language=args.source_language,
            speaker_gender=args.speaker_gender,
            model=args.model,
            mode=args.mode,
        )
    print(translated)
    return 0


def handle_speak(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    output_path = args.output or _temp_wav_path()
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        written_path = client.speak(
            args.text,
            language=args.lang,
            output_path=output_path,
            model=args.model,
            speaker=args.speaker,
            pace=args.pace,
            sample_rate=args.sample_rate,
        )
    print(written_path)
    if args.play:
        play_audio(written_path)
    return 0


def handle_detect_language(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    text = _read_text_input(args.input)
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        result = client.detect_language(text)
    language = result.get("language_code") or result.get("language")
    confidence = result.get("confidence")
    if confidence is None:
        print(language)
    else:
        print(f"{language}\t{confidence}")
    return 0


def handle_set_api_key(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    config.api_key = (args.value or getpass.getpass("Sarvam API key: ")).strip()
    if not config.api_key:
        raise ConfigError("API key cannot be empty.")
    config.save()
    print("API key saved.")
    return 0


def handle_set_base_url(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    config.base_url = args.url.rstrip("/")
    if not config.base_url:
        raise ConfigError("Base URL cannot be empty.")
    config.save()
    print("Base URL saved.")
    return 0


def handle_config_path(_: argparse.Namespace) -> int:
    print(config_path())
    return 0


def handle_show_config(_: argparse.Namespace) -> int:
    config = AppConfig.load()
    print(f"base_url={config.base_url}")
    print(f"api_key={'set' if config.api_key else 'unset'}")
    print(f"config_path={config_path()}")
    return 0


def _send_one_off_chat(message: str, *, model: str) -> int:
    config = AppConfig.load()
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        print(client.chat(message, model=model))
    return 0


def _run_interactive_chat(*, model: str) -> int:
    config = AppConfig.load()
    history: list[dict[str, str]] = []
    print("Interactive chat. Press Ctrl+D or Ctrl+C to exit.")
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        while True:
            try:
                prompt = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not prompt:
                continue
            reply = client.chat(prompt, model=model, history=history)
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": reply})
            print(f"sarvam> {reply}")
    return 0


def _handle_voice_chat(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    history: list[dict[str, str]] = []
    print(f"Voice chat active. Recording {args.record_seconds}s per turn. Press Ctrl+C to exit.")
    with SarvamClient(config.require_api_key(), config.base_url) as client:
        while True:
            try:
                audio_path = record_wav(args.record_seconds)
            except KeyboardInterrupt:
                print()
                break
            transcript = client.transcribe(audio_path, model="saaras:v3", mode="transcribe").strip()
            audio_path.unlink(missing_ok=True)
            if not transcript:
                print("sarvam> I could not detect speech. Try again.")
                continue
            print(f"you> {transcript}")
            reply = client.chat(transcript, model=args.model, history=history)
            history.append({"role": "user", "content": transcript})
            history.append({"role": "assistant", "content": reply})
            print(f"sarvam> {reply}")
            output_path = _temp_wav_path()
            client.speak(
                reply,
                language=args.lang or "en-IN",
                output_path=output_path,
                model="bulbul:v3",
                speaker="shubh",
            )
            play_audio(output_path)
            output_path.unlink(missing_ok=True)
    return 0


def _read_text_input(value: str | None) -> str:
    if value:
        return Path(value).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise ConfigError("Provide a file path or pipe text through stdin.")
    return sys.stdin.read()


def _apply_runtime_overrides(args: argparse.Namespace) -> None:
    if getattr(args, "api_key", None):
        os.environ["SARVAM_API_KEY"] = args.api_key
    if getattr(args, "base_url", None):
        os.environ["SARVAM_BASE_URL"] = args.base_url


def _temp_wav_path() -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        return Path(temp_file.name)
