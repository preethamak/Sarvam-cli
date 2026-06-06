from __future__ import annotations

import tempfile
import wave
from pathlib import Path


class AudioSupportError(RuntimeError):
    pass


def record_wav(seconds: int, sample_rate: int = 16000) -> Path:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise AudioSupportError(
            "Voice support requires optional dependencies. Install with `pip install \"sarvam-cli[voice]\"`."
        ) from exc

    recording = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_path = Path(temp_file.name)
    temp_file.close()

    samples = np.asarray(recording).reshape(-1)
    with wave.open(str(temp_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())

    return temp_path


def play_audio(path: Path) -> None:
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError as exc:
        raise AudioSupportError(
            "Audio playback requires optional dependencies. Install with `pip install \"sarvam-cli[voice]\"`."
        ) from exc

    audio, sample_rate = sf.read(str(path), dtype="float32")
    sd.play(audio, sample_rate)
    sd.wait()
