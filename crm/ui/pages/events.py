import streamlit as st

from crm.data.events import create_event, list_events


def render_events_page():
    st.subheader("Events")
    st.caption("Create and track campaign events.")

    with st.expander("Create event", expanded=True):
        form_cols = st.columns(2)
        with form_cols[0]:
            name = st.text_input("Event name *", key="events_name")
            start_date = st.text_input("Start date", key="events_start")
            end_date = st.text_input("End date", key="events_end")
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

        if st.button("Create event", key="events_create_btn"):
            ok = create_event(
                {
                    "name": name,
                    "startDate": start_date,
                    "endDate": end_date,
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
        st.info("No events found.")
    else:
        st.dataframe(
            df.rename(
                columns={
                    "name": "Name",
                    "startDate": "Start",
                    "endDate": "End",
                    "location": "Location",
                    "status": "Status",
                    "capacity": "Capacity",
                    "registrations": "Registrations",
                }
            ),
            use_container_width=True,
        )
