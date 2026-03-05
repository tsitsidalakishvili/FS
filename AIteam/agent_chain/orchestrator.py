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
    # Best-effort extractor when models wrap JSON in markdown fences.
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    if t.startswith("{") and t.endswith("}"):
        return t
    if t.startswith("[") and t.endswith("]"):
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

    def _client_for_agent(self, agent_name: str) -> OpenAIClient:
        spec = self.agents_config.agents[agent_name]
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
        state = self.run_store.load_state(paths)
        objective = state.get("objective") or ""
        repo_snapshot_md = None
        if paths.repo_snapshot_path.exists():
            repo_snapshot_md = paths.repo_snapshot_path.read_text(encoding="utf-8")

        prompt = load_prompt_text(self.framework_root, self.agents_config.agents[agent_name].prompt_path)
        context = format_run_context(objective=objective, repo_snapshot_md=repo_snapshot_md, state=state)

        system_msgs = [ChatMessage(role="system", content=prompt)]
        if json_mode_tag:
            system_msgs.append(ChatMessage(role="system", content=json_mode_tag))

        user_msg = ChatMessage(
            role="user",
            content=f"{context}\n\n## Task\n{message}".strip(),
        )

        client = self._client_for_agent(agent_name)

        if self.slack_cfg.webhook_url:
            send_slack_message(
                webhook_url=self.slack_cfg.webhook_url,
                username=self.slack_cfg.username,
                text=f"[agent_chain] {paths.run_id}: starting {agent_name}",
            )

        self.run_store.append_event(
            paths, event={"type": "agent_call_started", "agent": agent_name, "input": message}
        )

        response = client.chat(
            messages=system_msgs + [user_msg],
            temperature=self.agents_config.agents[agent_name].temperature,
            response_format={"type": "json_object"} if force_json else None,
        )

        self.run_store.append_event(
            paths, event={"type": "agent_call_finished", "agent": agent_name, "output": response}
        )

        if self.slack_cfg.webhook_url:
            send_slack_message(
                webhook_url=self.slack_cfg.webhook_url,
                username=self.slack_cfg.username,
                text=f"[agent_chain] {paths.run_id}: finished {agent_name}",
            )

        # Track agent outputs in state for UI display.
        state = self.run_store.load_state(paths)
        agents = state.setdefault("agents", {})
        agent_state = agents.setdefault(agent_name, {"messages": []})
        agent_state["messages"].append({"role": "user", "content": message})
        agent_state["messages"].append({"role": "assistant", "content": response})
        agent_state["messages"] = agent_state["messages"][-30:]
        self.run_store.save_state(paths, state)

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

        # Prefer Supervisor output as kickoff summary.
        supervisor_out = results[-1]["agent"] == "Supervisor" and (kickoff_dir / "Supervisor.md").exists()
        if supervisor_out:
            paths.kickoff_summary_path.write_text((kickoff_dir / "Supervisor.md").read_text(encoding="utf-8"), encoding="utf-8")

        state = self.run_store.load_state(paths)
        state["kickoff"]["completed"] = True
        state["kickoff"]["results"] = results
        self.run_store.save_state(paths, state)
        self.run_store.append_event(paths, event={"type": "kickoff_completed", "agent": "system"})
        return state

    def supervisor_autopilot(
        self,
        paths: RunPaths,
        *,
        user_request: str,
        options: AutopilotOptions | None = None,
    ) -> dict[str, Any]:
        options = options or AutopilotOptions()
        if not paths.repo_snapshot_path.exists():
            self.build_repo_snapshot(paths)

        self.run_store.append_event(paths, event={"type": "autopilot_started", "agent": "Supervisor", "input": user_request})

        for round_idx in range(options.max_rounds):
            resp = self.call_agent(
                paths,
                agent_name="Supervisor",
                message=f"AUTOPILOT_JSON\nUser request: {user_request}\nRound: {round_idx+1}/{options.max_rounds}\nReturn next_messages and any artifacts_to_write needed.",
                force_json=True,
                json_mode_tag="AUTOPILOT_JSON",
            )
            raw = _extract_json(resp)
            try:
                plan = json.loads(raw)
            except Exception as exc:
                self.run_store.append_event(
                    paths,
                    event={
                        "type": "autopilot_parse_failed",
                        "agent": "Supervisor",
                        "error": str(exc),
                        "raw": resp,
                    },
                )
                break

            state = self.run_store.load_state(paths)
            supervisor_state = state.setdefault("supervisor", {})
            supervisor_state["summary"] = plan.get("summary", "") or ""
            supervisor_state["backlog"] = plan.get("backlog", []) or []
            supervisor_state["last_autopilot"] = plan
            self.run_store.save_state(paths, state)

            # Write artifacts under run folder; optionally to repo if safe + enabled.
            artifacts = plan.get("artifacts_to_write") or []
            for art in artifacts:
                try:
                    rel_path = str(art.get("path") or "").strip()
                    content = str(art.get("content") or "")
                    repo_optional = bool(art.get("repo_optional", False))
                    if not rel_path:
                        continue
                    wrote = _safe_write_under(paths.run_dir, rel_path, content)
                    self.run_store.append_event(
                        paths,
                        event={
                            "type": "artifact_written_run",
                            "agent": "system",
                            "path": str(wrote.relative_to(paths.run_dir)),
                        },
                    )
                    state = self.run_store.load_state(paths)
                    state.setdefault("artifacts", []).append(
                        {"path": str(wrote.relative_to(paths.run_dir)), "repo_optional": repo_optional}
                    )
                    self.run_store.save_state(paths, state)

                    if options.write_artifacts_to_repo and repo_optional:
                        # Repo writes are only allowed into non-sensitive, non-run locations.
                        repo_target = (self.repo_root / rel_path).resolve()
                        if self.repo_root not in repo_target.parents:
                            raise ValueError(f"Repo artifact escapes repo root: {rel_path}")
                        if repo_target.parts and ".git" in repo_target.parts:
                            raise ValueError("Refusing to write into .git")
                        rel_parts = repo_target.relative_to(self.repo_root).parts
                        if rel_parts[:2] == ("agent_chain", "runs") or rel_parts[:3] == ("AIteam", "agent_chain", "runs"):
                            raise ValueError("Refusing to write into agent_chain runs")
                        if repo_target.name == ".env" or str(repo_target).endswith(".streamlit/secrets.toml"):
                            raise ValueError("Refusing to write secret files")
                        repo_target.parent.mkdir(parents=True, exist_ok=True)
                        repo_target.write_text(content, encoding="utf-8")
                        self.run_store.append_event(
                            paths,
                            event={
                                "type": "artifact_written_repo",
                                "agent": "system",
                                "path": str(repo_target.relative_to(self.repo_root)),
                            },
                        )
                except Exception as exc:
                    self.run_store.append_event(
                        paths,
                        event={"type": "artifact_write_failed", "agent": "system", "error": str(exc), "artifact": art},
                    )

            # Dispatch next messages.
            next_msgs = plan.get("next_messages") or []
            if not next_msgs:
                break
            for item in next_msgs:
                agent = str(item.get("agent") or "").strip()
                msg = str(item.get("message") or "").strip()
                if not agent or not msg:
                    continue
                if agent not in self.agents_config.agents:
                    self.run_store.append_event(
                        paths,
                        event={"type": "dispatch_skipped_unknown_agent", "agent": "system", "target": agent},
                    )
                    continue
                self.call_agent(paths, agent_name=agent, message=msg)

            # Optional executor phase (bounded + safe).
            if options.auto_implement_code:
                self._maybe_execute_code_change_plan(paths, plan=plan, apply_to_repo=options.apply_code_to_repo)

        self.run_store.append_event(paths, event={"type": "autopilot_finished", "agent": "Supervisor"})
        return self.run_store.load_state(paths)

    def _maybe_execute_code_change_plan(self, paths: RunPaths, *, plan: dict[str, Any], apply_to_repo: bool) -> None:
        artifacts = plan.get("artifacts_to_write") or []
        plan_art = None
        for art in artifacts:
            if str(art.get("path") or "").strip().endswith("code_change_plan.json"):
                plan_art = art
                break
        if not plan_art:
            self.run_store.append_event(
                paths,
                event={"type": "executor_skipped", "agent": "system", "reason": "no code_change_plan.json provided"},
            )
            return

        try:
            change_plan = json.loads(str(plan_art.get("content") or "{}"))
        except Exception as exc:
            self.run_store.append_event(
                paths,
                event={"type": "executor_skipped", "agent": "system", "reason": f"invalid plan json: {exc}"},
            )
            return

        files = change_plan.get("files") or []
        if not isinstance(files, list) or not files:
            self.run_store.append_event(
                paths,
                event={"type": "executor_skipped", "agent": "system", "reason": "plan has no files"},
            )
            return

        # Bound the files we read to keep prompts small and safer.
        approved_files = [str(f).strip() for f in files if str(f).strip()][:8]
        approved_set = set(approved_files)

        context_parts: list[str] = []
        context_parts.append("EXECUTOR_JSON")
        context_parts.append("You must return a JSON list of file operations.")
        context_parts.append("Only touch these approved paths (including add_file targets):")
        for f in approved_files:
            context_parts.append(f"- {f}")
        instructions = str(change_plan.get("instructions") or "").strip()
        if instructions:
            context_parts.append("\nInstructions:\n" + instructions)

        # Provide file contents for existing files only.
        context_parts.append("\nApproved file contents (excerpted):")
        for rel in approved_files:
            try:
                repo_path = (self.repo_root / rel).resolve()
                if not repo_path.exists() or not repo_path.is_file():
                    context_parts.append(f"\n### {rel}\n[MISSING]\n")
                    continue
                text = repo_path.read_text(encoding="utf-8", errors="replace")
                excerpt = text if len(text) <= 12000 else (text[:11800] + "\n\n... [truncated] ...\n")
                context_parts.append(f"\n### {rel}\n```")
                context_parts.append(excerpt.rstrip())
                context_parts.append("```")
            except Exception as exc:
                context_parts.append(f"\n### {rel}\n[ERROR READING FILE: {exc}]\n")

        executor_prompt = "\n".join(context_parts).strip()
        self.run_store.append_event(paths, event={"type": "executor_started", "agent": "ExecutorEngineer"})

        resp = self.call_agent(
            paths,
            agent_name="ExecutorEngineer",
            message=executor_prompt,
            force_json=False,
            json_mode_tag="EXECUTOR_JSON",
        )

        try:
            ops = parse_operations_json(resp)
        except Exception as exc:
            self.run_store.append_event(
                paths,
                event={"type": "executor_failed", "agent": "ExecutorEngineer", "error": f"parse failed: {exc}", "raw": resp},
            )
            return

        # Enforce that operations only touch approved files.
        illegal = []
        for op in ops:
            p = str(op.get("path") or "").strip()
            if not p or p not in approved_set:
                illegal.append(p or "<missing path>")
        if illegal:
            self.run_store.append_event(
                paths,
                event={"type": "executor_failed", "agent": "system", "error": f"operations touch unapproved paths: {illegal[:10]}"},
            )
            _safe_write_under(paths.run_dir, "executor/operations_rejected.json", json.dumps(ops, indent=2))
            return

        executor_dir = paths.run_dir / "executor"
        executor_dir.mkdir(parents=True, exist_ok=True)
        _safe_write_under(executor_dir, "operations.json", json.dumps(ops, indent=2))

        report = apply_operations(repo_root=self.repo_root, operations=ops, dry_run=not apply_to_repo)
        _safe_write_under(executor_dir, "apply_report.json", report.to_json())

        md_lines = []
        md_lines.append("# Executor apply report\n")
        md_lines.append(f"- Apply to repo: `{apply_to_repo}`")
        md_lines.append(f"- Applied ops: `{len(report.applied)}`")
        md_lines.append(f"- Failed ops: `{len(report.failed)}`\n")
        if report.applied:
            md_lines.append("## Applied\n")
            for item in report.applied:
                md_lines.append(f"- `{item.get('op')}` `{item.get('path')}`")
            md_lines.append("")
        if report.failed:
            md_lines.append("## Failed\n")
            for item in report.failed[:20]:
                md_lines.append(f"- `{item.get('op', {}).get('op', 'unknown')}`: {item.get('error')}")
        _safe_write_under(executor_dir, "apply_report.md", "\n".join(md_lines).strip() + "\n")

        self.run_store.append_event(
            paths,
            event={
                "type": "executor_finished",
                "agent": "ExecutorEngineer",
                "applied": report.applied,
                "failed": report.failed,
                "apply_to_repo": apply_to_repo,
            },
        )

    def run_status_markdown(self, paths: RunPaths) -> str:
        state = self.run_store.load_state(paths)
        supervisor = state.get("supervisor") or {}
        backlog = supervisor.get("backlog") or []
        events = state.get("events") or []
        recent = events[-10:] if len(events) > 10 else events

        lines: list[str] = []
        lines.append(f"### Run `{paths.run_id}` status\n")
        if supervisor.get("summary"):
            lines.append("**Supervisor summary**")
            lines.append(supervisor["summary"].strip())
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
                ts = e.get("ts", "")
                et = e.get("type", "event")
                ag = e.get("agent", "system")
                lines.append(f"- {ts} — `{et}` — {ag}")
        return "\n".join(lines).strip()

