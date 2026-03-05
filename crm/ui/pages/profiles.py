import pandas as pd
import streamlit as st

from crm.analytics.people import load_map_data, load_supporter_summary
from crm.data.people import load_person_profile, search_people, update_person_profile
from crm.data.tasks import create_task, list_tasks
from crm.utils.text import format_list_label


def render_profiles_tab():
    st.subheader("Profiles")
    st.caption(
        "Search and open a person profile. New feature; existing Supporter/Member forms remain unchanged."
    )

    query = st.text_input("Search by Name or Email", key="profiles_search")
    matches = search_people(query, limit=80) if query else pd.DataFrame()
    if matches.empty:
        st.info("Search to find a person.")
        return

    label_rows = [
        f"{row.get('fullName','')} — {row.get('email','')}" for _, row in matches.iterrows()
    ]
    selection = st.selectbox("Select Person", options=[""] + label_rows, key="profiles_select")
    if not selection:
        return
    idx = label_rows.index(selection)
    email = matches.iloc[idx].get("email")
    if not email:
        st.warning("Selected row missing email.")
        return

    prof = load_person_profile(email)
    if prof.empty:
        st.error("No profile found.")
        return

    row = prof.iloc[0].to_dict()
    summary_cols = st.columns(3)
    summary_cols[0].markdown(f"**Email**: `{email}`")
    summary_cols[1].markdown(f"**Tags**: {format_list_label(row.get('tags') or [])}")
    summary_cols[2].markdown(f"**Skills**: {format_list_label(row.get('skills') or [])}")

    details_tab, tasks_tab = st.tabs(["Details", "Tasks"])
    with details_tab:
        reveal = st.checkbox(
            "Reveal contact fields (PII)",
            value=False,
            key="profiles_reveal",
            help="When off, sensitive contact fields are masked to reduce accidental exposure.",
        )
        form_cols = st.columns(2)
        with form_cols[0]:
            first = st.text_input(
                "First Name", value=row.get("firstName") or "", key="profiles_first"
            )
            last = st.text_input(
                "Last Name", value=row.get("lastName") or "", key="profiles_last"
            )
            phone = st.text_input(
                "Phone",
                value=(row.get("phone") or "") if reveal else "••••••",
                key="profiles_phone",
                disabled=not reveal,
            )
            gender = st.selectbox(
                "Gender", ["", "Male", "Female", "Other"], index=0, key="profiles_gender"
            )
            age_val = row.get("age")
            age = st.number_input(
                "Age",
                min_value=0,
                max_value=120,
                value=int(age_val)
                if isinstance(age_val, (int, float)) and not pd.isna(age_val)
                else 0,
                step=1,
                key="profiles_age",
            )
        with form_cols[1]:
            time_availability = st.selectbox(
                "Time Availability",
                ["", "Weekends", "Evenings", "Full-time", "Ad-hoc", "Unspecified"],
                index=0,
                key="profiles_time",
            )
            about = st.text_area(
                "Motivation / Notes",
                value=row.get("about") or "",
                height=120,
                key="profiles_about",
            )
            agrees = st.checkbox(
                "Agrees with Manifesto",
                value=bool(row.get("agreesWithManifesto")),
                key="profiles_agrees",
            )
            interested = st.checkbox(
                "Interested in Party Membership",
                value=bool(row.get("interestedInMembership")),
                key="profiles_interested",
            )
            fb = st.checkbox(
                "Facebook Group Member",
                value=bool(row.get("facebookGroupMember")),
                key="profiles_fb",
            )

        if st.button(
            "Save profile updates",
            key="profiles_save_btn",
            help="Write profile field updates to Neo4j.",
        ):
            payload = {
                "firstName": first,
                "lastName": last,
                "phone": phone if reveal else row.get("phone"),
                "gender": gender,
                "age": age if age else None,
                "timeAvailability": time_availability
                if time_availability and time_availability != "Unspecified"
                else "Unspecified",
                "about": about,
                "agreesWithManifesto": agrees,
                "interestedInMembership": interested,
                "facebookGroupMember": fb,
            }
            ok = update_person_profile(email, payload)
            if ok:
                load_supporter_summary.clear()
                load_map_data.clear()
                st.success("Saved.")
            else:
                st.error("Save failed.")

    with tasks_tab:
        st.markdown("#### Tasks for this person")
        tcols = st.columns([2, 2, 1])
        with tcols[0]:
            t_title = st.text_input("Task Title *", key="profiles_task_title")
        with tcols[1]:
            t_due = st.text_input("Due Date (YYYY-MM-DD, optional)", key="profiles_task_due")
        with tcols[2]:
            if st.button(
                "Add task",
                key="profiles_add_task",
                help="Create a follow-up task for this person.",
            ):
                ok = create_task(email, t_title, due_date=t_due, status="Open")
                if ok:
                    st.success("Task added.")
                else:
                    st.error("Could not add task.")

        tdf = list_tasks(person_email=email, limit=200)
        if tdf.empty:
            st.caption("No tasks yet.")
        else:
            st.dataframe(
                tdf[["title", "status", "dueDate", "updatedAt"]].rename(
                    columns={
                        "title": "Title",
                        "status": "Status",
                        "dueDate": "Due",
                        "updatedAt": "Updated",
                    }
                ),
                use_container_width=True,
            )
