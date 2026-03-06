import streamlit as st

from crm.data.people import search_people
from crm.data.segments import list_segments, load_segment_filter, run_segment
from crm.data.tasks import TASK_STATUSES, bulk_create_tasks


def _render_template(template, context):
    if not template:
        return ""
    try:
        return template.format(**context)
    except Exception:
        return template


def _render_task_builder(target_df, prefix):
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
        key=f"{prefix}_task_preset",
        help="Pick a preset or use Custom and write your own template.",
    )
    title_key = f"{prefix}_task_title_template"
    if title_key not in st.session_state:
        st.session_state[title_key] = presets[preset_choice]
    if st.button(
        "Apply preset",
        key=f"{prefix}_apply_preset",
        help="Fill the task title template with the selected preset.",
    ):
        st.session_state[title_key] = presets[preset_choice]
    title_template = st.text_input(
        "Task title template",
        key=title_key,
        help="Use placeholders like {fullName}, {email}, {group}.",
    )
    desc_template = st.text_area(
        "Task notes (optional)",
        value="",
        key=f"{prefix}_task_desc_template",
        help="Optional notes. Same placeholders are supported.",
    )
    due_date = st.text_input(
        "Due date (YYYY-MM-DD, optional)",
        value="",
        key=f"{prefix}_task_due",
    )
    status = st.selectbox(
        "Task status",
        TASK_STATUSES,
        index=0,
        key=f"{prefix}_task_status",
    )
    if st.button(
        "Create tasks",
        key=f"{prefix}_create_tasks",
        help="Create tasks for everyone in the selected target list.",
    ):
        rows = []
        for _, row in target_df.iterrows():
            context = {key: row.get(key, "") for key in target_df.columns}
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


def _render_segment_outreach():
    st.markdown("### Segment outreach")
    st.caption("Choose a saved segment and create outreach tasks in bulk.")
    segments_df = list_segments()
    if segments_df.empty:
        st.info("No saved segments yet.")
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
    _render_task_builder(rdf, prefix="outreach_segment")


def _render_individual_outreach():
    st.markdown("### Individual outreach")
    st.caption("Select specific people and create outreach tasks.")
    query = st.text_input(
        "Search people by name or email",
        key="outreach_individual_search",
        help="Find people to include in this outreach batch.",
    )
    if not query.strip():
        st.info("Search to find people for individual outreach.")
        return

    matches = search_people(query, limit=200)
    if matches.empty:
        st.info("No people found for that search.")
        return
    if "email" not in matches.columns:
        st.error("Search results missing email field.")
        return

    matches = matches.dropna(subset=["email"]).copy()
    if matches.empty:
        st.info("No people with valid email found.")
        return
    if "fullName" not in matches.columns:
        matches["fullName"] = matches["email"]
    if "group" not in matches.columns:
        matches["group"] = "Supporter"

    matches["label"] = (
        matches["fullName"].astype(str)
        + " — "
        + matches["email"].astype(str)
        + " ("
        + matches["group"].astype(str)
        + ")"
    )
    selected_labels = st.multiselect(
        "Choose people",
        options=matches["label"].tolist(),
        default=[],
        key="outreach_individual_selected",
        help="Select one or more people for this outreach task batch.",
    )
    if not selected_labels:
        st.caption("Select people to continue.")
        return

    target_df = matches[matches["label"].isin(selected_labels)].copy()
    if target_df.empty:
        st.info("No valid people selected.")
        return

    preview_cols = [
        col
        for col in ["fullName", "email", "group", "timeAvailability"]
        if col in target_df.columns
    ]
    st.markdown("### Selected people")
    st.caption(f"{len(target_df):,} people selected.")
    st.dataframe(target_df[preview_cols] if preview_cols else target_df, use_container_width=True)
    _render_task_builder(target_df, prefix="outreach_individual")


def render_outreach_page():
    st.subheader("Outreach")
    st.caption("Choose outreach target type: segments or individuals.")
    target_mode = st.radio(
        "Outreach target",
        ["Segments", "Individuals"],
        horizontal=True,
        key="outreach_target_mode",
        help="Use saved segments for bulk outreach or pick specific individuals.",
    )
    if target_mode == "Segments":
        _render_segment_outreach()
    else:
        _render_individual_outreach()

    st.markdown("### Messaging campaigns")
    st.info("SMS/email campaign tools are in progress. Use task lists for now.")
