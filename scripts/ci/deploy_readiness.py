#!/usr/bin/env python3
import re
import sys
from pathlib import Path


REQUIRED_ENV_KEYS = [
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "DELIBERATION_API_URL",
    "DELIBERATION_DB_MODE",
    "REDIS_URL",
    "SENTRY_ENVIRONMENT",
    "LOG_LEVEL",
]

REQUIRED_FILES = [
    "docker-compose.yml",
    "monitoring/prometheus.yml",
    "monitoring/alert_rules.yml",
    "monitoring/alertmanager.yml",
    ".env.example",
]

ALLOWED_SECRET_PLACEHOLDERS = {"", "change_me", "local-dev"}


def _parse_dotenv(path: Path) -> dict:
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors = []

    for rel in REQUIRED_FILES:
        if not (repo_root / rel).exists():
            errors.append(f"missing required file: {rel}")

    env_path = repo_root / ".env.example"
    if env_path.exists():
        env_values = _parse_dotenv(env_path)
        missing_keys = [key for key in REQUIRED_ENV_KEYS if key not in env_values]
        if missing_keys:
            errors.append(f".env.example missing keys: {', '.join(missing_keys)}")

        for key, value in env_values.items():
            if not re.search(r"(PASSWORD|TOKEN|KEY|SECRET|DSN)", key):
                continue
            if value in ALLOWED_SECRET_PLACEHOLDERS:
                continue
            if value.startswith("http://") or value.startswith("https://"):
                continue
            errors.append(f".env.example key '{key}' must not contain a real secret value")

    if errors:
        print("deploy-readiness checks failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("deploy-readiness checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
