from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request


class SarvamAPIError(RuntimeError):
    pass


class SarvamClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "api-subscription-key": api_key,
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "sarvam-cli/0.1.0",
        }

    def close(self) -> None:
        return None

    def __enter__(self) -> "SarvamClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def chat(
        self,
        message: str,
        *,
        model: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        payload: dict[str, Any] = {
            "messages": messages,
            "model": model,
        }
        data = self._post_json("/v1/chat/completions", json=payload)
        return self._first_choice_text(data)

    def translate(
        self,
        text: str,
        *,
        target_language: str,
        source_language: str,
        speaker_gender: str | None = None,
        model: str | None = None,
        mode: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "input": text,
            "source_language_code": source_language,
            "target_language_code": target_language,
        }
        if speaker_gender:
            payload["speaker_gender"] = speaker_gender
        if model:
            payload["model"] = model
        if mode:
            payload["mode"] = mode
        data = self._post_json("/translate", json=payload)
        translated_text = data.get("translated_text")
        if isinstance(translated_text, str):
            return translated_text
        raise SarvamAPIError("Could not find translated_text in API response.")

    def detect_language(self, text: str) -> dict[str, Any]:
        return self._post_json("/text-lid", json={"input": text})

    def transcribe(
        self,
        audio_path: Path,
        *,
        model: str | None = None,
        mode: str | None = None,
    ) -> str:
        fields: dict[str, str] = {}
        if model:
            fields["model"] = model
        if mode:
            fields["mode"] = mode
        body, content_type = self._encode_multipart(audio_path, fields)
        data = self._request(
            "/speech-to-text",
            data=body,
            headers={"Content-Type": content_type},
        )
        transcript = data.get("transcript")
        if isinstance(transcript, str):
            return transcript
        raise SarvamAPIError("Could not find transcript in API response.")

    def speak(
        self,
        text: str,
        *,
        language: str,
        output_path: Path,
        model: str | None = None,
        speaker: str | None = None,
        pace: float | None = None,
        sample_rate: int | None = None,
    ) -> Path:
        payload: dict[str, Any] = {
            "text": text,
            "target_language_code": language,
        }
        if model:
            payload["model"] = model
        if speaker:
            payload["speaker"] = speaker
        if pace is not None:
            payload["pace"] = pace
        if sample_rate is not None:
            payload["speech_sample_rate"] = sample_rate
        response = self._request(
            "/text-to-speech",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        audios = response.get("audios")
        if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
            raise SarvamAPIError("Could not find base64 audio in API response.")
        output_path.write_bytes(base64.b64decode(audios[0]))
        return output_path

    def _post_json(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        data = self._request(
            path,
            data=self._encode_json(json),
            headers={"Content-Type": "application/json"},
        )
        if not isinstance(data, dict):
            raise SarvamAPIError(f"Unexpected response payload: {data!r}")
        return data

    def _first_choice_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
        raise SarvamAPIError("Could not find text in API response.")

    def _request(self, path: str, *, data: bytes, headers: dict[str, str] | None = None) -> dict[str, Any]:
        raw = self._request_raw(path, data=data, headers=headers)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SarvamAPIError(f"Failed to parse JSON response: {raw[:200]!r}") from exc
        if not isinstance(parsed, dict):
            raise SarvamAPIError(f"Unexpected response payload: {parsed!r}")
        return parsed

    def _request_raw(self, path: str, *, data: bytes, headers: dict[str, str] | None = None) -> bytes:
        req_headers = dict(self.headers)
        if headers:
            req_headers.update(headers)
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=req_headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                return response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise SarvamAPIError(f"Request failed with {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise SarvamAPIError(f"Network error: {exc.reason}") from exc

    def _encode_json(self, payload: dict[str, Any]) -> bytes:
        return json.dumps(payload).encode("utf-8")

    def _encode_multipart(self, audio_path: Path, fields: dict[str, str]) -> tuple[bytes, str]:
        boundary = f"----sarvam-cli-{uuid.uuid4().hex}"
        parts: list[bytes] = []

        for key, value in fields.items():
            parts.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )

        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n"
                ).encode("utf-8"),
                audio_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )

        return b"".join(parts), f"multipart/form-data; boundary={boundary}"
