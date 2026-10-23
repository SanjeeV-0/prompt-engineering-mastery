"""Aggregation, model-distribution analysis, and accept/reject decisions.

All functions here operate on already-collected `RequestRecord`
objects; none of them call a model. Every aggregate reports its
denominator so "insufficient data" is visible rather than hidden
behind a lone number.

Two quality views are always computed and kept separate:

- `quality` uses ALL requests as the denominator, including transport
  failures and unparseable responses, scored as misses. This is the
  end-to-end, operationally honest view.
- `quality_conditional` restricts to requests that completed the task
  (client success, valid JSON object, contract-valid). This isolates
  model output quality from operational reliability, which is reported
  separately in `reliability`.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass

from .evaluation import FIELDS
from .schema import Constraints, RequestRecord

MIN_SAMPLE_FOR_PERCENTILE = 20


def _percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile. Returns None for an empty sample."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(p * len(ordered)) - 1))
    return round(ordered[index], 2)


_REFUSAL_MARKERS = (
    "i cannot assist",
    "i can't assist",
    "i cannot help",
    "i can't help",
    "as an ai language model",
    "i'm sorry, but i can't",
    "i am not able to",
)


def _looks_like_refusal(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


@dataclass
class ReliabilityMetrics:
    total_requests: int
    successful_requests: int
    completed_requests: int  # success AND valid JSON object AND contract_valid
    request_success_rate: float | None
    task_completion_rate: float | None
    schema_validity_rate: float | None  # among successful requests
    refusal_like_rate: float | None
    retry_rate: float
    requests_with_retries: int
    error_category_counts: dict[str, int]
    unknown_actual_model_rate: float


def compute_reliability(records: list[RequestRecord]) -> ReliabilityMetrics:
    total = len(records)
    if total == 0:
        return ReliabilityMetrics(
            total_requests=0,
            successful_requests=0,
            completed_requests=0,
            request_success_rate=None,
            task_completion_rate=None,
            schema_validity_rate=None,
            refusal_like_rate=None,
            retry_rate=0.0,
            requests_with_retries=0,
            error_category_counts={},
            unknown_actual_model_rate=0.0,
        )

    successful = [r for r in records if r.success]
    completed = [r for r in successful if r.parse_outcome == "valid_json_object" and r.contract_valid]
    schema_valid_among_successful = [r for r in successful if r.contract_valid]
    non_completed = [r for r in records if not r.success or r.parse_outcome != "valid_json_object"]
    refusal_like = [r for r in non_completed if _looks_like_refusal(r.raw_response_text)]
    with_retries = [r for r in records if r.retries > 0]
    error_counts = Counter(r.failure_category for r in records if r.failure_category)
    unknown_model = sum(1 for r in records if r.success and not r.actual_model)

    return ReliabilityMetrics(
        total_requests=total,
        successful_requests=len(successful),
        completed_requests=len(completed),
        request_success_rate=round(len(successful) / total, 4),
        task_completion_rate=round(len(completed) / total, 4),
        schema_validity_rate=(
            round(len(schema_valid_among_successful) / len(successful), 4) if successful else None
        ),
        refusal_like_rate=round(len(refusal_like) / total, 4),
        retry_rate=round(len(with_retries) / total, 4),
        requests_with_retries=len(with_retries),
        error_category_counts=dict(error_counts),
        unknown_actual_model_rate=round(unknown_model / len(successful), 4) if successful else 0.0,
    )


@dataclass
class ParsingMetrics:
    counts: dict[str, int]
    rates: dict[str, float]
    sample_size: int


def compute_parsing(records: list[RequestRecord]) -> ParsingMetrics:
    total = len(records)
    counts = Counter(r.parse_outcome for r in records)
    rates = {k: round(v / total, 4) for k, v in counts.items()} if total else {}
    return ParsingMetrics(counts=dict(counts), rates=rates, sample_size=total)


@dataclass
class ContractMetrics:
    sample_size: int  # number of valid JSON objects evaluated
    missing_key_counts: dict[str, int]
    unexpected_key_counts: dict[str, int]
    invalid_date_rate: float | None
    invalid_currency_rate: float | None
    invalid_total_rate: float | None
    contract_validity_rate: float | None


def compute_contract(records: list[RequestRecord]) -> ContractMetrics:
    parsed = [r for r in records if r.parse_outcome == "valid_json_object"]
    n = len(parsed)
    missing: Counter = Counter()
    unexpected: Counter = Counter()
    for r in parsed:
        missing.update(r.missing_keys)
        unexpected.update(r.unexpected_keys)

    def rate(predicate) -> float | None:
        return round(sum(1 for r in parsed if predicate(r)) / n, 4) if n else None

    return ContractMetrics(
        sample_size=n,
        missing_key_counts=dict(missing),
        unexpected_key_counts=dict(unexpected),
        invalid_date_rate=rate(lambda r: bool(r.invalid_date_fields)),
        invalid_currency_rate=rate(lambda r: bool(r.invalid_currency_fields)),
        invalid_total_rate=rate(lambda r: bool(r.invalid_total_fields)),
        contract_validity_rate=rate(lambda r: bool(r.contract_valid)),
    )


@dataclass
class FieldQualityMetrics:
    precision: float | None
    recall: float | None
    f1: float | None
    strict_accuracy: float | None
    semantic_accuracy: float | None
    missing_value_accuracy: float | None       # among expected-null cases
    hallucinated_value_rate: float | None      # among expected-null cases
    unsupported_inference_rate: float | None   # among cases with a labeled decoy for this field
    unsupported_inference_n: int
    n_expected_null: int
    n_expected_value: int


@dataclass
class QualityMetrics:
    sample_size: int
    exact_match_rate: float
    semantic_exact_match_rate: float
    mean_field_accuracy: float
    per_field: dict[str, FieldQualityMetrics]


def _empty_quality_metrics() -> QualityMetrics:
    return QualityMetrics(
        sample_size=0,
        exact_match_rate=0.0,
        semantic_exact_match_rate=0.0,
        mean_field_accuracy=0.0,
        per_field={
            f: FieldQualityMetrics(None, None, None, None, None, None, None, None, 0, 0, 0)
            for f in FIELDS
        },
    )


def compute_quality(records: list[RequestRecord]) -> QualityMetrics:
    """Quality metrics use every supplied record as the denominator.

    Callers decide the subset: pass all records for the end-to-end
    view, or a completed-only subset for the conditional view. A
    request that failed at the transport layer or produced unparseable
    output counts as a miss here, not an exclusion.

    Field-level precision/recall/F1 use the standard slot-filling
    definition: a predicted value that is wrong (including a value
    where none was expected) counts against precision; failing to
    produce the correct value (missing or wrong) counts against
    recall. A wrong value therefore reduces both.
    """

    total = len(records)
    if total == 0:
        return _empty_quality_metrics()

    exact = sum(1 for r in records if r.exact_match)
    semantic_exact = sum(1 for r in records if r.semantic_exact_match)
    mean_field_accuracy = sum(r.field_accuracy for r in records) / total

    per_field: dict[str, FieldQualityMetrics] = {}
    for f in FIELDS:
        tp = fp = fn = 0
        strict_correct = 0
        semantic_correct = 0
        expected_null = 0
        expected_value = 0
        correctly_null = 0
        hallucinated_among_null = 0
        decoy_hits = 0
        decoy_n = 0

        for r in records:
            exp = r.expected.get(f)
            strict_match = r.field_matches_strict.get(f, False)
            semantic_match = r.field_matches_semantic.get(f, False)
            predicted = r.parsed.get(f) if r.parsed else None

            if strict_match:
                strict_correct += 1
            if semantic_match:
                semantic_correct += 1

            if exp is None:
                expected_null += 1
                if predicted is None:
                    correctly_null += 1
                else:
                    hallucinated_among_null += 1
            else:
                expected_value += 1

            if strict_match and exp is not None:
                tp += 1
            elif predicted is not None and not strict_match:
                fp += 1
            if exp is not None and not strict_match:
                fn += 1

            if f in r.decoy_selected:
                decoy_n += 1
                if r.decoy_selected[f]:
                    decoy_hits += 1

        precision = round(tp / (tp + fp), 4) if (tp + fp) else None
        recall = round(tp / (tp + fn), 4) if (tp + fn) else None
        if precision is None or recall is None:
            f1 = None
        elif precision + recall == 0:
            f1 = 0.0  # both defined but zero: conventional F1 = 0, not undefined
        else:
            f1 = round(2 * precision * recall / (precision + recall), 4)

        per_field[f] = FieldQualityMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            strict_accuracy=round(strict_correct / total, 4),
            semantic_accuracy=round(semantic_correct / total, 4),
            missing_value_accuracy=(round(correctly_null / expected_null, 4) if expected_null else None),
            hallucinated_value_rate=(
                round(hallucinated_among_null / expected_null, 4) if expected_null else None
            ),
            unsupported_inference_rate=(round(decoy_hits / decoy_n, 4) if decoy_n else None),
            unsupported_inference_n=decoy_n,
            n_expected_null=expected_null,
            n_expected_value=expected_value,
        )

    return QualityMetrics(
        sample_size=total,
        exact_match_rate=round(exact / total, 4),
        semantic_exact_match_rate=round(semantic_exact / total, 4),
        mean_field_accuracy=round(mean_field_accuracy, 4),
        per_field=per_field,
    )


@dataclass
class CostLatencyMetrics:
    n_requests: int
    n_with_token_usage: int
    n_with_cost: int
    total_prompt_tokens: int | None
    total_completion_tokens: int | None
    total_tokens: int | None
    mean_total_tokens: float | None
    total_provider_cost: float | None
    mean_cost_per_request: float | None
    cost_per_successful_task: float | None
    n_latency_samples: int
    median_latency_ms: float | None
    p95_latency_ms: float | None
    percentile_method: str
    latency_sample_is_small: bool


def compute_cost_latency(records: list[RequestRecord], completed_count: int) -> CostLatencyMetrics:
    n = len(records)
    prompt_tokens = [r.prompt_tokens for r in records if isinstance(r.prompt_tokens, (int, float))]
    completion_tokens = [
        r.completion_tokens for r in records if isinstance(r.completion_tokens, (int, float))
    ]
    total_tokens = [r.total_tokens for r in records if isinstance(r.total_tokens, (int, float))]
    costs = [r.provider_cost for r in records if isinstance(r.provider_cost, (int, float))]
    latencies = [r.latency_ms for r in records if isinstance(r.latency_ms, (int, float)) and r.success]

    total_cost = sum(costs) if costs else None

    return CostLatencyMetrics(
        n_requests=n,
        n_with_token_usage=len(total_tokens),
        n_with_cost=len(costs),
        total_prompt_tokens=sum(prompt_tokens) if prompt_tokens else None,
        total_completion_tokens=sum(completion_tokens) if completion_tokens else None,
        total_tokens=sum(total_tokens) if total_tokens else None,
        mean_total_tokens=round(sum(total_tokens) / len(total_tokens), 2) if total_tokens else None,
        total_provider_cost=total_cost,
        mean_cost_per_request=(round(total_cost / len(costs), 6) if costs else None),
        cost_per_successful_task=(
            round(total_cost / completed_count, 6)
            if total_cost is not None and completed_count
            else None
        ),
        n_latency_samples=len(latencies),
        median_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        percentile_method="nearest-rank, computed over successful requests only",
        latency_sample_is_small=len(latencies) < MIN_SAMPLE_FOR_PERCENTILE,
    )


@dataclass
class VariantSummary:
    variant_name: str
    n_requests: int
    reliability: ReliabilityMetrics
    parsing: ParsingMetrics
    contract: ContractMetrics
    quality: QualityMetrics
    quality_conditional: QualityMetrics
    cost_latency: CostLatencyMetrics
    model_frequencies: dict[str, int]


def summarize_variant(records: list[RequestRecord]) -> VariantSummary:
    reliability = compute_reliability(records)
    quality = compute_quality(records)
    completed_records = [
        r for r in records if r.success and r.parse_outcome == "valid_json_object" and r.contract_valid
    ]
    quality_conditional = compute_quality(completed_records)
    model_counts = Counter(r.actual_model or "unknown" for r in records)

    return VariantSummary(
        variant_name=records[0].variant_name if records else "unknown",
        n_requests=len(records),
        reliability=reliability,
        parsing=compute_parsing(records),
        contract=compute_contract(records),
        quality=quality,
        quality_conditional=quality_conditional,
        cost_latency=compute_cost_latency(records, reliability.completed_requests),
        model_frequencies=dict(model_counts),
    )


def summarize_by_model(records: list[RequestRecord]) -> dict[str, VariantSummary]:
    by_model: dict[str, list[RequestRecord]] = defaultdict(list)
    for r in records:
        by_model[r.actual_model or "unknown"].append(r)
    return {model: summarize_variant(items) for model, items in sorted(by_model.items())}


def _total_variation_distance(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    total_a = sum(a.values()) or 1
    total_b = sum(b.values()) or 1
    return 0.5 * sum(abs(a.get(k, 0) / total_a - b.get(k, 0) / total_b) for k in keys)


@dataclass
class ModelDistributionComparison:
    baseline_frequencies: dict[str, int]
    candidate_frequencies: dict[str, int]
    total_variation_distance: float
    distributions_diverge: bool
    note: str


def compare_model_distributions(
    baseline: list[RequestRecord],
    candidate: list[RequestRecord],
    *,
    tvd_threshold: float = 0.35,
) -> ModelDistributionComparison:
    base_counts = Counter(r.actual_model or "unknown" for r in baseline)
    cand_counts = Counter(r.actual_model or "unknown" for r in candidate)
    tvd = round(_total_variation_distance(base_counts, cand_counts), 4)

    note = (
        "Baseline and candidate requests may have been served by different "
        "underlying free-router models. Any quality difference between "
        "variants is confounded with model selection unless this "
        "distribution is effectively identical."
    )

    return ModelDistributionComparison(
        baseline_frequencies=dict(base_counts),
        candidate_frequencies=dict(cand_counts),
        total_variation_distance=tvd,
        distributions_diverge=tvd > tvd_threshold,
        note=note,
    )


@dataclass
class PairedComparison:
    metric_name: str
    n_pairs: int
    mean_difference: float | None
    ci_low: float | None
    ci_high: float | None
    n_bootstrap: int
    seed: int
    sufficient_for_inference: bool
    note: str


def paired_exact_match_comparison(
    baseline: list[RequestRecord],
    candidate: list[RequestRecord],
    *,
    min_pairs: int = 10,
    n_bootstrap: int = 2000,
    seed: int = 20261023,
) -> PairedComparison:
    """Bootstrap 95% CI on the mean per-case difference in exact_match.

    Only case_ids present in both variants are compared. If a case_id
    appears more than once within a variant (repeated trials), its
    outcomes are averaged before pairing: repeated requests for the
    same case are not independent evidence of generalization.
    """

    def _mean_by_case(records: list[RequestRecord]) -> dict[str, float]:
        grouped: dict[str, list[bool]] = defaultdict(list)
        for r in records:
            grouped[r.case_id].append(r.exact_match)
        return {cid: sum(v) / len(v) for cid, v in grouped.items()}

    base_by_case = _mean_by_case(baseline)
    cand_by_case = _mean_by_case(candidate)
    shared_ids = sorted(set(base_by_case) & set(cand_by_case))

    diffs = [cand_by_case[cid] - base_by_case[cid] for cid in shared_ids]
    n_pairs = len(diffs)

    if n_pairs == 0:
        return PairedComparison(
            metric_name="exact_match",
            n_pairs=0,
            mean_difference=None,
            ci_low=None,
            ci_high=None,
            n_bootstrap=n_bootstrap,
            seed=seed,
            sufficient_for_inference=False,
            note="No case_id was evaluated under both variants; no paired comparison is possible.",
        )

    mean_diff = sum(diffs) / n_pairs
    rng = random.Random(seed)
    bootstrap_means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [diffs[rng.randrange(n_pairs)] for _ in range(n_pairs)]
        bootstrap_means.append(sum(sample) / n_pairs)
    bootstrap_means.sort()
    ci_low = bootstrap_means[int(0.025 * n_bootstrap)]
    ci_high = bootstrap_means[min(n_bootstrap - 1, int(0.975 * n_bootstrap))]

    sufficient = n_pairs >= min_pairs
    note = (
        "Bootstrap 95% interval over paired per-case differences in exact_match. "
        f"{'Sample size meets' if sufficient else 'Sample size is below'} the configured "
        f"minimum of {min_pairs} pairs; treat this as "
        f"{'a candidate signal' if sufficient else 'exploratory only, not a confirmatory result'}."
    )

    return PairedComparison(
        metric_name="exact_match",
        n_pairs=n_pairs,
        mean_difference=round(mean_diff, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        n_bootstrap=n_bootstrap,
        seed=seed,
        sufficient_for_inference=sufficient,
        note=note,
    )


@dataclass
class Decision:
    verdict: str  # "accept" | "reject" | "inconclusive"
    reasons: list[str]


def decide(
    baseline_summary: VariantSummary,
    candidate_summary: VariantSummary,
    paired: PairedComparison,
    model_comparison: ModelDistributionComparison,
    constraints: Constraints,
) -> Decision:
    reasons: list[str] = []

    if not paired.sufficient_for_inference:
        reasons.append(
            f"Only {paired.n_pairs} paired case(s) were available "
            f"(minimum {constraints.min_pairs_for_decision}); evidence is insufficient for a "
            "confirmatory decision."
        )
        return Decision(verdict="inconclusive", reasons=reasons)

    if model_comparison.distributions_diverge:
        reasons.append(
            "Baseline and candidate model distributions diverge "
            f"(total variation distance={model_comparison.total_variation_distance}, "
            f"threshold={constraints.max_model_distribution_tvd}); any effect is confounded "
            "with model selection."
        )
        return Decision(verdict="inconclusive", reasons=reasons)

    if (
        constraints.min_quality is not None
        and candidate_summary.quality.exact_match_rate < constraints.min_quality
    ):
        reasons.append(
            f"Candidate exact_match_rate {candidate_summary.quality.exact_match_rate} is below "
            f"the required minimum {constraints.min_quality}."
        )
        return Decision(verdict="reject", reasons=reasons)

    if (
        constraints.max_cost_per_request is not None
        and candidate_summary.cost_latency.mean_cost_per_request is not None
        and candidate_summary.cost_latency.mean_cost_per_request > constraints.max_cost_per_request
    ):
        reasons.append(
            "Candidate mean cost per request "
            f"{candidate_summary.cost_latency.mean_cost_per_request} exceeds the limit "
            f"{constraints.max_cost_per_request}."
        )
        return Decision(verdict="reject", reasons=reasons)

    if (
        constraints.max_p95_latency_ms is not None
        and candidate_summary.cost_latency.p95_latency_ms is not None
        and candidate_summary.cost_latency.p95_latency_ms > constraints.max_p95_latency_ms
    ):
        reasons.append(
            f"Candidate p95 latency {candidate_summary.cost_latency.p95_latency_ms}ms exceeds "
            f"the limit {constraints.max_p95_latency_ms}ms."
        )
        return Decision(verdict="reject", reasons=reasons)

    if paired.ci_low is not None and paired.ci_low > 0:
        reasons.append(
            f"Candidate improves paired exact_match by {paired.mean_difference} "
            f"(95% CI [{paired.ci_low}, {paired.ci_high}]), with no constraint violated."
        )
        return Decision(verdict="accept", reasons=reasons)

    if paired.ci_high is not None and paired.ci_high < 0:
        reasons.append(
            f"Candidate paired exact_match difference {paired.mean_difference} "
            f"(95% CI [{paired.ci_low}, {paired.ci_high}]) is below baseline."
        )
        return Decision(verdict="reject", reasons=reasons)

    reasons.append(
        "The bootstrap interval for the paired exact_match difference "
        f"([{paired.ci_low}, {paired.ci_high}]) includes zero; the evidence does not clearly "
        "support either accepting or rejecting the candidate."
    )
    return Decision(verdict="inconclusive", reasons=reasons)
