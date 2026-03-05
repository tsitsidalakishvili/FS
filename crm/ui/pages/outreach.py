import streamlit as st

from crm.data.segments import list_segments, load_segment_filter, run_segment
from crm.data.tasks import TASK_STATUSES, bulk_create_tasks


def _render_template(template, context):
    if not template:
        return ""
    try:
        return template.format(**context)
    except Exception:
        return template


def render_outreach_page():
    st.subheader("Outreach")
    st.caption("Create tasks and outreach lists from segments.")

    segments_df = list_segments()
    if segments_df.empty:
        st.info("Create a segment first to build outreach lists.")
        return

    names = segments_df["name"].dropna().tolist() if "name" in segments_df.columns else []
    sel = st.selectbox(
        "Select segment",
        options=[""] + names,
        key="outreach_segment_select",
        help="Choose a segment to build an outreach list.",
    )
    if not sel:
        st.caption("Pick a segment to preview and create tasks.")
        return

    seg_rows = segments_df[segments_df["name"] == sel]
    seg_id = (
        seg_rows["segmentId"].iloc[0]
        if not seg_rows.empty and "segmentId" in seg_rows.columns
        else None
    )
    if not seg_id:
        st.error("Could not resolve segment.")
        return

    spec = load_segment_filter(seg_id)
    limit = st.number_input(
        "Preview limit",
        min_value=10,
        max_value=2000,
        value=200,
        step=50,
        key="outreach_preview_limit",
        help="Max number of people to preview + target for tasks.",
    )
    rdf = run_segment(spec, limit=limit)
    if rdf.empty:
        st.info("No matches for this segment.")
        return

    st.markdown("### Segment preview")
    st.caption(f"{len(rdf):,} people in this preview.")
    st.dataframe(rdf, use_container_width=True)

    st.markdown("### Create tasks")
    presets = {
        "Call": "Call {fullName}",
        "Text": "Text {fullName}",
        "Email": "Email {fullName}",
        "Follow-up": "Follow up with {fullName}",
        "Custom": "",
    }
    preset_choice = st.selectbox(
        "Task preset",
        list(presets.keys()),
        index=0,
        key="outreach_task_preset",
        help="Pick a preset or use Custom and write your own template.",
    )
    if "outreach_task_title_template" not in st.session_state:
        st.session_state["outreach_task_title_template"] = presets[preset_choice]
    if st.button(
        "Apply preset",
        key="outreach_apply_preset",
        help="Fill the task title template with the selected preset.",
    ):
        st.session_state["outreach_task_title_template"] = presets[preset_choice]
    title_template = st.text_input(
        "Task title template",
        key="outreach_task_title_template",
        help="Use placeholders like {fullName}, {email}, {group}.",
    )
    desc_template = st.text_area(
        "Task notes (optional)",
        value="",
        key="outreach_task_desc_template",
        help="Optional notes. Same placeholders are supported.",
    )
    due_date = st.text_input(
        "Due date (YYYY-MM-DD, optional)",
        value="",
        key="outreach_task_due",
    )
    status = st.selectbox(
        "Task status",
        TASK_STATUSES,
        index=0,
        key="outreach_task_status",
    )
    if st.button(
        "Create tasks",
        key="outreach_create_tasks",
        help="Create tasks for everyone in this segment preview.",
    ):
        rows = []
        for _, row in rdf.iterrows():
            context = {key: row.get(key, "") for key in row.index}
            rows.append(
                {
                    "email": row.get("email"),
                    "title": _render_template(title_template, context),
                    "description": _render_template(desc_template, context),
                    "dueDate": due_date,
                    "status": status,
                }
            )
        created = bulk_create_tasks(rows, default_status=status)
        if created:
            st.success(f"Created {created} tasks.")
        else:
            st.error("No tasks created (missing emails or titles).")

    st.markdown("### Messaging campaigns")
    st.info("SMS/email campaign tools are in progress. Use task lists for now.")
