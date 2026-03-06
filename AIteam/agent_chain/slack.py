from __future__ import annotations

import json
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class SlackMessageResult:
    ok: bool
    status_code: int | None = None
    error: str | None = None


def send_slack_message(
    *,
    webhook_url: str | None,
    text: str,
    username: str | None = None,
    timeout_s: int = 10,
) -> SlackMessageResult:
    if not webhook_url:
        return SlackMessageResult(ok=False, error="SLACK_WEBHOOK_URL not set")
    payload = {"text": text}
    if username:
        payload["username"] = username
    try:
        resp = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout_s,
        )
        if resp.status_code >= 400:
            return SlackMessageResult(ok=False, status_code=resp.status_code, error=resp.text)
        return SlackMessageResult(ok=True, status_code=resp.status_code)
    except Exception as exc:
        return SlackMessageResult(ok=False, error=str(exc))

