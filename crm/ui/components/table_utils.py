import streamlit as st


def render_table_with_export(
    df,
    *,
    key_prefix: str,
    filename: str,
    column_config: dict | None = None,
    height: int | None = None,
):
    st.dataframe(
        df,
        use_container_width=True,
        column_config=column_config or {},
        height=height,
    )
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Export current table (CSV)",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        key=f"{key_prefix}_export_csv",
    )
