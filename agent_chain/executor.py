from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BLOCKED_EXACT = {
    ".env",
    ".streamlit/secrets.toml",
}

BLOCKED_PREFIXES = (
    ".git/",
    "agent_chain/runs/",
)


_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")


@dataclass(frozen=True)
class ApplyReport:
    applied: list[dict[str, Any]]
    failed: list[dict[str, Any]]

    def to_json(self) -> str:
        return json.dumps({"applied": self.applied, "failed": self.failed}, indent=2)


def _normalize_rel_path(path: str) -> str:
    p = path.strip().replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    return p.lstrip("./")


def validate_repo_relative_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    p = _normalize_rel_path(path)

    if p.startswith("/"):
        raise ValueError("absolute paths are not allowed")
    if _WINDOWS_DRIVE_RE.match(p):
        raise ValueError("drive paths are not allowed")
    parts = [part for part in p.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("path traversal is not allowed")

    if p in BLOCKED_EXACT:
        raise ValueError(f"blocked path: {p}")
    if any(p.startswith(prefix) for prefix in BLOCKED_PREFIXES):
        raise ValueError(f"blocked path prefix: {p}")
    if "/.git/" in f"/{p}/" or p.startswith(".git/") or p == ".git":
        raise ValueError("blocked .git path")
    if p.endswith("/"):
        raise ValueError("path must be a file, not a directory")
    return p


def _resolve_under_repo(repo_root: Path, rel_path: str) -> Path:
    repo_root = repo_root.resolve()
    dest = (repo_root / rel_path).resolve()
    if repo_root not in dest.parents and dest != repo_root:
        raise ValueError(f"path escapes repo root: {rel_path}")
    return dest


def apply_operations(
    *,
    repo_root: str | Path,
    operations: list[dict[str, Any]],
    dry_run: bool = False,
) -> ApplyReport:
    repo_root = Path(repo_root).resolve()
    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    if not isinstance(operations, list):
        raise ValueError("operations must be a list")

    for op in operations:
        try:
            if not isinstance(op, dict):
                raise ValueError("operation must be an object")
            kind = str(op.get("op") or "").strip()
            rel = validate_repo_relative_path(str(op.get("path") or ""))
            dest = _resolve_under_repo(repo_root, rel)

            if kind == "add_file":
                content = str(op.get("content") or "")
                if dest.exists():
                    raise ValueError("file already exists")
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content, encoding="utf-8")
                applied.append({"op": kind, "path": rel})

            elif kind == "append":
                content = str(op.get("content") or "")
                if not dest.exists():
                    raise ValueError("file does not exist for append")
                if not dry_run:
                    existing = dest.read_text(encoding="utf-8", errors="replace")
                    sep = "" if (not existing or existing.endswith("\n") or content.startswith("\n")) else "\n"
                    dest.write_text(existing + sep + content, encoding="utf-8")
                applied.append({"op": kind, "path": rel})

            elif kind == "replace_once":
                find = str(op.get("find") or "")
                replace = str(op.get("replace") or "")
                if not dest.exists():
                    raise ValueError("file does not exist for replace_once")
                text = dest.read_text(encoding="utf-8", errors="replace")
                count = text.count(find)
                if count != 1:
                    raise ValueError(f"find string must appear exactly once (found {count})")
                if not dry_run:
                    dest.write_text(text.replace(find, replace, 1), encoding="utf-8")
                applied.append({"op": kind, "path": rel})

            else:
                raise ValueError(f"unknown op: {kind}")
        except Exception as exc:
            failed.append({"op": op, "error": str(exc)})

    return ApplyReport(applied=applied, failed=failed)


def parse_operations_json(text: str) -> list[dict[str, Any]]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Executor output must be a JSON list")
    return data

