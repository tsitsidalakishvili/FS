from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class OpenAIClient:
    """Minimal OpenAI-compatible Chat Completions client."""

    def __init__(self, *, api_key: str | None, base_url: str, model: str, timeout_s: int = 90):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    def chat(
        self,
        *,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if not self._api_key:
            raise RuntimeError("Missing OPENAI_API_KEY.")

        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self._timeout_s)
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI-compatible API error {resp.status_code}: {resp.text}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"No choices returned: {data}")
        content = (choices[0].get("message") or {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid message payload: {data}")
        return content

