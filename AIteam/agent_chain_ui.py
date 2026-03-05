from __future__ import annotations

from pathlib import Path

import streamlit as st

from AIteam.agent_chain.orchestrator import AutopilotOptions, Orchestrator


REPO_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Agent Chain (agents-only)", layout="wide")
st.title("Agent Chain (agents-only UI)")
st.caption("Lightweight view focused on kickoff/chat/autopilot. Use `console.py` for the full console.")

orch = Orchestrator(repo_root=REPO_ROOT)
runs = orch.list_runs()

run_ids = [r.run_id for r in runs]
if not run_ids:
    st.info("No runs yet. Use `console.py` to create a run.")
    st.stop()

run_id = st.selectbox("Run", options=run_ids, index=0)
paths = orch.get_run(run_id)

agent_names = list(orch.agents_config.agents.keys())
active_agent = st.selectbox("Agent", options=agent_names, index=agent_names.index("Supervisor") if "Supervisor" in agent_names else 0)
autopilot = st.checkbox("Supervisor autopilot", value=False)

prompt = st.chat_input("Message the agent")
if prompt:
    if autopilot and active_agent == "Supervisor":
        orch.supervisor_autopilot(paths, user_request=prompt, options=AutopilotOptions())
        state = orch.run_store.load_state(paths)
        sup = state.get("supervisor") or {}
        st.markdown("### Autopilot update")
        st.markdown(sup.get("summary") or "(no summary)")
    else:
        resp = orch.call_agent(paths, agent_name=active_agent, message=prompt)
        st.markdown(resp)

