"""Deterministic, provider-independent evaluation of extraction outputs.

This module never calls a model. Scoring a response is a pure function
of its text and the expected record, so results are fully reproducible.

Two correctness metrics are always computed and kept separate:

- `strict_match` compares the raw extracted string to the expected
  string exactly. This is the primary, contract-enforcing metric.
- `semantic_match` is a secondary metric that normalizes superficial
  formatting differences (currency symbols, grouping separators, case,
  whitespace) before comparing. It is never used to upgrade a failing
  strict result into a passing one in the primary metric; both are
  always reported together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

FIELDS: tuple[str, ...] = ("invoice_id", "vendor", "date", "total", "currency")


class ParseOutcome(str, Enum):
    VALID_JSON_OBJECT = "valid_json_object"
    EMPTY_RESPONSE = "empty_response"
    INVALID_JSON = "invalid_json"
    NON_JSON_RESPONSE = "non_json_response"  # parsed, but not an object (e.g. a list or string)
    UNSUPPORTED_SHAPE = "unsupported_shape"  # no text was available to parse at all


def parse_response(text: str | None) -> tuple[ParseOutcome, Any]:
    """Parse raw model text into a JSON value, classifying the outcome.

    Returns (outcome, parsed_value). `parsed_value` is a dict only when
    outcome is VALID_JSON_OBJECT; otherwise it is None.
    """

    import json

    if text is None:
        return ParseOutcome.UNSUPPORTED_SHAPE, None

    stripped = text.strip()
    if not stripped:
        return ParseOutcome.EMPTY_RESPONSE, None

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return ParseOutcome.INVALID_JSON, None

    if isinstance(value, dict):
        return ParseOutcome.VALID_JSON_OBJECT, value

    return ParseOutcome.NON_JSON_RESPONSE, None


@dataclass
class ContractReport:
    missing_keys: list[str]
    unexpected_keys: list[str]
    type_violations: dict[str, str]
    invalid_date_fields: list[str]
    invalid_currency_fields: list[str]
    invalid_total_fields: list[str]

    @property
    def contract_valid(self) -> bool:
        return not (
            self.missing_keys
            or self.unexpected_keys
            or self.type_violations
            or self.invalid_date_fields
            or self.invalid_currency_fields
            or self.invalid_total_fields
        )


def _is_valid_date_string(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10


def _is_valid_currency_code(value: str) -> bool:
    return len(value) == 3 and value.isalpha() and value.isupper()


def _is_valid_total_string(value: str) -> bool:
    if not value:
        return False
    if any(ch in value for ch in ",$€£¥ "):
        return False
    if value.count(".") > 1:
        return False
    digits_and_dot = value.replace(".", "", 1)
    return digits_and_dot.isdigit()


def evaluate_contract(parsed: dict[str, Any]) -> ContractReport:
    """Check key completeness and per-field type/format compliance.

    A non-string value is reported only as a type violation. Format
    checks (date/currency/total) run only on fields that are present
    and already strings, so a type violation is never double-counted
    as a format violation.
    """

    missing_keys = sorted(set(FIELDS) - set(parsed))
    unexpected_keys = sorted(set(parsed) - set(FIELDS))

    type_violations: dict[str, str] = {}
    invalid_date_fields: list[str] = []
    invalid_currency_fields: list[str] = []
    invalid_total_fields: list[str] = []

    for f in FIELDS:
        if f not in parsed:
            continue
        value = parsed[f]
        if value is not None and not isinstance(value, str):
            type_violations[f] = type(value).__name__
            continue
        if value is None:
            continue
        if f == "date" and not _is_valid_date_string(value):
            invalid_date_fields.append(f)
        if f == "currency" and not _is_valid_currency_code(value):
            invalid_currency_fields.append(f)
        if f == "total" and not _is_valid_total_string(value):
            invalid_total_fields.append(f)

    return ContractReport(
        missing_keys=missing_keys,
        unexpected_keys=unexpected_keys,
        type_violations=type_violations,
        invalid_date_fields=invalid_date_fields,
        invalid_currency_fields=invalid_currency_fields,
        invalid_total_fields=invalid_total_fields,
    )


def _normalize_total(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    for symbol in ("$", "€", "£", "¥", ",", " "):
        cleaned = cleaned.replace(symbol, "")
    try:
        as_float = float(cleaned)
    except ValueError:
        return cleaned or None
    return format(as_float, ".2f")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.strip().lower().split())


def _semantic_equal(field_name: str, predicted: Any, expected: Any) -> bool:
    if predicted is None and expected is None:
        return True
    if not isinstance(predicted, str) or not isinstance(expected, str):
        return False
    if field_name == "total":
        return _normalize_total(predicted) == _normalize_total(expected)
    if field_name in ("vendor", "invoice_id"):
        return _normalize_text(predicted) == _normalize_text(expected)
    return predicted == expected


@dataclass
class FieldOutcome:
    strict_match: bool
    semantic_match: bool
    hallucinated: bool           # expected null, predicted non-null
    missing: bool                # expected non-null, predicted null
    decoy_selected: bool | None  # None when the case has no labeled decoy for this field


@dataclass
class RecordEvaluation:
    parse_outcome: ParseOutcome
    parsed: dict[str, Any] | None
    contract: ContractReport | None
    field_outcomes: dict[str, FieldOutcome]
    exact_match: bool            # strict, all fields match AND the contract is valid
    semantic_exact_match: bool   # secondary, normalized match across all fields
    field_accuracy: float        # strict field-match ratio across FIELDS


def evaluate_record(
    text: str | None,
    expected: dict[str, Any],
    decoys: dict[str, tuple[str, ...]] | None = None,
) -> RecordEvaluation:
    """Score one model response against one expected record.

    A response that fails to parse as a JSON object scores every field
    as incorrect; it is never silently excluded or coerced into a pass.
    """

    decoys = decoys or {}
    outcome, parsed = parse_response(text)

    if outcome is not ParseOutcome.VALID_JSON_OBJECT or parsed is None:
        empty_outcomes = {
            f: FieldOutcome(
                strict_match=False,
                semantic_match=False,
                hallucinated=False,
                missing=expected.get(f) is not None,
                decoy_selected=False if f in decoys else None,
            )
            for f in FIELDS
        }
        return RecordEvaluation(
            parse_outcome=outcome,
            parsed=None,
            contract=None,
            field_outcomes=empty_outcomes,
            exact_match=False,
            semantic_exact_match=False,
            field_accuracy=0.0,
        )

    contract = evaluate_contract(parsed)

    field_outcomes: dict[str, FieldOutcome] = {}
    for f in FIELDS:
        predicted = parsed.get(f)
        exp = expected.get(f)

        strict_match = (
            f in parsed
            and predicted == exp
            and (predicted is None or isinstance(predicted, str))
        )
        semantic_match = _semantic_equal(f, predicted, exp)
        hallucinated = exp is None and predicted is not None
        missing = exp is not None and predicted is None

        decoy_selected: bool | None = None
        field_decoys = decoys.get(f)
        if field_decoys:
            decoy_selected = isinstance(predicted, str) and predicted.strip() in field_decoys

        field_outcomes[f] = FieldOutcome(
            strict_match=strict_match,
            semantic_match=semantic_match,
            hallucinated=hallucinated,
            missing=missing,
            decoy_selected=decoy_selected,
        )

    strict_all = all(o.strict_match for o in field_outcomes.values())
    semantic_all = all(o.semantic_match for o in field_outcomes.values())
    field_accuracy = sum(o.strict_match for o in field_outcomes.values()) / len(FIELDS)

    return RecordEvaluation(
        parse_outcome=outcome,
        parsed=parsed,
        contract=contract,
        field_outcomes=field_outcomes,
        exact_match=strict_all and contract.contract_valid,
        semantic_exact_match=semantic_all,
        field_accuracy=field_accuracy,
    )
