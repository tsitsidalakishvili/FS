from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentSpec:
    name: str  # internal id
    display_name: str
    prompt_path: str
    temperature: float = 0.2
    model: str | None = None


@dataclass(frozen=True)
class KickoffStep:
    agent: str
    message: str


@dataclass(frozen=True)
class AgentsConfig:
    agents: dict[str, AgentSpec]
    kickoff_pipeline: list[KickoffStep]


def load_agents_config(framework_root: Path) -> AgentsConfig:
    cfg_path = (framework_root / "agents.json").resolve()
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))

    agents: dict[str, AgentSpec] = {}
    for name, spec in (raw.get("agents") or {}).items():
        agents[name] = AgentSpec(
            name=name,
            display_name=str(spec.get("display_name") or name),
            prompt_path=str(spec["prompt"]),
            temperature=float(spec.get("temperature", 0.2)),
            model=spec.get("model"),
        )

    kickoff_pipeline: list[KickoffStep] = []
    for step in raw.get("kickoff_pipeline") or []:
        kickoff_pipeline.append(KickoffStep(agent=str(step["agent"]), message=str(step["message"])))

    return AgentsConfig(agents=agents, kickoff_pipeline=kickoff_pipeline)


def load_prompt_text(framework_root: Path, prompt_path: str) -> str:
    prompt_file = (framework_root / prompt_path).resolve()
    return prompt_file.read_text(encoding="utf-8")


def format_run_context(*, objective: str, repo_snapshot_md: str | None, state: dict[str, Any]) -> str:
    events = state.get("events") or []
    recent = events[-8:] if len(events) > 8 else events
    recent_lines = []
    for e in recent:
        agent = e.get("agent") or e.get("name") or "unknown"
        etype = e.get("type") or "event"
        recent_lines.append(f"- [{etype}] {agent}")

    parts: list[str] = []
    parts.append("## Run context (blackboard)\n")
    parts.append(f"**Objective**: {objective}\n")
    parts.append("**Recent activity**:\n")
    parts.append("\n".join(recent_lines) if recent_lines else "- (none yet)")

    supervisor = state.get("supervisor") or {}
    backlog = supervisor.get("backlog") or []
    if backlog:
        parts.append("\n\n**Current backlog (from Supervisor)**:\n")
        for item in backlog[:20]:
            parts.append(f"- {item}")

    if repo_snapshot_md:
        max_chars = 15000
        snap = (
            repo_snapshot_md
            if len(repo_snapshot_md) <= max_chars
            else (repo_snapshot_md[: max_chars - 120] + "\n\n... [truncated] ...\n")
        )
        parts.append("\n\n## Repo snapshot (excerpted)\n")
        parts.append(snap)

    return "\n".join(parts).strip()

