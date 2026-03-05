from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}


@dataclass(frozen=True)
class SnapshotOptions:
    max_files: int = 40
    max_chars_per_file: int = 5000


def _is_text_candidate(path: Path) -> bool:
    if path.name.startswith(".") and path.suffix not in {".md", ".toml", ".json", ".yml", ".yaml"}:
        return False
    return path.suffix.lower() in {
        ".py",
        ".md",
        ".txt",
        ".toml",
        ".json",
        ".yml",
        ".yaml",
        ".csv",
    }


def _tree_lines(root: Path, *, max_depth: int = 6) -> list[str]:
    lines: list[str] = []
    root = root.resolve()

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        items = []
        for p in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if p.name in DEFAULT_IGNORE_DIRS:
                continue
            if p.parts and "agent_chain" in p.parts and "runs" in p.parts:
                # Always exclude run outputs from snapshots.
                continue
            items.append(p)
        for i, p in enumerate(items):
            is_last = i == len(items) - 1
            branch = "└── " if is_last else "├── "
            lines.append(f"{prefix}{branch}{p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir():
                walk(p, prefix + ("    " if is_last else "│   "), depth + 1)

    lines.append(f"{root.name}/")
    walk(root, "", 1)
    return lines


def _read_excerpt(path: Path, *, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[Could not read file: {exc}]"
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 120] + "\n\n... [truncated] ...\n"


def build_repo_snapshot_md(repo_root: Path, *, options: SnapshotOptions | None = None) -> str:
    options = options or SnapshotOptions()
    repo_root = repo_root.resolve()

    # Priority ordering keeps the snapshot useful even for large repos.
    priority_files = [
        repo_root / "README.md",
        repo_root / "requirements.txt",
        repo_root / "app.py",
        repo_root / "GRAPH_SCHEMA.md",
    ]

    candidates: list[Path] = []
    seen = set()
    for p in priority_files:
        if p.exists() and p.is_file():
            candidates.append(p)
            seen.add(str(p))

    for p in repo_root.rglob("*"):
        if len(candidates) >= options.max_files:
            break
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if rel.parts and rel.parts[0] in DEFAULT_IGNORE_DIRS:
            continue
        if rel.parts[:2] == ("agent_chain", "runs"):
            continue
        if not _is_text_candidate(p):
            continue
        if str(p) in seen:
            continue
        candidates.append(p)
        seen.add(str(p))

    tree = "\n".join(_tree_lines(repo_root))
    parts: list[str] = []
    parts.append("# Repo snapshot\n")
    parts.append("## File tree\n")
    parts.append("```")
    parts.append(tree)
    parts.append("```\n")
    parts.append("## File excerpts\n")

    for p in candidates[: options.max_files]:
        rel = p.relative_to(repo_root)
        parts.append(f"### `{rel.as_posix()}`\n")
        parts.append("```")
        parts.append(_read_excerpt(p, max_chars=options.max_chars_per_file).rstrip())
        parts.append("```\n")

    return "\n".join(parts).rstrip() + "\n"

