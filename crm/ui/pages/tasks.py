import pandas as pd
import streamlit as st
import altair as alt
from datetime import date

from crm.data.people import search_people
from crm.data.tasks import TASK_STATUSES, create_task, list_tasks, update_task_status
from crm.ui.components.table_utils import render_table_with_export


def render_tasks_tab():
    st.subheader("Tasks / Follow-ups")
    st.caption("Track follow-ups as tasks linked to people. This is a new feature and does not change existing tabs.")

    filter_cols = st.columns([1, 1, 1, 1])
    with filter_cols[0]:
        status_filter = st.selectbox(
            "Status",
            ["(any)"] + TASK_STATUSES,
            index=0,
            key="tasks_status_filter",
            help="Filter the task queue by status.",
        )
    with filter_cols[1]:
        group_filter = st.selectbox(
            "Group",
            ["(any)", "Supporter", "Member"],
            index=0,
            key="tasks_group_filter",
            help="Filter tasks by the person’s group (Supporter/Member).",
        )
    with filter_cols[2]:
        limit = st.number_input(
            "Limit",
            min_value=10,
            max_value=1000,
            value=300,
            step=10,
            key="tasks_limit",
            help="Max number of tasks to load.",
        )
    with filter_cols[3]:
        refresh = st.button("Refresh", key="tasks_refresh", help="Reload the task queue with the selected filters.")

    st.markdown("#### Create task")
    with st.form("tasks_person_search_form"):
        person_query = st.text_input(
            "Find Person (Name/Email)",
            key="tasks_person_query",
            help="Search people by name/email to attach the task to a person.",
        )
        search_clicked = st.form_submit_button("Search people")
    if search_clicked:
        query_clean = (person_query or "").strip()
        if len(query_clean) < 2:
            st.warning("Enter at least 2 characters to search.")
            st.session_state["tasks_person_query_committed"] = ""
        else:
            st.session_state["tasks_person_query_committed"] = query_clean
    committed_query = st.session_state.get("tasks_person_query_committed", "")

    matches = pd.DataFrame()
    if committed_query:
        with st.spinner("Searching people..."):
            matches = search_people(committed_query, limit=50)
    options = [""] + (
        matches["email"].tolist()
        if not matches.empty and "email" in matches.columns
        else []
    )
    if committed_query:
        st.caption(f"{len(options)-1:,} people found.")

    with st.form("tasks_create_form"):
        create_cols = st.columns([2, 2, 2, 1])
        with create_cols[0]:
            person_email = st.selectbox(
                "Person",
                options=options,
                key="tasks_person_email",
                help="Pick the person who should receive this follow-up task.",
            )
        with create_cols[1]:
            title = st.text_input(
                "Title *", key="tasks_title", help="Short task title (required)."
            )
            set_due = st.checkbox("Set due date", value=False, key="tasks_set_due")
            due_date_value = st.date_input(
                "Due date",
                value=date.today(),
                key="tasks_due_date_picker",
                disabled=not set_due,
            )
        with create_cols[2]:
            description = st.text_area("Notes (optional)", height=80, key="tasks_description")
        with create_cols[3]:
            status_new = st.selectbox("New Status", TASK_STATUSES, index=0, key="tasks_new_status")
            add_task_clicked = st.form_submit_button(
                "Add task", help="Create a task linked to the selected person."
            )
    if add_task_clicked:
        due_date = due_date_value.isoformat() if set_due else ""
        ok = create_task(
            person_email,
            title,
            description=description,
            due_date=due_date,
            status=status_new,
        )
        if ok:
            st.success("Task created.")
        else:
            st.error("Could not create task (check person + title).")

    st.markdown("---")

    status = None if status_filter == "(any)" else status_filter
    group = None if group_filter == "(any)" else group_filter
    df = list_tasks(status=status, group=group, limit=limit)
    if refresh:
        df = list_tasks(status=status, group=group, limit=limit)

    if not df.empty and "status" in df.columns:
        st.markdown("#### Task statistics")
        status_counts = (
            df["status"]
            .fillna("Open")
            .value_counts()
            .rename_axis("status")
            .reset_index(name="count")
        )
        total_tasks = int(status_counts["count"].sum())
        completed_tasks = int(
            status_counts.loc[status_counts["status"] == "Done", "count"].sum()
        )
        completion_rate = (completed_tasks / total_tasks * 100.0) if total_tasks else 0.0
        metrics = st.columns(3)
        metrics[0].metric("Total tasks", f"{total_tasks:,}")
        metrics[1].metric("Completed", f"{completed_tasks:,}")
        metrics[2].metric("Completion rate", f"{completion_rate:.1f}%")

        status_chart = (
            alt.Chart(status_counts)
            .mark_bar()
            .encode(
                x=alt.X("status:N", title="Task status"),
                y=alt.Y("count:Q", title="Count"),
                tooltip=["status:N", "count:Q"],
                color=alt.Color("status:N", legend=None),
            )
        )
        st.altair_chart(status_chart, use_container_width=True)

    st.markdown("#### Task queue")
    if df.empty:
        st.info("No tasks found yet. Create a task above.")
        return

    display_df = df[
        [
            "title",
            "status",
            "dueDate",
            "firstName",
            "lastName",
            "email",
            "group",
            "updatedAt",
        ]
    ].rename(
        columns={
            "title": "Title",
            "status": "Status",
            "dueDate": "Due",
            "firstName": "First",
            "lastName": "Last",
            "email": "Email",
            "group": "Group",
            "updatedAt": "Updated",
        }
    )
    st.caption(f"{len(display_df):,} tasks shown")
    display_df["Due"] = pd.to_datetime(display_df["Due"], errors="coerce")
    display_df["Email"] = display_df["Email"].apply(
        lambda value: f"mailto:{value}" if isinstance(value, str) and value.strip() else ""
    )
    render_table_with_export(
        display_df,
        key_prefix="tasks_queue",
        filename="tasks_queue.csv",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=TASK_STATUSES),
            "Due": st.column_config.DateColumn("Due", format="YYYY-MM-DD"),
            "Email": st.column_config.LinkColumn("Email", display_text=r"mailto:(.*)"),
        },
    )

    st.markdown("#### Update task status")
    task_ids = df["taskId"].tolist() if "taskId" in df.columns else []
    upd_cols = st.columns([2, 1, 1])
    with upd_cols[0]:
        selected_task = st.selectbox("Task", options=[""] + task_ids, key="tasks_update_task")
    with upd_cols[1]:
        new_status = st.selectbox("Set Status", TASK_STATUSES, key="tasks_update_status")
    with upd_cols[2]:
        if st.button("Update", key="tasks_update_btn", help="Update the selected task’s status."):
            ok = update_task_status(selected_task, new_status)
            if ok:
                st.success("Updated.")
            else:
                st.error("Update failed.")
