from typing import Optional, Protocol

import redis


class TaskQueue(Protocol):
    def enqueue(self, job_id: str) -> bool:
        """Returns True if this call queued the job, False if it was deduplicated."""

    def dequeue(self, timeout: int = 1) -> Optional[str]:
        """Pops the next queued job id, or None when no item is available."""

    def ack(self, job_id: str) -> None:
        """Marks a queued job as processed so it can be re-queued later if needed."""


class RedisTaskQueue:
    def __init__(self, client: redis.Redis, queue_name: str):
        self._client = client
        self._queue_name = queue_name

    @classmethod
    def from_url(cls, redis_url: str, queue_name: str) -> "RedisTaskQueue":
        return cls(redis.Redis.from_url(redis_url, decode_responses=True), queue_name)

    def _dedupe_key(self, job_id: str) -> str:
        return f"{self._queue_name}:dedupe:{job_id}"

    def enqueue(self, job_id: str) -> bool:
        dedupe_key = self._dedupe_key(job_id)
        added = self._client.set(dedupe_key, "1", ex=86400, nx=True)
        if added:
            self._client.rpush(self._queue_name, job_id)
            return True
        return False

    def dequeue(self, timeout: int = 1) -> Optional[str]:
        if timeout > 0:
            item = self._client.blpop(self._queue_name, timeout=timeout)
            if not item:
                return None
            _, payload = item
            return str(payload)
        payload = self._client.lpop(self._queue_name)
        return str(payload) if payload else None

    def ack(self, job_id: str) -> None:
        self._client.delete(self._dedupe_key(job_id))

