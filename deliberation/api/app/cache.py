import json
import logging
import os
from typing import Any, Optional

try:
    import redis
except Exception:  # pragma: no cover - import guard for minimal environments
    redis = None


logger = logging.getLogger(__name__)
_redis_client = None


def _cache_ttl_seconds(default: int = 30) -> int:
    raw = os.getenv("REDIS_CACHE_TTL_SECONDS", str(default))
    try:
        parsed = int(raw)
    except Exception:
        return default
    return max(1, parsed)


def get_cache_ttl_seconds(default: int = 30) -> int:
    return _cache_ttl_seconds(default=default)


def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url or redis is None:
        return None
    try:
        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    except Exception as exc:
        logger.warning("redis_client_init_failed error=%s", exc)
        _redis_client = None
    return _redis_client


def ping_redis() -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception as exc:
        logger.warning("redis_ping_failed error=%s", exc)
        return False


def cache_get_json(key: str) -> Optional[Any]:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("redis_cache_get_failed key=%s error=%s", key, exc)
        return None


def cache_set_json(key: str, payload: Any, ttl_seconds: Optional[int] = None) -> None:
    client = get_redis_client()
    if client is None:
        return
    ttl = ttl_seconds if ttl_seconds is not None else _cache_ttl_seconds()
    try:
        client.setex(key, ttl, json.dumps(payload))
    except Exception as exc:
        logger.warning("redis_cache_set_failed key=%s error=%s", key, exc)


def cache_delete(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.warning("redis_cache_delete_failed key=%s error=%s", key, exc)


def close_redis_client() -> None:
    global _redis_client
    client = _redis_client
    _redis_client = None
    if client is None:
        return
    try:
        client.close()
    except Exception:
        pass
