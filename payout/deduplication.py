import hashlib
from datetime import date

import redis as redis_lib

from config.settings import settings

# 90-day TTL in seconds
DEDUP_TTL_SECONDS = 90 * 24 * 60 * 60


def generate_idempotency_key(farm_id: str, rule_id: str, event_date: date) -> str:
    """
    Generate a deterministic, non-guessable idempotency key.
    Same farm + rule + date always produces the same key.
    """
    raw = f"{farm_id}:{rule_id}:{event_date.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def is_duplicate(key: str, redis_client: redis_lib.Redis) -> bool:
    """
    Atomically check if key exists and set it if not (SET NX).
    Returns True if this is a duplicate (key already existed).
    Returns False if this is a new payout (key was set successfully).
    """
    was_set = redis_client.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
    return was_set is None   # None = key already existed = duplicate


def get_redis_client() -> redis_lib.Redis:
    return redis_lib.from_url(settings.redis_url, decode_responses=True)
