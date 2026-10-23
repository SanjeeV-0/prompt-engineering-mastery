"""Shared record and manifest schemas for benchmark runs.

`SCHEMA_VERSION` must be bumped whenever a field is added, removed, or
reinterpreted, so a saved run can be matched to code that can analyze
it correctly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"

# Deliberately does not include "token": prompt_tokens/completion_tokens/
# total_tokens are legitimate usage counters, not secrets.
_SECRET_KEY_MARKERS = ("api_key", "apikey", "authorization", "secret", "password", "bearer")


def redact(value: Any) -> Any:
    """Recursively strip values under suspicious keys from dicts/lists."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, val in value.items():
            if isinstance(key, str) and any(marker in key.lower() for marker in _SECRET_KEY_MARKERS):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact(val)
        return redacted
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RequestRecord:
    schema_version: str
    experiment_id: str
    run_id: str
    timestamp_utc: str
    dataset_version: str
    case_id: str
    split: str
    variant_name: str
    variant_version: str
    prompt_hash: str
    requested_model: str
    actual_model: str | None
    temperature: float
    attempts: int
    retries: int
    success: bool
    failure_category: str | None
    error_message: str | None
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    provider_cost: float | None
    request_id: str | None
    raw_response_text: str | None
    parse_outcome: str
    contract_valid: bool | None
    missing_keys: list[str]
    unexpected_keys: list[str]
    type_violations: dict[str, str]
    invalid_date_fields: list[str]
    invalid_currency_fields: list[str]
    invalid_total_fields: list[str]
    expected: dict[str, Any]
    parsed: dict[str, Any] | None
    field_matches_strict: dict[str, bool]
    field_matches_semantic: dict[str, bool]
    exact_match: bool
    semantic_exact_match: bool
    field_accuracy: float
    decoy_selected: dict[str, bool]

    def to_json_dict(self) -> dict[str, Any]:
        return redact(asdict(self))


@dataclass
class Constraints:
    min_quality: float | None = None  # minimum acceptable exact_match_rate
    max_cost_per_request: float | None = None
    max_p95_latency_ms: float | None = None
    min_pairs_for_decision: int = 10
    max_model_distribution_tvd: float = 0.35


@dataclass
class RunManifest:
    experiment_id: str
    run_id: str
    created_utc: str
    research_question: str
    hypothesis: str
    primary_metric: str
    secondary_metrics: list[str]
    baseline_variant: str
    candidate_variant: str
    dataset_version: str
    dataset_split: str
    requested_model: str
    base_url: str
    temperature: float
    trial_count: int
    constraints: Constraints
    limitations: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        return redact(asdict(self))
