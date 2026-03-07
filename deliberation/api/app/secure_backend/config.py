import os
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TokenConfig:
    subject: str
    role: str


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    queue_name: str
    request_id_header: str
    tokens: Dict[str, TokenConfig]

    @classmethod
    def from_env(cls) -> "Settings":
        token_blob = os.getenv("SECURE_API_TOKENS", "").strip()
        parsed_tokens: Dict[str, TokenConfig] = {}
        if token_blob:
            # Format: "token:role[:subject],token2:role2[:subject2]"
            for raw_entry in token_blob.split(","):
                entry = raw_entry.strip()
                if not entry:
                    continue
                parts = entry.split(":")
                if len(parts) < 2:
                    continue
                token = parts[0].strip()
                role = parts[1].strip()
                subject = parts[2].strip() if len(parts) >= 3 else role
                if token and role:
                    parsed_tokens[token] = TokenConfig(subject=subject, role=role)
        else:
            parsed_tokens = {
                "admin-token": TokenConfig(subject="admin-user", role="admin"),
                "worker-token": TokenConfig(subject="worker-service", role="worker"),
                "viewer-token": TokenConfig(subject="viewer-user", role="viewer"),
            }

        return cls(
            database_url=os.getenv("SECURE_API_DATABASE_URL", "sqlite:///./secure_backend.db"),
            redis_url=os.getenv("SECURE_API_REDIS_URL", "redis://localhost:6379/0"),
            queue_name=os.getenv("SECURE_API_QUEUE_NAME", "secure-backend:jobs"),
            request_id_header=os.getenv("SECURE_API_REQUEST_ID_HEADER", "X-Request-ID"),
            tokens=parsed_tokens,
        )

