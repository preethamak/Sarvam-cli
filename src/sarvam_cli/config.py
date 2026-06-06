from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_BASE_URL = "https://api.sarvam.ai"


class ConfigError(RuntimeError):
    pass


def config_dir() -> Path:
    override = os.getenv("SARVAM_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "sarvam"
    return Path.home() / ".config" / "sarvam"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class AppConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def load(cls) -> "AppConfig":
        env_api_key = os.getenv("SARVAM_API_KEY")
        env_base_url = os.getenv("SARVAM_BASE_URL")
        data: dict[str, str] = {}

        path = config_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))

        return cls(
            api_key=env_api_key or data.get("api_key"),
            base_url=env_base_url or data.get("base_url", DEFAULT_BASE_URL),
        )

    def save(self) -> None:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigError(
                "Missing API key. Run `sarvam config set-api-key` or export `SARVAM_API_KEY`."
            )
        return self.api_key
