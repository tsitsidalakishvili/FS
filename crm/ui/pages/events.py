import streamlit as st
import pandas as pd
from datetime import date

from crm.data.events import create_event, list_events
from crm.ui.components.table_utils import render_table_with_export


def render_events_page():
    st.subheader("Events")
    st.caption("Create and track campaign events.")

    with st.expander("Create event", expanded=True):
        with st.form("events_create_form"):
            form_cols = st.columns(2)
            with form_cols[0]:
                name = st.text_input("Event name *", key="events_name")
                set_start = st.checkbox("Set start date", value=False, key="events_set_start")
                start_date_val = st.date_input(
                    "Start date",
                    value=date.today(),
                    key="events_start",
                    disabled=not set_start,
                )
                set_end = st.checkbox("Set end date", value=False, key="events_set_end")
                end_date_val = st.date_input(
                    "End date",
                    value=date.today(),
                    key="events_end",
                    disabled=not set_end,
                )
                location = st.text_input("Location", key="events_location")
            with form_cols[1]:
                status = st.selectbox(
                    "Status", ["Planned", "Scheduled", "Completed", "Cancelled"], key="events_status"
                )
                capacity = st.number_input(
                    "Capacity",
                    min_value=0,
                    value=0,
                    step=10,
                    key="events_capacity",
                )
                notes = st.text_area("Notes", key="events_notes", height=80)
            create_clicked = st.form_submit_button("Create event")

        if create_clicked:
            ok = create_event(
                {
                    "name": name,
                    "startDate": start_date_val.isoformat() if set_start else "",
                    "endDate": end_date_val.isoformat() if set_end else "",
                    "location": location,
                    "status": status,
                    "capacity": capacity,
                    "notes": notes,
                }
            )
            if ok:
                st.success("Event created.")
            else:
                st.error("Event name is required.")

    st.markdown("### Event list")
    df = list_events()
    if df.empty:
        st.info("No events found. Create one above.")
    else:
        event_df = df.rename(
            columns={
                "name": "Name",
                "startDate": "Start",
                "endDate": "End",
                "location": "Location",
                "status": "Status",
                "capacity": "Capacity",
                "registrations": "Registrations",
            }
        )
        event_df["Start"] = pd.to_datetime(event_df["Start"], errors="coerce")
        event_df["End"] = pd.to_datetime(event_df["End"], errors="coerce")
        render_table_with_export(
            event_df,
            key_prefix="events_table",
            filename="events.csv",
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Planned", "Scheduled", "Completed", "Cancelled"],
                ),
                "Start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
                "End": st.column_config.DateColumn("End", format="YYYY-MM-DD"),
            },
        )
