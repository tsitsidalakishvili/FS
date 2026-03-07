import streamlit as st


def render_due_diligence_page():
    st.subheader("Due Diligence")
    st.write(
        "DD module will help the team run structured checks on people, organizations, "
        "and opportunities before decisions are made."
    )
    st.caption("Planned scope: verification, risk flags, evidence notes, and approval tracking.")
