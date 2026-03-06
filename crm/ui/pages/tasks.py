import pandas as pd
import streamlit as st

from crm.data.people import search_people
from crm.data.tasks import TASK_STATUSES, create_task, list_tasks, update_task_status


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
    create_cols = st.columns([2, 2, 2, 1])
    with create_cols[0]:
        person_query = st.text_input(
            "Find Person (Name/Email)",
            key="tasks_person_query",
            help="Search people by name/email to attach the task to a person.",
        )
        matches = search_people(person_query, limit=30) if person_query else pd.DataFrame()
        options = [""] + (
            matches["email"].tolist()
            if not matches.empty and "email" in matches.columns
            else []
        )
        person_email = st.selectbox(
            "Person",
            options=options,
            key="tasks_person_email",
            help="Pick the person who should receive this follow-up task.",
        )
    with create_cols[1]:
        title = st.text_input("Title *", key="tasks_title", help="Short task title (required).")
        due_date = st.text_input(
            "Due Date (YYYY-MM-DD, optional)",
            key="tasks_due_date",
            help="Optional due date. Stored as text (YYYY-MM-DD recommended).",
        )
    with create_cols[2]:
        description = st.text_area("Notes (optional)", height=80, key="tasks_description")
    with create_cols[3]:
        status_new = st.selectbox("New Status", TASK_STATUSES, index=0, key="tasks_new_status")
        if st.button("Add task", key="tasks_add_btn", help="Create a task linked to the selected person."):
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

    st.markdown("#### Task queue")
    if df.empty:
        st.info("No tasks found (yet).")
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
    st.dataframe(display_df, use_container_width=True)

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
                st.rerun()
            else:
                st.error("Update failed.")
