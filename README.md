# Sarvam CLI

Agent-style terminal interface for Sarvam AI.

Sarvam CLI brings chat, voice, translation, transcription, language detection, and speech generation into a clean terminal workflow. It is designed to feel closer to a modern coding agent CLI than a thin API wrapper.

## Why

Sarvam has strong multilingual and speech APIs, but quick experimentation usually means writing setup code first. Sarvam CLI removes that setup friction:

- talk to Sarvam directly from the terminal
- test speech and translation flows without boilerplate
- switch between text, voice, and file-based workflows quickly
- keep per-user config local and simple

## Highlights

- Guided home screen with onboarding
- Interactive chat workspace with boxed composer flow
- Voice chat using microphone input and spoken replies
- Speech-to-text for audio files
- Translation for file or stdin input
- Text-to-speech with file output
- Language detection
- Per-user config with env-var overrides

## Installation

Basic install:

```bash
pip install sarvam-cli
```

With voice support:

```bash
pip install "sarvam-cli[voice]"
```

For local development from this repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

1. Set your API key:

```bash
sarvam config set-api-key
```

2. Open the CLI:

```bash
sarvam
```

3. Start chatting:

```bash
sarvam chat
```

## Configuration

Sarvam CLI stores user config at:

```text
~/.config/sarvam/config.json
```

Useful commands:

```bash
sarvam config set-api-key
sarvam config set-base-url https://api.sarvam.ai
sarvam config show
sarvam config path
```

Environment variables are also supported:

```bash
export SARVAM_API_KEY=your_api_key
export SARVAM_BASE_URL=https://api.sarvam.ai
```

For one-off overrides:

```bash
sarvam --api-key your_api_key chat "Hello"
sarvam --base-url https://api.sarvam.ai chat "Hello"
```

You can override the config directory too:

```bash
export SARVAM_CONFIG_DIR=/custom/path
```

## Command Overview

Open the landing screen:

```bash
sarvam
```

Show guided help:

```bash
sarvam help
```

Interactive chat:

```bash
sarvam chat
sarvam chat "Explain transformers simply"
```

Voice chat:

```bash
sarvam chat --voice --lang hi-IN
```

Translate text:

```bash
sarvam translate notes.txt --to kn-IN --from-lang en-IN
cat notes.txt | sarvam translate --to hi-IN
```

Transcribe audio:

```bash
sarvam transcribe meeting.wav
```

Generate speech:

```bash
sarvam speak "Welcome to Sarvam AI" --lang en-IN --output speech.wav
sarvam speak "Namaste" --lang hi-IN --play
```

Detect language:

```bash
sarvam detect-language notes.txt
```

## Chat UX

`sarvam chat` opens a dedicated terminal workspace rather than a plain prompt loop.

Inside chat:

```text
/help   Show session commands
/stats  Show session stats
/clear  Reset conversation history
/exit   Leave the session
```

## Voice Flow

```text
Microphone
  -> Speech-to-Text
  -> Sarvam Chat
  -> Text-to-Speech
  -> Speaker
```

## Common Examples

Translate English to Hindi:

```bash
sarvam translate ideas.txt --to hi-IN --from-lang en-IN
```

Chat in the terminal:

```bash
sarvam chat
```

Start a voice session in Hindi:

```bash
sarvam chat --voice --lang hi-IN
```

Generate spoken audio:

```bash
sarvam speak "This is a test" --lang en-IN --output test.wav
```

Check current config:

```bash
sarvam config show
```

## Development

Run the CLI from source without installing the console script:

```bash
PYTHONPATH=src python -m sarvam_cli
PYTHONPATH=src python -m sarvam_cli help
PYTHONPATH=src python -m sarvam_cli chat
```

Run tests:

```bash
PYTHONPATH=src python -m unittest -v tests.test_e2e
```

## Project Structure

```text
src/sarvam_cli/cli.py      Command routing and user flows
src/sarvam_cli/api.py      Sarvam API client
src/sarvam_cli/ui.py       Terminal UX and rendering
src/sarvam_cli/config.py   User config handling
src/sarvam_cli/audio.py    Microphone and playback helpers
tests/test_e2e.py          End-to-end CLI tests
```

## Notes

- Voice features require optional audio dependencies and working local audio hardware.
- The CLI supports per-user configuration and is suitable for installed users on the same machine without sharing credentials.
- If you exposed a real API key publicly while testing, rotate it.
