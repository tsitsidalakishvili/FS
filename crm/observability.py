import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def setup_streamlit_observability(service_name: str = "freedom-square-crm") -> bool:
    logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    sentry_dsn = (os.getenv("CRM_SENTRY_DSN") or os.getenv("SENTRY_DSN") or "").strip()
    if not sentry_dsn:
        return False
    if not _bool_env("SENTRY_ENABLE_STREAMLIT", True):
        return False
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("APP_RELEASE"),
        traces_sample_rate=_float_env("SENTRY_TRACES_SAMPLE_RATE", 0.0),
        profiles_sample_rate=_float_env("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
        send_default_pii=_bool_env("SENTRY_SEND_DEFAULT_PII", False),
        integrations=[sentry_logging],
        server_name=service_name,
    )
    return True
