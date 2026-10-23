"""Runtime configuration for the prompt-optimization benchmark.

Centralizes environment-variable parsing and validation so the client,
runner, and CLI share one source of truth for model routing, timeouts,
and retry behavior. `BenchmarkConfig.api_key` is never printed, logged,
or included in any serialized artifact produced by this package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "openrouter/free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY_S = 1.0
DEFAULT_RETRY_MAX_DELAY_S = 20.0
DEFAULT_CONCURRENCY = 1
DEFAULT_TEMPERATURE = 0.0


@dataclass(frozen=True)
class BenchmarkConfig:
    """Resolved configuration for one benchmark invocation."""

    api_key: str | None
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_base_delay_s: float = DEFAULT_RETRY_BASE_DELAY_S
    retry_max_delay_s: float = DEFAULT_RETRY_MAX_DELAY_S
    concurrency: int = DEFAULT_CONCURRENCY
    temperature: float = DEFAULT_TEMPERATURE
    request_limit: int | None = None

    def __repr__(self) -> str:  # pragma: no cover - defensive redaction
        return (
            "BenchmarkConfig(api_key="
            f"{'<set>' if self.api_key else None}, model={self.model!r}, "
            f"base_url={self.base_url!r}, timeout_s={self.timeout_s}, "
            f"max_retries={self.max_retries}, concurrency={self.concurrency}, "
            f"temperature={self.temperature}, request_limit={self.request_limit})"
        )


def load_config_from_env(env: dict[str, str] | None = None) -> BenchmarkConfig:
    """Build a BenchmarkConfig from environment variables.

    `env` may be injected for tests; defaults to `os.environ`.
    """

    source = env if env is not None else os.environ

    def _float(name: str, default: float) -> float:
        raw = source.get(name)
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def _int(name: str, default: int) -> int:
        raw = source.get(name)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    request_limit_raw = source.get("BENCHMARK_CASE_LIMIT", "")
    request_limit = (
        int(request_limit_raw)
        if request_limit_raw.isdigit() and int(request_limit_raw) > 0
        else None
    )

    return BenchmarkConfig(
        api_key=source.get("OPENROUTER_API_KEY") or None,
        model=source.get("OPENROUTER_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL,
        base_url=(source.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/"),
        timeout_s=_float("OPENROUTER_TIMEOUT_S", DEFAULT_TIMEOUT_S),
        max_retries=_int("OPENROUTER_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        retry_base_delay_s=_float("OPENROUTER_RETRY_BASE_DELAY_S", DEFAULT_RETRY_BASE_DELAY_S),
        retry_max_delay_s=_float("OPENROUTER_RETRY_MAX_DELAY_S", DEFAULT_RETRY_MAX_DELAY_S),
        concurrency=_int("BENCHMARK_CONCURRENCY", DEFAULT_CONCURRENCY),
        temperature=_float("BENCHMARK_TEMPERATURE", DEFAULT_TEMPERATURE),
        request_limit=request_limit,
    )


def validate_config(config: BenchmarkConfig, *, require_api_key: bool = True) -> list[str]:
    """Return human-readable configuration problems.

    An empty list means the configuration is usable. Call this before
    spending API requests.
    """

    problems: list[str] = []

    if require_api_key and not config.api_key:
        problems.append("OPENROUTER_API_KEY is not set.")

    if not config.model:
        problems.append("Model is empty; set OPENROUTER_MODEL or use the default.")

    if not config.base_url.startswith(("http://", "https://")):
        problems.append(f"Base URL does not look like a URL: {config.base_url!r}")

    if config.timeout_s <= 0:
        problems.append("Timeout must be positive.")

    if config.max_retries < 0:
        problems.append("max_retries cannot be negative.")

    if config.retry_base_delay_s < 0 or config.retry_max_delay_s < 0:
        problems.append("Retry delays cannot be negative.")

    if config.retry_max_delay_s < config.retry_base_delay_s:
        problems.append("retry_max_delay_s must be >= retry_base_delay_s.")

    if config.concurrency < 1:
        problems.append("concurrency must be at least 1.")

    if not (0.0 <= config.temperature <= 2.0):
        problems.append("temperature should be within [0, 2].")

    if config.request_limit is not None and config.request_limit < 1:
        problems.append("request_limit must be a positive integer when set.")

    return problems
