from __future__ import annotations

import streamlit as st

from crm.analytics.people import load_map_data, load_supporter_summary
from crm.ui.components.import_export import render_import_export_section
from crm.data.people import upsert_person
from crm.ui.pages.profiles import render_profiles_tab
from crm.ui.shell import (
    apply_global_styles,
    ensure_db_connection,
    ensure_supporter_access,
    handle_special_entrypoints,
)


st.set_page_config(page_title="Freedom Square CRM", layout="wide")
apply_global_styles()
if handle_special_entrypoints():
    st.stop()
if not ensure_supporter_access("People"):
    st.stop()
if not ensure_db_connection():
    st.stop()

st.subheader("People")
people_tab, profile_tab = st.tabs(["Directory", "Profile"])

with people_tab:
    st.markdown("#### New person")
    with st.form("people_new_person_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First name")
            email = st.text_input("Email *")
            supporter_type = st.selectbox("Type", ["Supporter", "Member"], index=0)
            gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], index=0)
            age = st.number_input("Age", min_value=0, max_value=120, value=0, step=1)
        with c2:
            last_name = st.text_input("Last name")
            phone = st.text_input("Phone")
            address = st.text_input("Address")
            lat = st.number_input("Latitude", value=0.0, format="%.6f")
            lon = st.number_input("Longitude", value=0.0, format="%.6f")
        save_person = st.form_submit_button("Save person")
    if save_person:
        payload = {
            "email": (email or "").strip(),
            "firstName": (first_name or "").strip(),
            "lastName": (last_name or "").strip(),
            "gender": (gender or "").strip(),
            "age": int(age) if age else None,
            "phone": (phone or "").strip(),
            "lat": float(lat) if lat else None,
            "lon": float(lon) if lon else None,
            "effortHours": None,
            "eventsAttendedCount": None,
            "referralCount": None,
            "supporterType": supporter_type,
            "address": (address or "").strip(),
        }
        if not payload["email"]:
            st.error("Email is required.")
        elif upsert_person(payload):
            load_supporter_summary.clear()
            load_map_data.clear()
            st.success(f"{supporter_type} saved.")
        else:
            st.error("Could not save person.")

    st.markdown("---")
    group_view = st.radio(
        "View",
        ["Supporters", "Members"],
        horizontal=True,
        key="people_group_view_multipage",
    )
    target_group = "Supporter" if group_view == "Supporters" else "Member"
    df_summary = load_supporter_summary()
    if df_summary.empty:
        st.info("No people found.")
    else:
        people = df_summary[df_summary["group"] == target_group]
        if people.empty:
            st.info(f"No {target_group.lower()}s found.")
        else:
            sort_choice = st.selectbox(
                "Sort by",
                ["Name", "Effort score", "Events attended", "Referrals"],
                key="people_sort_multipage",
            )
            if sort_choice == "Effort score" and "effortScore" in people.columns:
                people = people.sort_values("effortScore", ascending=False)
            elif sort_choice == "Events attended" and "eventAttendCount" in people.columns:
                people = people.sort_values("eventAttendCount", ascending=False)
            elif sort_choice == "Referrals" and "referralCount" in people.columns:
                people = people.sort_values("referralCount", ascending=False)
            elif "fullName" in people.columns:
                people = people.sort_values("fullName")

            cols = [
                "fullName",
                "email",
                "effortHours",
                "eventAttendCount",
                "referralCount",
                "effortScore",
                "joinCount",
                "skillCount",
                "educationLevel",
                "ratingStars",
                "gender",
                "age",
            ]
            existing_cols = [col for col in cols if col in people.columns]
            display_df = people[existing_cols].rename(
                columns={
                    "fullName": "Name",
                    "email": "Email",
                    "effortHours": "Effort Hours",
                    "eventAttendCount": "Events Attended",
                    "referralCount": "Referrals",
                    "effortScore": "Effort Score",
                    "joinCount": "Joined",
                    "skillCount": "Skills",
                    "educationLevel": "Education",
                    "ratingStars": "Rating",
                    "gender": "Gender",
                    "age": "Age",
                }
            )
            st.caption(f"{len(display_df):,} people shown")
            st.dataframe(display_df, use_container_width=True)
    section_id = "supporters" if target_group == "Supporter" else "members"
    render_import_export_section(section_id, target_group, target_group)

with profile_tab:
    render_profiles_tab()
