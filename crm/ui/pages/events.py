import streamlit as st
import pandas as pd
from datetime import date

from crm.data.events import (
    EVENT_REGISTRATION_STATUSES,
    EVENT_STATUSES,
    create_event,
    list_event_registrations,
    list_events,
    register_person_to_event,
)
from crm.ui.components.table_utils import render_table_with_export


def _split_full_name(full_name):
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


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
                    "Status",
                    EVENT_STATUSES,
                    key="events_status",
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

    events_df = list_events()
    if events_df.empty:
        st.info("No events found yet. Create an event first.")
    else:
        event_labels = []
        event_lookup = {}
        for _, row in events_df.iterrows():
            start = (row.get("startDate") or "").strip()
            start_label = f" — {start}" if start else ""
            label = f"{row.get('name', 'Untitled event')}{start_label}"
            if label in event_lookup:
                label = f"{label} ({str(row.get('eventId'))[:8]})"
            event_lookup[label] = row.get("eventId")
            event_labels.append(label)

        with st.expander("Event registration form", expanded=True):
            with st.form("events_registration_form", clear_on_submit=True):
                selected_event_label = st.selectbox(
                    "Event *",
                    options=[""] + event_labels,
                    key="events_registration_event",
                    help="Select which event this person is registering for.",
                )
                full_name = st.text_input("Full name *", key="events_registration_full_name")
                email = st.text_input("Email *", key="events_registration_email")
                phone = st.text_input("Phone (optional)", key="events_registration_phone")
                group = st.selectbox(
                    "Group",
                    ["Supporter", "Member"],
                    key="events_registration_group",
                )
                registration_status = st.selectbox(
                    "Registration status",
                    EVENT_REGISTRATION_STATUSES,
                    key="events_registration_status",
                )
                registration_notes = st.text_area(
                    "Registration notes (optional)",
                    key="events_registration_notes",
                    height=80,
                )
                register_clicked = st.form_submit_button("Register person")

            if register_clicked:
                event_id = event_lookup.get(selected_event_label)
                first_name, last_name = _split_full_name(full_name)
                person_payload = {
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "phone": phone,
                    "group": group,
                }
                if not event_id:
                    st.error("Select an event.")
                elif not str(email or "").strip():
                    st.error("Email is required.")
                elif not str(full_name or "").strip():
                    st.error("Full name is required.")
                elif register_person_to_event(
                    event_id,
                    person_payload,
                    status=registration_status,
                    notes=registration_notes,
                ):
                    st.success("Person registered to event.")
                else:
                    st.error("Could not register person.")

        with st.expander("Registrations by event", expanded=False):
            selected_event_label = st.selectbox(
                "View registrations for event",
                options=[""] + event_labels,
                key="events_registration_view_event",
            )
            selected_event_id = event_lookup.get(selected_event_label)
            if selected_event_id:
                reg_df = list_event_registrations(selected_event_id, limit=2000)
                if reg_df.empty:
                    st.info("No registrations for this event yet.")
                else:
                    render_table_with_export(
                        reg_df,
                        key_prefix="events_registrations_table",
                        filename="event_registrations.csv",
                        column_config={
                            "registrationStatus": st.column_config.SelectboxColumn(
                                "Registration status",
                                options=EVENT_REGISTRATION_STATUSES,
                            )
                        },
                    )

    st.markdown("### Event list")
    if events_df.empty:
        st.info("No events found. Create one above.")
    else:
        event_df = events_df.rename(
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
