import requests
import streamlit as st

from crm.config import DELIBERATION_API_TIMEOUT_S, DELIBERATION_API_URL


def _parse_timeout_seconds(value, default=20.0):
    try:
        timeout = float(value)
    except Exception:
        timeout = default
    return max(1.0, timeout)


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


def _effective_timeout(url: str) -> float:
    timeout = _parse_timeout_seconds(DELIBERATION_API_TIMEOUT_S, default=20.0)
    # Render free services can cold-start in ~50s, so use a safer minimum there.
    if "onrender.com" in url:
        return max(timeout, 70.0)
    return timeout


def _request_json(method, path, payload=None, headers=None, show_error=True):
    url = _delib_api_url(path)
    if not url:
        if show_error:
            render_delib_api_unavailable()
        return None
    timeout = _effective_timeout(url)
    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        if show_error:
            if "onrender.com" in url:
                st.error(
                    "Deliberation API timed out while waking up (Render cold start). "
                    "Please wait ~1 minute and retry."
                )
            else:
                st.error(f"Deliberation API timeout: {exc}")
        return None
    except requests.RequestException as exc:
        if show_error:
            st.error(f"Deliberation API error: {exc}")
        return None


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
    return _request_json("GET", path, show_error=show_error)


def delib_api_post(path, payload, headers=None, show_error=True):
    return _request_json("POST", path, payload=payload, headers=headers, show_error=show_error)


def delib_api_patch(path, payload, show_error=True):
    return _request_json("PATCH", path, payload=payload, show_error=show_error)
