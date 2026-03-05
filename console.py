from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

import streamlit as st

from agent_chain.git_ops import changed_files, commit, push, stage_changed_files
from agent_chain.orchestrator import AutopilotOptions, Orchestrator


REPO_ROOT = Path(__file__).resolve().parent


def _get_orchestrator() -> Orchestrator:
    if "agent_chain_orchestrator" not in st.session_state:
        st.session_state["agent_chain_orchestrator"] = Orchestrator(repo_root=REPO_ROOT)
    return st.session_state["agent_chain_orchestrator"]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"[Could not read {path.name}: {exc}]"


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_process(pid: int) -> None:
    if not _is_pid_running(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        return


st.set_page_config(page_title="Agent Chain Console", layout="wide")
st.title("Agent Chain Console")

orch = _get_orchestrator()
runs = orch.list_runs()

with st.sidebar:
    st.subheader("Environment")
    st.caption(f"OpenAI model: `{orch.openai_cfg.model}`")
    if orch.slack_cfg.webhook_url:
        st.caption("Slack: enabled (`SLACK_WEBHOOK_URL` set)")
    else:
        st.caption("Slack: disabled (set `SLACK_WEBHOOK_URL` to enable)")

    st.subheader("Git automation (optional)")
    changed = changed_files(REPO_ROOT)
    st.caption(f"Changed files: `{len(changed)}`")
    if changed:
        st.code("\n".join(changed), language=None)

    git_commit = st.checkbox("Commit after staging", value=False)
    git_push = st.checkbox("Push after commit", value=False)
    git_message = st.text_input("Commit message", value="agent_chain: update")
    if st.button("Stage (+ optional commit/push)"):
        res = stage_changed_files(REPO_ROOT)
        if res.ok:
            st.success("Staged changed files.")
        else:
            st.error(res.stderr or res.stdout or "git add failed")
        if res.ok and git_commit:
            cres = commit(REPO_ROOT, message=git_message)
            if cres.ok:
                st.success("Committed.")
            else:
                st.error(cres.stderr or cres.stdout or "git commit failed")
        if res.ok and git_commit and git_push:
            pres = push(REPO_ROOT)
            if pres.ok:
                st.success("Pushed.")
            else:
                st.error(pres.stderr or pres.stdout or "git push failed")

# --- Kickoff (always visible at top)
st.markdown("### Kickoff")
kick_cols = st.columns([2, 1, 1])
with kick_cols[0]:
    objective = st.text_area(
        "Run objective",
        value=st.session_state.get("agent_chain_objective", "Evolve this repo into a campaign operations platform."),
        height=90,
    )
    st.session_state["agent_chain_objective"] = objective
with kick_cols[1]:
    if st.button("Create run"):
        paths = orch.create_run(objective=objective, created_by="streamlit")
        st.session_state["agent_chain_run_id"] = paths.run_id
        st.success(f"Created run `{paths.run_id}`")
        st.rerun()
with kick_cols[2]:
    run_ids = [r.run_id for r in runs]
    default_run_id = st.session_state.get("agent_chain_run_id") or (run_ids[0] if run_ids else "")
    if run_ids:
        selected_run_id = st.selectbox(
            "Active run",
            options=run_ids,
            index=run_ids.index(default_run_id) if default_run_id in run_ids else 0,
        )
        if selected_run_id:
            st.session_state["agent_chain_run_id"] = selected_run_id
    else:
        st.caption("No runs yet.")

if not st.session_state.get("agent_chain_run_id"):
    st.info("Create a run to begin.")
    st.stop()

paths = orch.get_run(st.session_state["agent_chain_run_id"])
state = orch.run_store.load_state(paths)

kickoff_cols = st.columns([1, 3])
with kickoff_cols[0]:
    if st.button("Run kickoff pipeline"):
        try:
            orch.run_kickoff(paths)
            st.success("Kickoff completed.")
        except Exception as exc:
            st.error(f"Kickoff failed: {exc}")
with kickoff_cols[1]:
    st.caption("Kickoff pipeline")
    pipeline = (state.get("kickoff") or {}).get("pipeline") or []
    if pipeline:
        st.write("\n".join([f"- **{step['agent']}**: {step['message'][:90]}..." for step in pipeline]))
    else:
        st.caption("No kickoff pipeline loaded yet (create a run).")

# --- Chat (always visible)
st.markdown("### Chat")
agent_names = list(orch.agents_config.agents.keys())
default_agent = "Supervisor" if "Supervisor" in agent_names else (agent_names[0] if agent_names else "")
chat_cols = st.columns([1, 1, 1, 2])
with chat_cols[0]:
    active_agent = st.selectbox(
        "Agent",
        options=agent_names,
        index=agent_names.index(st.session_state.get("agent_chain_active_agent", default_agent))
        if st.session_state.get("agent_chain_active_agent", default_agent) in agent_names
        else (agent_names.index(default_agent) if default_agent in agent_names else 0),
    )
    st.session_state["agent_chain_active_agent"] = active_agent
with chat_cols[1]:
    autopilot = st.checkbox("Supervisor autopilot", value=False)
with chat_cols[2]:
    auto_implement = st.checkbox("Executor (auto-implement)", value=False)
with chat_cols[3]:
    apply_to_repo = st.checkbox("Apply code changes to repo", value=False, disabled=not auto_implement)

status_cols = st.columns([1, 4])
with status_cols[0]:
    if st.button("Run status"):
        st.markdown(orch.run_status_markdown(paths))
with status_cols[1]:
    st.caption("Chat history shown is per-agent (last ~30 messages).")

state = orch.run_store.load_state(paths)
agent_state = (state.get("agents") or {}).get(active_agent) or {}
messages = agent_state.get("messages") or []
for msg in messages[-24:]:
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(content)

prompt = st.chat_input("Message the selected agent")
if prompt:
    if autopilot and active_agent == "Supervisor":
        try:
            opts = AutopilotOptions(
                max_rounds=3,
                write_artifacts_to_repo=False,
                auto_implement_code=auto_implement,
                apply_code_to_repo=apply_to_repo,
            )
            orch.supervisor_autopilot(paths, user_request=prompt, options=opts)
            state = orch.run_store.load_state(paths)
            sup = state.get("supervisor") or {}
            with st.chat_message("assistant"):
                st.markdown("**Supervisor autopilot update**")
                if sup.get("summary"):
                    st.markdown(sup["summary"])
                if sup.get("backlog"):
                    st.markdown("**Backlog**")
                    st.markdown("\n".join([f"- {item}" for item in sup["backlog"][:15]]))
        except Exception as exc:
            st.error(f"Autopilot failed: {exc}")
    else:
        try:
            resp = orch.call_agent(paths, agent_name=active_agent, message=prompt)
            with st.chat_message("assistant"):
                st.markdown(resp)
        except Exception as exc:
            st.error(f"Agent call failed: {exc}")

# --- View selector
st.markdown("### Views")
view = st.radio("Select view", ["Platform view", "Run details"], horizontal=True)

if view == "Platform view":
    st.markdown("#### Platform view (`app.py`)")
    st.caption("Start/stop the existing Streamlit app (`app.py`) and optionally embed it.")

    platform_cols = st.columns([1, 1, 2, 2])
    with platform_cols[0]:
        port = st.number_input("Port", min_value=1024, max_value=65535, value=int(st.session_state.get("platform_port", 8506)))
        st.session_state["platform_port"] = int(port)
    log_path = paths.run_dir / "platform_app.log"

    with platform_cols[1]:
        running = _is_pid_running(int(st.session_state.get("platform_pid", 0) or 0))
        st.caption("Running" if running else "Stopped")
    with platform_cols[2]:
        if st.button("Start / Restart"):
            pid = int(st.session_state.get("platform_pid", 0) or 0)
            if _is_pid_running(pid):
                _stop_process(pid)
            with open(log_path, "a", encoding="utf-8") as fp:
                proc = subprocess.Popen(
                    [
                        "python",
                        "-m",
                        "streamlit",
                        "run",
                        "app.py",
                        "--server.address",
                        "0.0.0.0",
                        "--server.port",
                        str(int(port)),
                        "--server.headless",
                        "true",
                    ],
                    cwd=str(REPO_ROOT),
                    stdout=fp,
                    stderr=fp,
                )
            st.session_state["platform_pid"] = proc.pid
            st.success(f"Started `app.py` (pid {proc.pid}) on port {int(port)}")
    with platform_cols[3]:
        if st.button("Stop"):
            pid = int(st.session_state.get("platform_pid", 0) or 0)
            _stop_process(pid)
            st.session_state["platform_pid"] = 0
            st.success("Stopped (SIGTERM sent).")

    pid = int(st.session_state.get("platform_pid", 0) or 0)
    if _is_pid_running(pid):
        url = f"http://localhost:{int(port)}"
        st.markdown(f"Open in browser: `{url}`")
        try:
            import streamlit.components.v1 as components

            components.iframe(url, height=800, scrolling=True)
        except Exception:
            st.info("Iframe embed not available in this environment.")

    st.markdown("#### Platform logs (tail)")
    st.code("\n".join(_read_text(log_path).splitlines()[-120:]) if log_path.exists() else "(no log yet)", language=None)

else:
    st.markdown("#### Run details")
    tab_summary, tab_snapshot, tab_state, tab_events = st.tabs(
        ["kickoff_summary.md", "repo_snapshot.md", "state.json", "events"]
    )
    with tab_summary:
        st.markdown(_read_text(paths.kickoff_summary_path))
    with tab_snapshot:
        st.markdown(_read_text(paths.repo_snapshot_path))
    with tab_state:
        st.json(state)
    with tab_events:
        events = state.get("events") or []
        if not events:
            st.caption("(no events yet)")
        else:
            for e in events[-80:][::-1]:
                st.markdown(f"- `{e.get('ts','')}` **{e.get('type','event')}** — `{e.get('agent','system')}`")

