"""Tests for prompt_benchmark.client: transport mocking, retries, failure metadata.

No test in this file performs real network I/O. `FakeTransport` stands
in for `Transport` and either returns a scripted `TransportResponse` or
raises a scripted transport exception.
"""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark.client import (
    FailureCategory,
    OpenRouterClient,
    TransportConnectionError,
    TransportResponse,
    TransportTimeout,
)
from prompt_benchmark.config import BenchmarkConfig


def _config(**overrides) -> BenchmarkConfig:
    base = dict(
        api_key="test-secret-key",
        model="openrouter/free",
        base_url="https://openrouter.ai/api/v1",
        timeout_s=5.0,
        max_retries=2,
        retry_base_delay_s=0.01,
        retry_max_delay_s=0.02,
    )
    base.update(overrides)
    return BenchmarkConfig(**base)


class FakeTransport:
    """Scripted transport: returns/raises each entry in `script` in order."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls: list[dict] = []

    def post(self, url, data, headers, timeout):
        self.calls.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _no_sleep(_seconds: float) -> None:
    return None


def _success_body(**overrides) -> TransportResponse:
    body = {
        "id": "gen-123",
        "model": "some-free-model/v1",
        "choices": [{"message": {"content": '{"invoice_id": "A"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    body.update(overrides)
    return TransportResponse(status_code=200, body=json.dumps(body))


class MissingApiKeyTests(unittest.TestCase):
    def test_missing_api_key_fails_without_network_call(self) -> None:
        transport = FakeTransport([])
        client = OpenRouterClient(_config(api_key=None), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.MISSING_API_KEY.value)
        self.assertEqual(transport.calls, [])


class SuccessPathTests(unittest.TestCase):
    def test_successful_completion_captures_metadata(self) -> None:
        transport = FakeTransport([_success_body()])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("extract this", system="be precise")

        self.assertTrue(result.success)
        self.assertEqual(result.text, '{"invoice_id": "A"}')
        self.assertEqual(result.requested_model, "openrouter/free")
        self.assertEqual(result.actual_model, "some-free-model/v1")
        self.assertEqual(result.prompt_tokens, 10)
        self.assertEqual(result.completion_tokens, 5)
        self.assertEqual(result.total_tokens, 15)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.retries, 0)
        self.assertIsNone(result.failure_category)

    def test_api_key_never_appears_in_result(self) -> None:
        transport = FakeTransport([_success_body()])
        client = OpenRouterClient(_config(api_key="super-secret-value"), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        dumped = json.dumps(result.__dict__)
        self.assertNotIn("super-secret-value", dumped)

    def test_missing_usage_metadata_is_none_not_zero(self) -> None:
        body = {
            "id": "gen-1",
            "model": "m",
            "choices": [{"message": {"content": "{}"}}],
        }
        transport = FakeTransport([TransportResponse(200, json.dumps(body))])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertTrue(result.success)
        self.assertIsNone(result.prompt_tokens)
        self.assertIsNone(result.total_tokens)
        self.assertIsNone(result.provider_cost)

    def test_missing_actual_model_is_none(self) -> None:
        body = {"id": "gen-1", "choices": [{"message": {"content": "{}"}}]}
        transport = FakeTransport([TransportResponse(200, json.dumps(body))])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertTrue(result.success)
        self.assertIsNone(result.actual_model)

    def test_provider_cost_captured_when_present(self) -> None:
        transport = FakeTransport([_success_body(usage={"cost": 0.0003})])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertEqual(result.provider_cost, 0.0003)


class FailureClassificationTests(unittest.TestCase):
    def test_empty_choices_is_classified(self) -> None:
        body = {"id": "g1", "model": "m", "choices": []}
        transport = FakeTransport([TransportResponse(200, json.dumps(body))])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.EMPTY_CHOICES.value)

    def test_non_textual_content_is_classified(self) -> None:
        body = {"id": "g1", "model": "m", "choices": [{"message": {"content": None}}]}
        transport = FakeTransport([TransportResponse(200, json.dumps(body))])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.UNSUPPORTED_CONTENT.value)

    def test_provider_error_object_is_classified(self) -> None:
        body = {"id": "g1", "model": "m", "error": {"message": "model unavailable"}}
        transport = FakeTransport([TransportResponse(200, json.dumps(body))])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.PROVIDER_ERROR.value)

    def test_malformed_response_body_is_classified(self) -> None:
        transport = FakeTransport([TransportResponse(200, "not json")])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.MALFORMED_RESPONSE.value)

    def test_permanent_client_error_is_not_retried(self) -> None:
        transport = FakeTransport([TransportResponse(401, '{"error": "unauthorized"}')])
        client = OpenRouterClient(_config(max_retries=3), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.HTTP_CLIENT_ERROR.value)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(transport.calls), 1)


class RetryBehaviorTests(unittest.TestCase):
    def test_timeout_is_retried_then_succeeds(self) -> None:
        transport = FakeTransport([TransportTimeout("slow"), _success_body()])
        client = OpenRouterClient(
            _config(max_retries=2), transport=transport, sleep=_no_sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")
        self.assertTrue(result.success)
        self.assertEqual(result.retries, 1)
        self.assertEqual(result.attempts, 2)

    def test_connection_error_is_retried_then_fails_after_budget(self) -> None:
        transport = FakeTransport(
            [TransportConnectionError("x"), TransportConnectionError("x"), TransportConnectionError("x")]
        )
        client = OpenRouterClient(
            _config(max_retries=2), transport=transport, sleep=_no_sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.CONNECTION_ERROR.value)
        self.assertEqual(result.retries, 2)
        self.assertEqual(result.attempts, 3)

    def test_rate_limit_retried_bounded_by_max_retries(self) -> None:
        transport = FakeTransport(
            [
                TransportResponse(429, "rate limited", headers={"Retry-After": "0"}),
                TransportResponse(429, "rate limited", headers={"Retry-After": "0"}),
                TransportResponse(429, "rate limited", headers={"Retry-After": "0"}),
            ]
        )
        client = OpenRouterClient(
            _config(max_retries=2), transport=transport, sleep=_no_sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.failure_category, FailureCategory.RATE_LIMITED.value)
        self.assertEqual(len(transport.calls), 3)

    def test_server_error_retried_then_recovers(self) -> None:
        transport = FakeTransport([TransportResponse(503, "unavailable"), _success_body()])
        client = OpenRouterClient(
            _config(max_retries=2), transport=transport, sleep=_no_sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")
        self.assertTrue(result.success)
        self.assertEqual(result.retries, 1)

    def test_zero_max_retries_fails_immediately(self) -> None:
        transport = FakeTransport([TransportTimeout("slow")])
        client = OpenRouterClient(_config(max_retries=0), transport=transport, sleep=_no_sleep)
        result = client.complete("prompt")
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.retries, 0)


class RetryAfterEdgeCaseTests(unittest.TestCase):
    """Retry-After is attacker/server-controlled input: it must never be
    able to crash the client. `_no_sleep` in other tests is a no-op that
    ignores its argument, so it cannot catch a bad duration being computed
    here -- these tests use a recording spy that asserts on the duration
    actually passed, the way the real `time.sleep` would receive it.
    """

    def _recording_sleep(self):
        calls: list[float] = []

        def _sleep(seconds: float) -> None:
            self.assertGreaterEqual(seconds, 0, "sleep duration must never be negative")
            self.assertFalse(
                seconds != seconds, "sleep duration must never be NaN"  # NaN != NaN
            )
            calls.append(seconds)

        return _sleep, calls

    def test_retry_after_negative_value_does_not_crash(self) -> None:
        sleep, calls = self._recording_sleep()
        transport = FakeTransport(
            [
                TransportResponse(429, "rate limited", headers={"Retry-After": "-5"}),
                _success_body(),
            ]
        )
        client = OpenRouterClient(
            _config(max_retries=1), transport=transport, sleep=sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")  # must not raise
        self.assertTrue(result.success)
        self.assertEqual(len(calls), 1)

    def test_retry_after_nan_value_does_not_crash(self) -> None:
        sleep, calls = self._recording_sleep()
        transport = FakeTransport(
            [
                TransportResponse(429, "rate limited", headers={"Retry-After": "nan"}),
                _success_body(),
            ]
        )
        client = OpenRouterClient(
            _config(max_retries=1), transport=transport, sleep=sleep, rng=random.Random(1)
        )
        result = client.complete("prompt")  # must not raise
        self.assertTrue(result.success)
        self.assertEqual(len(calls), 1)

    def test_retry_after_malformed_text_falls_back_to_backoff(self) -> None:
        client = OpenRouterClient(_config(), transport=FakeTransport([]), sleep=_no_sleep)
        self.assertIsNone(client._retry_after({"Retry-After": "not-a-number"}))

    def test_retry_after_missing_header_returns_none(self) -> None:
        client = OpenRouterClient(_config(), transport=FakeTransport([]), sleep=_no_sleep)
        self.assertIsNone(client._retry_after({}))

    def test_retry_after_zero_is_a_legitimate_immediate_retry(self) -> None:
        client = OpenRouterClient(_config(), transport=FakeTransport([]), sleep=_no_sleep)
        self.assertEqual(client._retry_after({"Retry-After": "0"}), 0.0)

    def test_retry_after_excessively_large_value_is_capped_by_max_delay(self) -> None:
        sleep, calls = self._recording_sleep()
        transport = FakeTransport(
            [
                TransportResponse(429, "rate limited", headers={"Retry-After": "999999999"}),
                _success_body(),
            ]
        )
        client = OpenRouterClient(
            _config(max_retries=1, retry_max_delay_s=0.02),
            transport=transport, sleep=sleep, rng=random.Random(1),
        )
        result = client.complete("prompt")
        self.assertTrue(result.success)
        self.assertLessEqual(calls[0], 0.02 * 1.25)  # capped delay plus up to 25% jitter


if __name__ == "__main__":
    unittest.main()
