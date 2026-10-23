"""A minimal, testable OpenRouter chat-completions client.

Network access goes through a small `Transport` protocol so tests can
inject a fake transport instead of hitting the real API. The default
transport uses `urllib` only (standard library). The client never
falls back to a different model or endpoint than requested, and it
never raises on a provider or transport failure: every call returns a
`ClientResult` with enough metadata to audit what happened.
"""

from __future__ import annotations

import json
import math
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .config import BenchmarkConfig


class FailureCategory(str, Enum):
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_CLIENT_ERROR = "http_client_error"
    HTTP_SERVER_ERROR = "http_server_error"
    RATE_LIMITED = "rate_limited"
    EMPTY_CHOICES = "empty_choices"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    UNSUPPORTED_CONTENT = "unsupported_content"
    MISSING_API_KEY = "missing_api_key"


@dataclass
class TransportResponse:
    status_code: int
    body: str
    headers: dict[str, str] = field(default_factory=dict)


class TransportTimeout(Exception):
    """Raised by a Transport implementation on a request timeout."""


class TransportConnectionError(Exception):
    """Raised by a Transport implementation on a connection failure."""


class Transport(Protocol):
    def post(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> TransportResponse: ...


class UrllibTransport:
    """Default transport: standard-library `urllib` only."""

    def post(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> TransportResponse:
        request = urllib.request.Request(url=url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return TransportResponse(
                    status_code=response.getcode(),
                    body=body,
                    headers={k: v for k, v in response.headers.items()},
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return TransportResponse(
                status_code=exc.code,
                body=body,
                headers={k: v for k, v in (exc.headers or {}).items()},
            )
        except TimeoutError as exc:
            raise TransportTimeout(str(exc)) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TransportTimeout(str(exc)) from exc
            raise TransportConnectionError(str(exc)) from exc


@dataclass
class ClientResult:
    success: bool
    text: str | None
    requested_model: str
    actual_model: str | None
    latency_ms: float
    attempts: int
    retries: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    provider_cost: float | None
    request_id: str | None
    failure_category: str | None
    error_message: str | None
    raw_response: dict[str, Any] | None


def _redact_message(message: str, api_key: str | None) -> str:
    if api_key and api_key in message:
        message = message.replace(api_key, "<redacted>")
    return message


class OpenRouterClient:
    """Chat-completions client with bounded retries and rich result metadata."""

    def __init__(
        self,
        config: BenchmarkConfig,
        transport: Transport | None = None,
        sleep: Any = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or UrllibTransport()
        self._sleep = sleep
        self._rng = rng or random.Random()

    def complete(self, prompt: str, system: str | None = None) -> ClientResult:
        config = self._config

        if not config.api_key:
            return ClientResult(
                success=False,
                text=None,
                requested_model=config.model,
                actual_model=None,
                latency_ms=0.0,
                attempts=0,
                retries=0,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                provider_cost=None,
                request_id=None,
                failure_category=FailureCategory.MISSING_API_KEY.value,
                error_message="OPENROUTER_API_KEY is not set.",
                raw_response=None,
            )

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": config.model, "messages": messages, "temperature": config.temperature}
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{config.base_url}/chat/completions"

        attempts = 0
        retries = 0
        started = time.perf_counter()

        while True:
            attempts += 1
            try:
                response = self._transport.post(url, body_bytes, headers, config.timeout_s)
            except TransportTimeout as exc:
                if retries < config.max_retries:
                    retries += 1
                    self._backoff(retries)
                    continue
                return self._failure(FailureCategory.TIMEOUT, str(exc), started, attempts, retries)
            except TransportConnectionError as exc:
                if retries < config.max_retries:
                    retries += 1
                    self._backoff(retries)
                    continue
                return self._failure(
                    FailureCategory.CONNECTION_ERROR, str(exc), started, attempts, retries
                )

            if response.status_code == 429:
                if retries < config.max_retries:
                    retries += 1
                    self._backoff(retries, retry_after=self._retry_after(response.headers))
                    continue
                return self._failure(
                    FailureCategory.RATE_LIMITED,
                    f"HTTP 429: {response.body[:500]}",
                    started, attempts, retries,
                )

            if response.status_code >= 500:
                if retries < config.max_retries:
                    retries += 1
                    self._backoff(retries, retry_after=self._retry_after(response.headers))
                    continue
                return self._failure(
                    FailureCategory.HTTP_SERVER_ERROR,
                    f"HTTP {response.status_code}: {response.body[:500]}",
                    started, attempts, retries,
                )

            if response.status_code >= 400:
                # Permanent client errors (400/401/403/404/...) are not retried.
                return self._failure(
                    FailureCategory.HTTP_CLIENT_ERROR,
                    f"HTTP {response.status_code}: {response.body[:500]}",
                    started, attempts, retries,
                )

            return self._parse_success(response, started, attempts, retries)

    def _retry_after(self, headers: dict[str, str]) -> float | None:
        """Parse a Retry-After header value, rejecting anything unusable.

        A server (or an attacker on the wire) can send any string here.
        Negative, NaN, or non-numeric values are treated the same as a
        missing header -- fall back to exponential backoff -- rather
        than being passed through to `time.sleep`, which raises
        `ValueError` on a negative or NaN duration and would otherwise
        crash the whole run.
        """
        for key, value in headers.items():
            if key.lower() == "retry-after":
                try:
                    parsed = float(value)
                except ValueError:
                    return None
                if not math.isfinite(parsed) or parsed < 0:
                    return None
                return parsed
        return None

    def _backoff(self, retry_number: int, retry_after: float | None = None) -> None:
        if retry_after is not None:
            delay = min(retry_after, self._config.retry_max_delay_s)
        else:
            base = self._config.retry_base_delay_s * (2 ** (retry_number - 1))
            delay = min(base, self._config.retry_max_delay_s)
        jitter = self._rng.uniform(0, delay * 0.25)
        self._sleep(delay + jitter)

    def _failure(
        self,
        category: FailureCategory,
        message: str,
        started: float,
        attempts: int,
        retries: int,
        actual_model: str | None = None,
        request_id: str | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> ClientResult:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ClientResult(
            success=False,
            text=None,
            requested_model=self._config.model,
            actual_model=actual_model,
            latency_ms=latency_ms,
            attempts=attempts,
            retries=retries,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            provider_cost=None,
            request_id=request_id,
            failure_category=category.value,
            error_message=_redact_message(message, self._config.api_key),
            raw_response=raw_response,
        )

    def _parse_success(
        self,
        response: TransportResponse,
        started: float,
        attempts: int,
        retries: int,
    ) -> ClientResult:
        config = self._config
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        try:
            body = json.loads(response.body)
        except json.JSONDecodeError as exc:
            return self._failure(
                FailureCategory.MALFORMED_RESPONSE,
                f"Response body was not valid JSON: {exc}",
                started, attempts, retries,
            )

        if not isinstance(body, dict):
            return self._failure(
                FailureCategory.MALFORMED_RESPONSE,
                "Response body was not a JSON object.",
                started, attempts, retries,
            )

        provider_error = body.get("error")
        if provider_error:
            return self._failure(
                FailureCategory.PROVIDER_ERROR,
                str(provider_error)[:500],
                started, attempts, retries,
                actual_model=body.get("model"),
                request_id=body.get("id"),
                raw_response=body,
            )

        choices = body.get("choices") or []
        if not choices:
            return self._failure(
                FailureCategory.EMPTY_CHOICES,
                "Provider returned no completion choices.",
                started, attempts, retries,
                actual_model=body.get("model"),
                request_id=body.get("id"),
                raw_response=body,
            )

        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")

        if not isinstance(content, str):
            return self._failure(
                FailureCategory.UNSUPPORTED_CONTENT,
                "Message content was not textual.",
                started, attempts, retries,
                actual_model=body.get("model"),
                request_id=body.get("id"),
                raw_response=body,
            )

        usage = body.get("usage") or {}

        return ClientResult(
            success=True,
            text=content,
            requested_model=config.model,
            actual_model=body.get("model"),
            latency_ms=latency_ms,
            attempts=attempts,
            retries=retries,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            provider_cost=usage.get("cost"),
            request_id=body.get("id"),
            failure_category=None,
            error_message=None,
            raw_response=body,
        )
