"""Atomic artifact I/O and human-readable report generation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .analysis import Decision, ModelDistributionComparison, PairedComparison, VariantSummary
from .schema import RequestRecord, RunManifest, redact


def write_json_atomic(path: str | Path, obj: dict[str, Any]) -> Path:
    """Write a JSON file without ever overwriting an existing run's output."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(redact(obj), handle, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return path


def write_jsonl_atomic(path: str | Path, records: Iterable[RequestRecord]) -> Path:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.to_json_dict(), ensure_ascii=False) + "\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return path


def write_text_atomic(path: str | Path, text: str) -> Path:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return path


def load_records_jsonl(path: str | Path) -> list[RequestRecord]:
    """Load a previously saved *.jsonl request-record file for offline analysis."""
    path = Path(path)
    records: list[RequestRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            records.append(RequestRecord(**data))
    return records


def _fmt(value: Any) -> str:
    return "n/a" if value is None else str(value)


def build_markdown_report(
    manifest: RunManifest,
    baseline_summary: VariantSummary,
    candidate_summary: VariantSummary,
    paired: PairedComparison,
    model_comparison: ModelDistributionComparison,
    decision: Decision,
    dataset_warnings: list[str],
    next_experiment: str,
) -> str:
    lines: list[str] = []
    a = lines.append

    a(f"# Prompt Optimization Report: {manifest.experiment_id}")
    a("")
    a(f"Run `{manifest.run_id}` generated {manifest.created_utc}.")
    a("")
    a("## 1. Objective and Hypothesis")
    a("")
    a(f"**Research question:** {manifest.research_question}")
    a("")
    a(f"**Hypothesis:** {manifest.hypothesis}")
    a("")
    a(f"**Primary metric:** {manifest.primary_metric}")
    a(f"**Secondary metrics:** {', '.join(manifest.secondary_metrics) or 'none'}")
    a("")
    a("## 2. Configuration and Dataset")
    a("")
    a(f"- Requested model: `{manifest.requested_model}`")
    a(f"- Base URL: `{manifest.base_url}`")
    a(f"- Temperature: {manifest.temperature}")
    a(f"- Dataset version: `{manifest.dataset_version}`")
    a(f"- Dataset split evaluated: `{manifest.dataset_split}`")
    a(f"- Trial count per case per variant: {manifest.trial_count}")
    if dataset_warnings:
        a("- Dataset validation warnings:")
        for w in dataset_warnings:
            a(f"  - {w}")
    a("")
    a("## 3. Prompt Versions")
    a("")
    a(f"- Baseline: `{manifest.baseline_variant}`")
    a(f"- Candidate: `{manifest.candidate_variant}`")
    a("")
    a("## 4. Aggregate and Per-Model Metrics")
    a("")
    a("| Metric | Baseline | Candidate |")
    a("|---|---|---|")
    a(f"| Requests | {baseline_summary.n_requests} | {candidate_summary.n_requests} |")
    a(
        "| Request success rate | "
        f"{_fmt(baseline_summary.reliability.request_success_rate)} | "
        f"{_fmt(candidate_summary.reliability.request_success_rate)} |"
    )
    a(
        "| Task completion rate | "
        f"{_fmt(baseline_summary.reliability.task_completion_rate)} | "
        f"{_fmt(candidate_summary.reliability.task_completion_rate)} |"
    )
    a(
        "| Exact match rate (all requests) | "
        f"{_fmt(baseline_summary.quality.exact_match_rate)} | "
        f"{_fmt(candidate_summary.quality.exact_match_rate)} |"
    )
    a(
        "| Exact match rate (completed requests only, n="
        f"{baseline_summary.reliability.completed_requests}/{baseline_summary.n_requests} vs "
        f"{candidate_summary.reliability.completed_requests}/{candidate_summary.n_requests}) | "
        f"{_fmt(baseline_summary.quality_conditional.exact_match_rate)} | "
        f"{_fmt(candidate_summary.quality_conditional.exact_match_rate)} |"
    )
    a(
        "| Semantic exact match rate (secondary) | "
        f"{_fmt(baseline_summary.quality.semantic_exact_match_rate)} | "
        f"{_fmt(candidate_summary.quality.semantic_exact_match_rate)} |"
    )
    a(
        "| Mean field accuracy | "
        f"{_fmt(baseline_summary.quality.mean_field_accuracy)} | "
        f"{_fmt(candidate_summary.quality.mean_field_accuracy)} |"
    )
    a(
        "| Contract validity rate (among parsed JSON) | "
        f"{_fmt(baseline_summary.contract.contract_validity_rate)} | "
        f"{_fmt(candidate_summary.contract.contract_validity_rate)} |"
    )
    a(
        "| Refusal-like rate | "
        f"{_fmt(baseline_summary.reliability.refusal_like_rate)} | "
        f"{_fmt(candidate_summary.reliability.refusal_like_rate)} |"
    )
    a(
        "| Unknown actual-model rate | "
        f"{_fmt(baseline_summary.reliability.unknown_actual_model_rate)} | "
        f"{_fmt(candidate_summary.reliability.unknown_actual_model_rate)} |"
    )
    a("")
    a("### Model selection frequencies")
    a("")
    a(f"- Baseline: {baseline_summary.model_frequencies}")
    a(f"- Candidate: {candidate_summary.model_frequencies}")
    a(
        f"- Distribution divergence (total variation distance): "
        f"{model_comparison.total_variation_distance} "
        f"({'DIVERGES' if model_comparison.distributions_diverge else 'comparable'})"
    )
    a(f"- {model_comparison.note}")
    a("")
    a("## 5. Failure Analysis")
    a("")
    a(f"- Baseline error categories: {baseline_summary.reliability.error_category_counts}")
    a(f"- Candidate error categories: {candidate_summary.reliability.error_category_counts}")
    a(f"- Baseline parse outcomes: {baseline_summary.parsing.counts}")
    a(f"- Candidate parse outcomes: {candidate_summary.parsing.counts}")
    a("")
    a(
        "Per-field extraction quality (candidate, over all requests; precision/recall use the "
        "slot-filling definition where a wrong value counts against both):"
    )
    a("")
    a(
        "| Field | Precision | Recall | F1 | Missing-value acc. | Hallucinated rate | "
        "Unsupported-inference rate (n) |"
    )
    a("|---|---|---|---|---|---|---|")
    for field_name, m in candidate_summary.quality.per_field.items():
        a(
            f"| {field_name} | {_fmt(m.precision)} | {_fmt(m.recall)} | {_fmt(m.f1)} | "
            f"{_fmt(m.missing_value_accuracy)} | {_fmt(m.hallucinated_value_rate)} | "
            f"{_fmt(m.unsupported_inference_rate)} (n={m.unsupported_inference_n}) |"
        )
    a("")
    a("## 6. Cost and Latency")
    a("")
    cl_b, cl_c = baseline_summary.cost_latency, candidate_summary.cost_latency
    a("| Metric | Baseline | Candidate |")
    a("|---|---|---|")
    a(
        "| Requests with token usage | "
        f"{cl_b.n_with_token_usage}/{cl_b.n_requests} | {cl_c.n_with_token_usage}/{cl_c.n_requests} |"
    )
    a(f"| Mean total tokens | {_fmt(cl_b.mean_total_tokens)} | {_fmt(cl_c.mean_total_tokens)} |")
    a(
        "| Requests with provider cost | "
        f"{cl_b.n_with_cost}/{cl_b.n_requests} | {cl_c.n_with_cost}/{cl_c.n_requests} |"
    )
    a(
        "| Mean cost per request | "
        f"{_fmt(cl_b.mean_cost_per_request)} | {_fmt(cl_c.mean_cost_per_request)} |"
    )
    a(
        "| Cost per successful task | "
        f"{_fmt(cl_b.cost_per_successful_task)} | {_fmt(cl_c.cost_per_successful_task)} |"
    )
    a(
        f"| Median / p95 latency (ms), n={cl_b.n_latency_samples} vs n={cl_c.n_latency_samples} | "
        f"{_fmt(cl_b.median_latency_ms)} / {_fmt(cl_b.p95_latency_ms)} | "
        f"{_fmt(cl_c.median_latency_ms)} / {_fmt(cl_c.p95_latency_ms)} |"
    )
    if cl_b.latency_sample_is_small or cl_c.latency_sample_is_small:
        a("")
        a(
            f"Latency percentiles use the {cl_c.percentile_method}. At least one variant has "
            f"fewer than {20} successful samples; treat its p95 as indicative only, not a "
            "reliable tail estimate."
        )
    a("")
    a("## 7. Uncertainty and Limitations")
    a("")
    a(
        f"- Paired exact-match comparison: n={paired.n_pairs} matched case(s), "
        f"mean difference={_fmt(paired.mean_difference)}, "
        f"95% bootstrap CI=[{_fmt(paired.ci_low)}, {_fmt(paired.ci_high)}] "
        f"({paired.n_bootstrap} resamples, seed={paired.seed})."
    )
    a(f"- {paired.note}")
    for limitation in manifest.limitations:
        a(f"- {limitation}")
    a("")
    a("## 8. Acceptance Decision")
    a("")
    a(f"**Verdict: {decision.verdict.upper()}**")
    a("")
    for reason in decision.reasons:
        a(f"- {reason}")
    a("")
    a("## 9. Recommended Next Experiment")
    a("")
    a(next_experiment)
    a("")

    return "\n".join(lines)
