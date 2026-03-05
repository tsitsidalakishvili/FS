from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_run_id() -> str:
    # Example: 20260305_091122Z_4f2c1a
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    rand = os.urandom(3).hex()
    return f"{ts}_{rand}"


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_dir: Path
    state_path: Path
    repo_snapshot_path: Path
    kickoff_summary_path: Path


class RunStore:
    def __init__(self, *, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.runs_root = (self.repo_root / "agent_chain" / "runs").resolve()
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def create_run(self, *, objective: str, created_by: str = "user") -> RunPaths:
        run_id = _safe_run_id()
        run_dir = (self.runs_root / run_id).resolve()
        run_dir.mkdir(parents=True, exist_ok=False)
        paths = RunPaths(
            run_id=run_id,
            run_dir=run_dir,
            state_path=run_dir / "state.json",
            repo_snapshot_path=run_dir / "repo_snapshot.md",
            kickoff_summary_path=run_dir / "kickoff_summary.md",
        )
        state: dict[str, Any] = {
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "created_by": created_by,
            "objective": objective,
            "events": [],
            "agents": {},
            "kickoff": {"completed": False, "pipeline": [], "results": []},
            "supervisor": {"summary": "", "backlog": [], "last_autopilot": None},
            "artifacts": [],
        }
        self.save_state(paths, state)
        return paths

    def list_runs(self) -> list[RunPaths]:
        if not self.runs_root.exists():
            return []
        runs: list[RunPaths] = []
        for child in sorted(self.runs_root.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            run_id = child.name
            runs.append(
                RunPaths(
                    run_id=run_id,
                    run_dir=child,
                    state_path=child / "state.json",
                    repo_snapshot_path=child / "repo_snapshot.md",
                    kickoff_summary_path=child / "kickoff_summary.md",
                )
            )
        return runs

    def load_state(self, paths: RunPaths) -> dict[str, Any]:
        if not paths.state_path.exists():
            return {}
        return json.loads(paths.state_path.read_text(encoding="utf-8"))

    def save_state(self, paths: RunPaths, state: dict[str, Any]) -> None:
        paths.state_path.write_text(json.dumps(state, indent=2, sort_keys=False), encoding="utf-8")

    def append_event(self, paths: RunPaths, *, event: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state(paths)
        state.setdefault("events", [])
        event = {**event, "ts": utc_now_iso()}
        state["events"].append(event)
        self.save_state(paths, state)
        return state

