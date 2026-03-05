import requests
import streamlit as st

from crm.config import DELIBERATION_API_URL


def _delib_api_base_url():
    base = (DELIBERATION_API_URL or "").strip()
    return base.rstrip("/") if base else None


def _delib_api_url(path: str):
    base = _delib_api_base_url()
    if not base:
        return None
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def render_delib_api_unavailable():
    base = _delib_api_base_url()
    if base:
        st.warning("Deliberation backend is not reachable.")
        st.caption(f"Expected at `{base}`.")
        if "localhost" in base or "127.0.0.1" in base:
            st.caption(
                "Streamlit Cloud cannot reach your local machine. "
                "Deploy the deliberation API separately and set `DELIBERATION_API_URL`."
            )
    else:
        st.warning("Deliberation backend is not configured.")
        st.caption("Set `DELIBERATION_API_URL` (or `API_URL`) in `.env`.")
    st.caption("If running locally, start the service with:")
    st.code(
        "python -m uvicorn deliberation.api.app.main:app --host 0.0.0.0 --port 8010"
    )


def delib_api_get(path, show_error=True):
    url = _delib_api_url(path)
    if not url:
        if show_error:
            render_delib_api_unavailable()
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        if show_error:
            st.error(f"Deliberation API error: {exc}")
        return None


def delib_api_post(path, payload, headers=None, show_error=True):
    url = _delib_api_url(path)
    if not url:
        if show_error:
            render_delib_api_unavailable()
        return None
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        if show_error:
            st.error(f"Deliberation API error: {exc}")
        return None


def delib_api_patch(path, payload, show_error=True):
    url = _delib_api_url(path)
    if not url:
        if show_error:
            render_delib_api_unavailable()
        return None
    try:
        response = requests.patch(url, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        if show_error:
            st.error(f"Deliberation API error: {exc}")
        return None
