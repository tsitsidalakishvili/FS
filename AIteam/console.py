from __future__ import annotations

from pathlib import Path

import streamlit as st

from AIteam.agent_chain.orchestrator import AutopilotOptions, Orchestrator


REPO_ROOT = Path(__file__).resolve().parents[1]


st.set_page_config(page_title="AIteam Console", layout="wide")
st.title("AIteam Console (Agent Chain)")

orch = Orchestrator(repo_root=REPO_ROOT)

st.markdown("### Kickoff")
objective = st.text_area("Objective", value="Improve the CRM app safely.", height=80)
cols = st.columns([1, 2])
with cols[0]:
    if st.button("Create run"):
        paths = orch.create_run(objective=objective, created_by="streamlit")
        st.session_state["run_id"] = paths.run_id
        st.success(f"Created run `{paths.run_id}`")
        st.rerun()
with cols[1]:
    runs = orch.list_runs()
    run_ids = [r.run_id for r in runs]
    if run_ids:
        st.session_state["run_id"] = st.selectbox("Active run", options=run_ids, index=0)
    else:
        st.info("No runs yet.")

run_id = st.session_state.get("run_id")
if not run_id:
    st.stop()

paths = orch.get_run(run_id)

st.markdown("### Chat")
agent_ids = list(orch.agents_config.agents.keys())
default_agent = "Supervisor" if "Supervisor" in agent_ids else agent_ids[0]

def _fmt(agent_id: str) -> str:
    return orch.agents_config.agents[agent_id].display_name

agent = st.selectbox("Agent", options=agent_ids, index=agent_ids.index(default_agent), format_func=_fmt)
autopilot = st.checkbox("CRM Supervisor autopilot", value=False)
rounds = st.number_input("Rounds", min_value=1, max_value=10, value=3, step=1)

prompt = st.chat_input("Message")
if prompt:
    if autopilot and agent == "Supervisor":
        orch.supervisor_autopilot(paths, user_request=prompt, options=AutopilotOptions(max_rounds=int(rounds)))
        state = orch.run_store.load_state(paths)
        sup = state.get("supervisor") or {}
        st.markdown(sup.get("summary") or "(no summary)")
    else:
        st.markdown(orch.call_agent(paths, agent_name=agent, message=prompt))

