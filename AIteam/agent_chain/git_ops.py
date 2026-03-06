from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def _run_git(repo_root: Path, args: list[str]) -> GitResult:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        return GitResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=proc.returncode,
        )
    except FileNotFoundError as exc:
        return GitResult(ok=False, stderr=str(exc), returncode=127)


def changed_files(repo_root: str | Path) -> list[str]:
    repo_root = Path(repo_root).resolve()
    res = _run_git(repo_root, ["status", "--porcelain"])
    if not res.ok:
        return []
    files: list[str] = []
    for line in (res.stdout or "").splitlines():
        if not line.strip():
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        if path_part:
            files.append(path_part)
    return sorted(set(files))


def stage_changed_files(repo_root: str | Path) -> GitResult:
    repo_root = Path(repo_root).resolve()
    files = changed_files(repo_root)
    if not files:
        return GitResult(ok=True, stdout="No changed files to stage.", returncode=0)
    return _run_git(repo_root, ["add", "-A", "--", *files])


def check_git_identity(repo_root: str | Path) -> GitResult:
    repo_root = Path(repo_root).resolve()
    email = _run_git(repo_root, ["config", "--get", "user.email"])
    name = _run_git(repo_root, ["config", "--get", "user.name"])
    if not (email.ok and email.stdout.strip()) or not (name.ok and name.stdout.strip()):
        return GitResult(ok=False, stderr="Missing git user.name/user.email configuration.")
    return GitResult(ok=True, stdout=f"{name.stdout.strip()} <{email.stdout.strip()}>")


def commit(repo_root: str | Path, *, message: str) -> GitResult:
    repo_root = Path(repo_root).resolve()
    ident = check_git_identity(repo_root)
    if not ident.ok:
        return ident
    if not message.strip():
        return GitResult(ok=False, stderr="Commit message is empty.")
    return _run_git(repo_root, ["commit", "-m", message])


def push(repo_root: str | Path, *, remote: str = "origin") -> GitResult:
    repo_root = Path(repo_root).resolve()
    branch = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not branch.ok:
        return branch
    return _run_git(repo_root, ["push", remote, branch.stdout.strip()])

