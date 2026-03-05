from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_dotenv_once() -> None:
    # Load repo-local .env (if present) to match existing app behavior.
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path), override=True)


def _get_env(key: str, default: str | None = None) -> str | None:
    _load_dotenv_once()
    value = os.getenv(key)
    return value if value is not None else default


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str | None
    base_url: str
    model: str
    timeout_s: int = 90


@dataclass(frozen=True)
class SlackConfig:
    webhook_url: str | None
    username: str | None = None


def load_openai_config() -> OpenAIConfig:
    return OpenAIConfig(
        api_key=_get_env("OPENAI_API_KEY"),
        base_url=_get_env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=_get_env("OPENAI_MODEL", "gpt-4o-mini"),
        timeout_s=int(_get_env("OPENAI_TIMEOUT_S", "90") or "90"),
    )


def load_slack_config() -> SlackConfig:
    return SlackConfig(
        webhook_url=_get_env("SLACK_WEBHOOK_URL"),
        username=_get_env("SLACK_USERNAME"),
    )

