from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents import AgentsConfig, load_agents_config, load_prompt_text, format_run_context
from .config import load_openai_config, load_slack_config
from .executor import apply_operations, parse_operations_json
from .openai_client import ChatMessage, OpenAIClient
from .repo_snapshot import build_repo_snapshot_md
from .run_store import RunPaths, RunStore
from .slack import send_slack_message


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")
_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def _extract_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
        return t
    m = _JSON_OBJECT_RE.search(t)
    if m:
        return m.group(0)
    m = _JSON_ARRAY_RE.search(t)
    if m:
        return m.group(0)
    return t


def _safe_write_under(base_dir: Path, rel_path: str, content: str) -> Path:
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe relative path: {rel_path}")
    dest = (base_dir / rel).resolve()
    if base_dir.resolve() not in dest.parents and dest != base_dir.resolve():
        raise ValueError(f"Path escapes base dir: {rel_path}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


@dataclass(frozen=True)
class AutopilotOptions:
    max_rounds: int = 3
    write_artifacts_to_repo: bool = False
    auto_implement_code: bool = False
    apply_code_to_repo: bool = False


class Orchestrator:
    def __init__(self, *, repo_root: str | Path = "."):
        self.repo_root = Path(repo_root).resolve()
        self.framework_root = Path(__file__).resolve().parent
        self.run_store = RunStore(framework_root=self.framework_root)
        self.agents_config: AgentsConfig = load_agents_config(self.framework_root)
        self.openai_cfg = load_openai_config()
        self.slack_cfg = load_slack_config()

    def resolve_agent_id(self, identifier: str) -> str:
        if identifier in self.agents_config.agents:
            return identifier
        needle = identifier.strip().lower()
        for agent_id, spec in self.agents_config.agents.items():
            if spec.display_name.strip().lower() == needle:
                return agent_id
        raise KeyError(f"Unknown agent: {identifier}")

    def create_run(self, *, objective: str, created_by: str = "user") -> RunPaths:
        paths = self.run_store.create_run(objective=objective, created_by=created_by)
        self.run_store.append_event(paths, event={"type": "run_created", "agent": "system", "input": objective})
        return paths

    def get_run(self, run_id: str) -> RunPaths:
        run_dir = (self.run_store.runs_root / run_id).resolve()
        return RunPaths(
            run_id=run_id,
            run_dir=run_dir,
            state_path=run_dir / "state.json",
            repo_snapshot_path=run_dir / "repo_snapshot.md",
            kickoff_summary_path=run_dir / "kickoff_summary.md",
        )

    def list_runs(self) -> list[RunPaths]:
        return self.run_store.list_runs()

    def _client_for_agent(self, agent_id: str) -> OpenAIClient:
        spec = self.agents_config.agents[agent_id]
        return OpenAIClient(
            api_key=self.openai_cfg.api_key,
            base_url=self.openai_cfg.base_url,
            model=spec.model or self.openai_cfg.model,
            timeout_s=self.openai_cfg.timeout_s,
        )

    def build_repo_snapshot(self, paths: RunPaths) -> str:
        snapshot_md = build_repo_snapshot_md(self.repo_root)
        paths.repo_snapshot_path.write_text(snapshot_md, encoding="utf-8")
        self.run_store.append_event(paths, event={"type": "repo_snapshot_built", "agent": "system"})
        return snapshot_md

    def call_agent(
        self,
        paths: RunPaths,
        *,
        agent_name: str,
        message: str,
        force_json: bool = False,
        json_mode_tag: str | None = None,
    ) -> str:
        agent_id = self.resolve_agent_id(agent_name)
        state = self.run_store.load_state(paths)
        objective = state.get("objective") or ""
        repo_snapshot_md = paths.repo_snapshot_path.read_text(encoding="utf-8") if paths.repo_snapshot_path.exists() else None

        prompt = load_prompt_text(self.framework_root, self.agents_config.agents[agent_id].prompt_path)
        context = format_run_context(objective=objective, repo_snapshot_md=repo_snapshot_md, state=state)

        system_msgs = [ChatMessage(role="system", content=prompt)]
        if json_mode_tag:
            system_msgs.append(ChatMessage(role="system", content=json_mode_tag))

        user_msg = ChatMessage(role="user", content=f"{context}\n\n## Task\n{message}".strip())
        client = self._client_for_agent(agent_id)

        if self.slack_cfg.webhook_url:
            send_slack_message(
                webhook_url=self.slack_cfg.webhook_url,
                username=self.slack_cfg.username,
                text=f"[agent_chain] {paths.run_id}: starting {agent_id}",
            )

        self.run_store.append_event(paths, event={"type": "agent_call_started", "agent": agent_id, "input": message})
        response = client.chat(
            messages=system_msgs + [user_msg],
            temperature=self.agents_config.agents[agent_id].temperature,
            response_format={"type": "json_object"} if force_json else None,
        )
        self.run_store.append_event(paths, event={"type": "agent_call_finished", "agent": agent_id, "output": response})

        state = self.run_store.load_state(paths)
        agent_state = state.setdefault("agents", {}).setdefault(agent_id, {"messages": []})
        agent_state["messages"].append({"role": "user", "content": message})
        agent_state["messages"].append({"role": "assistant", "content": response})
        agent_state["messages"] = agent_state["messages"][-30:]
        self.run_store.save_state(paths, state)

        if self.slack_cfg.webhook_url:
            send_slack_message(
                webhook_url=self.slack_cfg.webhook_url,
                username=self.slack_cfg.username,
                text=f"[agent_chain] {paths.run_id}: finished {agent_id}",
            )

        return response

    def run_kickoff(self, paths: RunPaths) -> dict[str, Any]:
        state = self.run_store.load_state(paths)
        pipeline = self.agents_config.kickoff_pipeline
        state.setdefault("kickoff", {})
        state["kickoff"]["pipeline"] = [{"agent": s.agent, "message": s.message} for s in pipeline]
        self.run_store.save_state(paths, state)

        if not paths.repo_snapshot_path.exists():
            self.build_repo_snapshot(paths)

        kickoff_dir = paths.run_dir / "kickoff"
        kickoff_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        for step in pipeline:
            resp = self.call_agent(paths, agent_name=step.agent, message=step.message)
            out_path = _safe_write_under(kickoff_dir, f"{step.agent}.md", resp)
            results.append({"agent": step.agent, "message": step.message, "output_file": str(out_path.name)})

        if (kickoff_dir / "Supervisor.md").exists():
            paths.kickoff_summary_path.write_text((kickoff_dir / "Supervisor.md").read_text(encoding="utf-8"), encoding="utf-8")

        state = self.run_store.load_state(paths)
        state["kickoff"]["completed"] = True
        state["kickoff"]["results"] = results
        self.run_store.save_state(paths, state)
        self.run_store.append_event(paths, event={"type": "kickoff_completed", "agent": "system"})
        return state

    def supervisor_autopilot(self, paths: RunPaths, *, user_request: str, options: AutopilotOptions | None = None) -> dict[str, Any]:
        options = options or AutopilotOptions()
        if not paths.repo_snapshot_path.exists():
            self.build_repo_snapshot(paths)

        self.run_store.append_event(paths, event={"type": "autopilot_started", "agent": "Supervisor", "input": user_request})
        for round_idx in range(options.max_rounds):
            resp = self.call_agent(
                paths,
                agent_name="Supervisor",
                message=f"AUTOPILOT_JSON\nUser request: {user_request}\nRound: {round_idx+1}/{options.max_rounds}",
                force_json=True,
                json_mode_tag="AUTOPILOT_JSON",
            )
            try:
                plan = json.loads(_extract_json(resp))
            except Exception as exc:
                self.run_store.append_event(paths, event={"type": "autopilot_parse_failed", "agent": "Supervisor", "error": str(exc), "raw": resp})
                break

            state = self.run_store.load_state(paths)
            sup = state.setdefault("supervisor", {})
            sup["summary"] = plan.get("summary", "") or ""
            sup["backlog"] = plan.get("backlog", []) or []
            sup["last_autopilot"] = plan
            self.run_store.save_state(paths, state)

            for art in plan.get("artifacts_to_write") or []:
                try:
                    rel_path = str(art.get("path") or "").strip()
                    if not rel_path:
                        continue
                    content = str(art.get("content") or "")
                    repo_optional = bool(art.get("repo_optional", False))
                    wrote = _safe_write_under(paths.run_dir, rel_path, content)
                    self.run_store.append_event(paths, event={"type": "artifact_written_run", "agent": "system", "path": str(wrote.relative_to(paths.run_dir))})
                    state = self.run_store.load_state(paths)
                    state.setdefault("artifacts", []).append({"path": str(wrote.relative_to(paths.run_dir)), "repo_optional": repo_optional})
                    self.run_store.save_state(paths, state)
                except Exception as exc:
                    self.run_store.append_event(paths, event={"type": "artifact_write_failed", "agent": "system", "error": str(exc)})

            next_msgs = plan.get("next_messages") or []
            if not next_msgs:
                break
            for item in next_msgs:
                agent = str(item.get("agent") or "").strip()
                msg = str(item.get("message") or "").strip()
                if agent and msg:
                    self.call_agent(paths, agent_name=agent, message=msg)

            if options.auto_implement_code:
                self._maybe_execute_code_change_plan(paths, plan=plan, apply_to_repo=options.apply_code_to_repo)

        self.run_store.append_event(paths, event={"type": "autopilot_finished", "agent": "Supervisor"})
        return self.run_store.load_state(paths)

    def _maybe_execute_code_change_plan(self, paths: RunPaths, *, plan: dict[str, Any], apply_to_repo: bool) -> None:
        artifacts = plan.get("artifacts_to_write") or []
        plan_art = next((a for a in artifacts if str(a.get("path") or "").endswith("code_change_plan.json")), None)
        if not plan_art:
            return
        try:
            change_plan = json.loads(str(plan_art.get("content") or "{}"))
        except Exception:
            return
        files = change_plan.get("files") or []
        if not isinstance(files, list) or not files:
            return
        approved_files = [str(f).strip() for f in files if str(f).strip()][:8]
        approved_set = set(approved_files)

        context_parts = ["EXECUTOR_JSON", "Only touch these approved paths:"]
        context_parts += [f"- {f}" for f in approved_files]
        context_parts.append("\nApproved file contents (excerpted):")
        for rel in approved_files:
            repo_path = (self.repo_root / rel).resolve()
            if not repo_path.exists():
                context_parts.append(f"\n### {rel}\n[MISSING]\n")
                continue
            text = repo_path.read_text(encoding="utf-8", errors="replace")
            excerpt = text if len(text) <= 12000 else (text[:11800] + "\n\n... [truncated] ...\n")
            context_parts.append(f"\n### {rel}\n```")
            context_parts.append(excerpt.rstrip())
            context_parts.append("```")

        resp = self.call_agent(paths, agent_name="ExecutorEngineer", message="\n".join(context_parts), json_mode_tag="EXECUTOR_JSON")
        try:
            ops = parse_operations_json(resp)
        except Exception:
            return
        for op in ops:
            if str(op.get("path") or "").strip() not in approved_set:
                return

        executor_dir = paths.run_dir / "executor"
        executor_dir.mkdir(parents=True, exist_ok=True)
        _safe_write_under(executor_dir, "operations.json", json.dumps(ops, indent=2))
        report = apply_operations(repo_root=self.repo_root, operations=ops, dry_run=not apply_to_repo)
        _safe_write_under(executor_dir, "apply_report.json", report.to_json())

    def run_status_markdown(self, paths: RunPaths) -> str:
        state = self.run_store.load_state(paths)
        sup = state.get("supervisor") or {}
        backlog = sup.get("backlog") or []
        events = state.get("events") or []
        recent = events[-10:] if len(events) > 10 else events
        lines: list[str] = []
        lines.append(f"### Run `{paths.run_id}` status\n")
        if sup.get("summary"):
            lines.append("**Supervisor summary**")
            lines.append(str(sup["summary"]).strip())
            lines.append("")
        if backlog:
            lines.append("**Backlog (top)**")
            for item in backlog[:12]:
                lines.append(f"- {item}")
            lines.append("")
        lines.append("**Recent activity**")
        if not recent:
            lines.append("- (none yet)")
        else:
            for e in recent:
                lines.append(f"- {e.get('ts','')} — `{e.get('type','event')}` — {e.get('agent','system')}")
        return "\n".join(lines).strip()

