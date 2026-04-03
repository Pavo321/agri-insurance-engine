from datetime import date
from unittest.mock import MagicMock

import pytest

from payout.deduplication import generate_idempotency_key, is_duplicate


class TestIdempotencyKey:
    def test_same_inputs_produce_same_key(self):
        key1 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        key2 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        assert key1 == key2

    def test_different_date_produces_different_key(self):
        key1 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        key2 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 4))
        assert key1 != key2

    def test_different_rule_produces_different_key(self):
        key1 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        key2 = generate_idempotency_key("farm-abc", "DROUGHT_NDVI_30", date(2026, 4, 3))
        assert key1 != key2

    def test_different_farm_produces_different_key(self):
        key1 = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        key2 = generate_idempotency_key("farm-xyz", "FLOOD_RAIN_48H", date(2026, 4, 3))
        assert key1 != key2

    def test_key_is_64_hex_chars(self):
        key = generate_idempotency_key("farm-abc", "FLOOD_RAIN_48H", date(2026, 4, 3))
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestDeduplication:
    def test_first_call_returns_false(self):
        """First call: key does not exist → SET succeeds → not duplicate."""
        redis_mock = MagicMock()
        redis_mock.set.return_value = True   # SET NX succeeded
        assert is_duplicate("newkey", redis_mock) is False

    def test_second_call_returns_true(self):
        """Second call: key already exists → SET NX fails → duplicate."""
        redis_mock = MagicMock()
        redis_mock.set.return_value = None   # SET NX returned None = key existed
        assert is_duplicate("existingkey", redis_mock) is True

    def test_redis_set_called_with_nx_and_ttl(self):
        """Verify Redis is called with atomic NX flag and correct TTL."""
        redis_mock = MagicMock()
        redis_mock.set.return_value = True
        is_duplicate("testkey", redis_mock)
        redis_mock.set.assert_called_once_with(
            "testkey", "1", nx=True, ex=90 * 24 * 60 * 60
        )
