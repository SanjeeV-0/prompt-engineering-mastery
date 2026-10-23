"""Executes a benchmark run: dataset -> client -> evaluation -> records."""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from . import prompts as prompts_module
from .client import OpenRouterClient
from .config import BenchmarkConfig
from .dataset import Case
from .evaluation import evaluate_record
from .prompts import PromptVariant
from .schema import SCHEMA_VERSION, RequestRecord, utc_now_iso


@dataclass
class RunPlanItem:
    case: Case
    variant: PromptVariant


def build_plan(
    cases: list[Case],
    variants: list[PromptVariant],
    *,
    seed: int,
    shuffle: bool = True,
) -> list[RunPlanItem]:
    """Interleave cases and variants with a balanced, seeded request order.

    Balancing request order (rather than running one variant fully
    before the other) reduces systematic drift from free-router model
    availability changing over the course of a run, but it does not
    guarantee an identical model mix per variant -- see
    `analysis.compare_model_distributions`.
    """

    plan = [RunPlanItem(case=c, variant=v) for v in variants for c in cases]
    if shuffle:
        random.Random(seed).shuffle(plan)
    return plan


def execute_plan(
    plan: list[RunPlanItem],
    client: OpenRouterClient,
    config: BenchmarkConfig,
    *,
    experiment_id: str,
    run_id: str,
    dataset_version: str,
    on_record: Callable[[RequestRecord], None] | None = None,
    limit: int | None = None,
    max_workers: int = 1,
) -> list[RequestRecord]:
    """Run each (case, variant) pair through the client and evaluator.

    `limit` caps the number of planned requests: `None` runs the whole
    plan; a positive integer takes the first `limit` items. A
    non-positive `limit` (zero or negative) deliberately resolves to no
    requests at all, rather than relying on Python's slice semantics --
    `plan[:0]` is unambiguous, but `plan[:-1]` silently returns "every
    item except the last one," which is not a sensible reading of a
    request cap and was previously reachable here.
    """

    if limit is None:
        items = plan
    elif limit <= 0:
        items = []
    else:
        items = plan[:limit]

    def _process(item: RunPlanItem) -> RequestRecord:
        prompt_text = item.variant.render(item.case.document)
        result = client.complete(prompt_text, system=prompts_module.SYSTEM_MESSAGE)
        evaluation = evaluate_record(result.text, item.case.expected, item.case.decoys)

        return RequestRecord(
            schema_version=SCHEMA_VERSION,
            experiment_id=experiment_id,
            run_id=run_id,
            timestamp_utc=utc_now_iso(),
            dataset_version=dataset_version,
            case_id=item.case.case_id,
            split=item.case.split,
            variant_name=item.variant.name,
            variant_version=item.variant.version,
            prompt_hash=item.variant.prompt_hash,
            requested_model=result.requested_model,
            actual_model=result.actual_model,
            temperature=config.temperature,
            attempts=result.attempts,
            retries=result.retries,
            success=result.success,
            failure_category=result.failure_category,
            error_message=result.error_message,
            latency_ms=result.latency_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            provider_cost=result.provider_cost,
            request_id=result.request_id,
            raw_response_text=result.text,
            parse_outcome=evaluation.parse_outcome.value,
            contract_valid=(evaluation.contract.contract_valid if evaluation.contract else None),
            missing_keys=(evaluation.contract.missing_keys if evaluation.contract else []),
            unexpected_keys=(evaluation.contract.unexpected_keys if evaluation.contract else []),
            type_violations=(evaluation.contract.type_violations if evaluation.contract else {}),
            invalid_date_fields=(
                evaluation.contract.invalid_date_fields if evaluation.contract else []
            ),
            invalid_currency_fields=(
                evaluation.contract.invalid_currency_fields if evaluation.contract else []
            ),
            invalid_total_fields=(
                evaluation.contract.invalid_total_fields if evaluation.contract else []
            ),
            expected=dict(item.case.expected),
            parsed=evaluation.parsed,
            field_matches_strict={f: o.strict_match for f, o in evaluation.field_outcomes.items()},
            field_matches_semantic={f: o.semantic_match for f, o in evaluation.field_outcomes.items()},
            exact_match=evaluation.exact_match,
            semantic_exact_match=evaluation.semantic_exact_match,
            field_accuracy=evaluation.field_accuracy,
            decoy_selected={
                f: bool(o.decoy_selected)
                for f, o in evaluation.field_outcomes.items()
                if o.decoy_selected is not None
            },
        )

    records: list[RequestRecord] = []
    if max_workers <= 1:
        for item in items:
            record = _process(item)
            records.append(record)
            if on_record:
                on_record(record)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for record in executor.map(_process, items):
                records.append(record)
                if on_record:
                    on_record(record)

    return records
