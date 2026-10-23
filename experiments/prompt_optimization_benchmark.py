"""Command-line interface for the invoice-extraction prompt benchmark.

Run from the repository root (PowerShell or any shell):
    python experiments/prompt_optimization_benchmark.py <command> [options]

Commands:
    check-config        Validate environment configuration (no API calls).
    validate-dataset     Validate the dataset file structurally (no API calls).
    smoke-test           Tiny pipeline check. NOT evidence of prompt quality.
    benchmark-dev        Run baseline vs candidate on the development split.
    benchmark-held-out   Run baseline vs candidate on the held-out split.
    analyze              Recompute analysis/report from a saved run (no API calls).

Required environment variable for any command that calls the API:
    OPENROUTER_API_KEY

The API key is never printed. See experiments/README.md for full
documentation, environment variables, and how to interpret results.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt_benchmark import prompts as prompts_module  # noqa: E402
from prompt_benchmark import reporting  # noqa: E402
from prompt_benchmark.analysis import (  # noqa: E402
    compare_model_distributions,
    decide,
    paired_exact_match_comparison,
    summarize_variant,
)
from prompt_benchmark.client import OpenRouterClient  # noqa: E402
from prompt_benchmark.config import BenchmarkConfig, load_config_from_env, validate_config  # noqa: E402
from prompt_benchmark.dataset import (  # noqa: E402
    DATASET_VERSION,
    default_dataset_path,
    dev_cases,
    held_out_cases,
    load_dataset,
    validate_dataset,
)
from prompt_benchmark.runner import build_plan, execute_plan  # noqa: E402
from prompt_benchmark.schema import Constraints, RunManifest, utc_now_iso  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"
EXPERIMENT_ID_DEFAULT = "invoice-extraction-benchmark"
SEED_DEFAULT = 20261023

LIMITATIONS = [
    "The dataset is small and synthetic; it does not represent production invoice traffic "
    "and cannot support strong generalization claims.",
    "OpenRouter free-model routing can select different underlying models across requests. "
    "Any baseline-vs-candidate difference may be confounded with model selection unless the "
    "model distribution comparison in this report shows comparable coverage.",
    "The unsupported-inference rate is approximated using authored decoy values and is only "
    "defined for fields where a decoy was labeled in the dataset.",
]


def _make_run_id(tag: str) -> str:
    return f"{tag}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _print_problems(title: str, problems: list[str]) -> None:
    print(title)
    for p in problems:
        print(f"  - {p}")


def _apply_overrides(config: BenchmarkConfig, args: argparse.Namespace) -> BenchmarkConfig:
    overrides = {}
    # `is not None`, not truthiness: an explicit --concurrency 0 must still
    # override so validate_config() can reject it with a clear message,
    # rather than being silently dropped in favor of the existing default.
    if getattr(args, "concurrency", None) is not None:
        overrides["concurrency"] = args.concurrency
    return replace(config, **overrides) if overrides else config


def _build_constraints(args: argparse.Namespace) -> Constraints:
    return Constraints(
        min_quality=args.min_quality,
        max_cost_per_request=args.max_cost_per_request,
        max_p95_latency_ms=args.max_p95_latency_ms,
        min_pairs_for_decision=args.min_pairs,
    )


def _effective_limit(args: argparse.Namespace, config: BenchmarkConfig) -> int | None:
    """Resolve the total-planned-requests cap.

    The CLI's own `--limit` always wins; otherwise fall back to
    `BENCHMARK_CASE_LIMIT` (parsed into `config.request_limit`) so the
    environment variable has an effect even when `--limit` is omitted.
    """
    explicit = getattr(args, "limit", None)
    return explicit if explicit is not None else config.request_limit


def _limit_problems(limit: int | None) -> list[str]:
    """Reject a non-positive request cap before any API call is made.

    `runner.execute_plan` treats a non-positive limit as "zero planned
    requests" rather than silently running the full plan (`--limit 0`)
    or an off-by-one subset via negative-index slicing (`--limit -1`).
    Both are almost certainly a mistake rather than an intentional cap,
    so fail clearly here instead of spending zero-but-confusing API
    calls on a run the user did not mean to request.
    """
    if limit is not None and limit <= 0:
        return [f"--limit must be a positive integer when set (got {limit})."]
    return []


def cmd_check_config(args: argparse.Namespace) -> int:
    config = load_config_from_env()
    problems = validate_config(config, require_api_key=not args.allow_missing_key)
    print(f"Model: {config.model}")
    print(f"Base URL: {config.base_url}")
    print(
        f"Timeout: {config.timeout_s}s  Max retries: {config.max_retries}  "
        f"Concurrency: {config.concurrency}"
    )
    print(f"API key present: {bool(config.api_key)}")
    if problems:
        _print_problems("Configuration problems:", problems)
        return 1
    print("Configuration looks usable.")
    return 0


def cmd_validate_dataset(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset) if args.dataset else default_dataset_path()
    cases = load_dataset(dataset_path)
    report = validate_dataset(cases)

    print(f"Loaded {len(cases)} cases from {dataset_path}")
    print(f"  dev: {len(dev_cases(cases))}  held_out: {len(held_out_cases(cases))}")

    if report.warnings:
        print("Warnings:")
        for w in report.warnings:
            print(f"  - [{w.case_id}] {w.message}")

    if report.errors:
        print("Errors:")
        for e in report.errors:
            print(f"  - [{e.case_id}] {e.message}")
        return 1

    print("Dataset is structurally valid.")
    return 0


def _run_variants(cases, config: BenchmarkConfig, *, tag: str, seed: int, limit, experiment_id: str):
    client = OpenRouterClient(config)
    variants = prompts_module.all_variants()
    plan = build_plan(cases, variants, seed=seed)
    run_id = _make_run_id(tag)

    planned = len(plan) if limit is None else min(limit, len(plan)) if limit > 0 else 0
    print(f"Requested model: {config.model}")
    print(f"Cases: {len(cases)}  Variants: {len(variants)}  Planned requests: {planned}")

    def _on_record(record) -> None:
        status = "ERROR" if not record.success else ("PASS" if record.exact_match else "MISMATCH")
        model = record.actual_model or "unknown-model"
        print(f"[{record.variant_name}] {record.case_id}: {status}; model={model}")

    records = execute_plan(
        plan,
        client,
        config,
        experiment_id=experiment_id,
        run_id=run_id,
        dataset_version=DATASET_VERSION,
        on_record=_on_record,
        limit=limit,
        max_workers=config.concurrency,
    )
    return run_id, records


def _persist_and_report(
    args: argparse.Namespace,
    run_id: str,
    records,
    config: BenchmarkConfig,
    *,
    dataset_split: str,
    research_question: str,
    hypothesis: str,
) -> int:
    results_dir = Path(args.output) if args.output else RESULTS_DIR
    records_path = results_dir / f"{run_id}.jsonl"
    manifest_path = results_dir / f"{run_id}_manifest.json"
    report_path = results_dir / f"{run_id}_report.md"

    reporting.write_jsonl_atomic(records_path, records)

    constraints = _build_constraints(args)
    manifest = RunManifest(
        experiment_id=args.experiment_id,
        run_id=run_id,
        created_utc=utc_now_iso(),
        research_question=research_question,
        hypothesis=hypothesis,
        primary_metric="exact_match_rate (strict, over all requests)",
        secondary_metrics=[
            "mean_field_accuracy",
            "contract_validity_rate",
            "task_completion_rate",
            "cost_per_successful_task",
            "p95_latency_ms",
        ],
        baseline_variant="baseline:v1",
        candidate_variant="candidate:v1",
        dataset_version=DATASET_VERSION,
        dataset_split=dataset_split,
        requested_model=config.model,
        base_url=config.base_url,
        temperature=config.temperature,
        trial_count=1,
        constraints=constraints,
        limitations=LIMITATIONS,
    )
    reporting.write_json_atomic(manifest_path, manifest.to_json_dict())

    baseline_records = [r for r in records if r.variant_name == "baseline"]
    candidate_records = [r for r in records if r.variant_name == "candidate"]

    baseline_summary = summarize_variant(baseline_records)
    candidate_summary = summarize_variant(candidate_records)
    paired = paired_exact_match_comparison(
        baseline_records, candidate_records, min_pairs=constraints.min_pairs_for_decision
    )
    model_comparison = compare_model_distributions(
        baseline_records, candidate_records, tvd_threshold=constraints.max_model_distribution_tvd
    )
    decision = decide(baseline_summary, candidate_summary, paired, model_comparison, constraints)

    report_text = reporting.build_markdown_report(
        manifest,
        baseline_summary,
        candidate_summary,
        paired,
        model_comparison,
        decision,
        dataset_warnings=[],
        next_experiment=(
            "If inconclusive, increase the paired sample size (more held-out cases or repeated "
            "trials) before drawing a conclusion. If a specific field dominates the remaining "
            "errors, write a narrowly-scoped candidate revision targeting that error category "
            "and re-run on development data before touching held-out data again."
        ),
    )
    reporting.write_text_atomic(report_path, report_text)

    print(f"\nDecision: {decision.verdict.upper()}")
    for reason in decision.reasons:
        print(f"  - {reason}")
    print(f"\nRecords:  {records_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Report:   {report_path}")
    return 0


def cmd_smoke_test(args: argparse.Namespace) -> int:
    print("SMOKE TEST: pipeline connectivity check only. This is NOT evidence of prompt quality.")
    config = _apply_overrides(load_config_from_env(), args)
    problems = validate_config(config)
    if problems:
        _print_problems("Cannot run smoke test:", problems)
        return 2

    dataset_path = Path(args.dataset) if args.dataset else default_dataset_path()
    cases = load_dataset(dataset_path)
    subset = dev_cases(cases)[: max(1, args.limit or 2)]

    run_id, records = _run_variants(
        subset, config, tag="smoke", seed=args.seed, limit=None, experiment_id=args.experiment_id
    )
    return _persist_and_report(
        args,
        run_id,
        records,
        config,
        dataset_split="dev[smoke-subset]",
        research_question="Pipeline connectivity check only.",
        hypothesis="N/A: this run is a smoke test, not a hypothesis-driven experiment.",
    )


def cmd_benchmark_dev(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config_from_env(), args)
    problems = validate_config(config)
    if problems:
        _print_problems("Cannot run benchmark:", problems)
        return 2

    dataset_path = Path(args.dataset) if args.dataset else default_dataset_path()
    cases = load_dataset(dataset_path)
    validation = validate_dataset(cases)
    if not validation.is_valid:
        _print_problems(
            "Dataset is invalid:", [f"[{e.case_id}] {e.message}" for e in validation.errors]
        )
        return 2

    dev = dev_cases(cases)
    limit = _effective_limit(args, config)
    limit_problems = _limit_problems(limit)
    if limit_problems:
        _print_problems("Cannot run benchmark:", limit_problems)
        return 2

    run_id, records = _run_variants(
        dev, config, tag="dev", seed=args.seed, limit=limit, experiment_id=args.experiment_id,
    )
    return _persist_and_report(
        args,
        run_id,
        records,
        config,
        dataset_split="dev",
        research_question=(
            "Does the candidate prompt improve invoice-extraction task quality over the "
            "baseline prompt on development data, without violating cost/latency constraints?"
        ),
        hypothesis=(
            "Explicit ambiguity handling, an evidence-only extraction rule, and untrusted-content "
            "framing in the candidate prompt reduce hallucinated and decoy-driven field errors "
            "relative to the baseline, increasing exact_match_rate."
        ),
    )


def cmd_benchmark_held_out(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config_from_env(), args)
    problems = validate_config(config)
    if problems:
        _print_problems("Cannot run benchmark:", problems)
        return 2

    dataset_path = Path(args.dataset) if args.dataset else default_dataset_path()
    cases = load_dataset(dataset_path)
    validation = validate_dataset(cases)
    if not validation.is_valid:
        _print_problems(
            "Dataset is invalid:", [f"[{e.case_id}] {e.message}" for e in validation.errors]
        )
        return 2

    held = held_out_cases(cases)
    print(
        "HELD-OUT EVALUATION: this split must not be used to choose between prompt revisions. "
        "Run it only to confirm a candidate already selected on development data."
    )
    limit = _effective_limit(args, config)
    limit_problems = _limit_problems(limit)
    if limit_problems:
        _print_problems("Cannot run benchmark:", limit_problems)
        return 2

    run_id, records = _run_variants(
        held, config, tag="held_out", seed=args.seed, limit=limit, experiment_id=args.experiment_id,
    )
    return _persist_and_report(
        args,
        run_id,
        records,
        config,
        dataset_split="held_out",
        research_question="Does the development-set improvement persist on unseen held-out cases?",
        hypothesis="The candidate's development-set improvement generalizes to held-out cases.",
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    records_path = Path(args.records)
    records = reporting.load_records_jsonl(records_path)
    if not records:
        print(f"No records found in {records_path}")
        return 1

    baseline_records = [r for r in records if r.variant_name == "baseline"]
    candidate_records = [r for r in records if r.variant_name == "candidate"]
    constraints = _build_constraints(args)

    baseline_summary = summarize_variant(baseline_records)
    candidate_summary = summarize_variant(candidate_records)
    paired = paired_exact_match_comparison(
        baseline_records, candidate_records, min_pairs=constraints.min_pairs_for_decision
    )
    model_comparison = compare_model_distributions(
        baseline_records, candidate_records, tvd_threshold=constraints.max_model_distribution_tvd
    )
    decision = decide(baseline_summary, candidate_summary, paired, model_comparison, constraints)

    manifest = RunManifest(
        experiment_id=records[0].experiment_id,
        run_id=f"analysis_{records[0].run_id}",
        created_utc=utc_now_iso(),
        research_question=args.research_question or "(reanalysis of a saved run; see its manifest file)",
        hypothesis=args.hypothesis or "(reanalysis of a saved run; see its manifest file)",
        primary_metric="exact_match_rate (strict, over all requests)",
        secondary_metrics=["mean_field_accuracy", "contract_validity_rate", "task_completion_rate"],
        baseline_variant="baseline:v1",
        candidate_variant="candidate:v1",
        dataset_version=records[0].dataset_version,
        dataset_split=records[0].split,
        requested_model=records[0].requested_model,
        base_url="(not re-queried; offline analysis)",
        temperature=records[0].temperature,
        trial_count=1,
        constraints=constraints,
        limitations=LIMITATIONS,
    )

    report_text = reporting.build_markdown_report(
        manifest,
        baseline_summary,
        candidate_summary,
        paired,
        model_comparison,
        decision,
        dataset_warnings=[],
        next_experiment="Re-run the live benchmark if the prompts or dataset have changed since this run.",
    )

    output_dir = Path(args.output) if args.output else records_path.parent
    report_path = output_dir / f"{records_path.stem}_reanalysis_report.md"
    if report_path.exists():
        report_path.unlink()
    reporting.write_text_atomic(report_path, report_text)

    print(f"Decision: {decision.verdict.upper()}")
    for reason in decision.reasons:
        print(f"  - {reason}")
    print(f"Report: {report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt_optimization_benchmark",
        description="Invoice-extraction prompt-optimization benchmark (OpenRouter free-model routing).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _common(p: argparse.ArgumentParser, needs_network: bool) -> None:
        p.add_argument("--dataset", help="Path to the dataset JSONL file.")
        p.add_argument("--experiment-id", default=EXPERIMENT_ID_DEFAULT)
        p.add_argument("--seed", type=int, default=SEED_DEFAULT)
        p.add_argument("--output", help="Directory for results (default: experiments/results).")
        p.add_argument("--min-quality", type=float, default=None)
        p.add_argument("--max-cost-per-request", type=float, default=None)
        p.add_argument("--max-p95-latency-ms", type=float, default=None)
        p.add_argument("--min-pairs", type=int, default=10)
        if needs_network:
            p.add_argument(
                "--limit", type=int, default=None,
                help="Cap the total number of planned requests (across both variants).",
            )
            p.add_argument(
                "--concurrency", type=int, default=None, help="Override BENCHMARK_CONCURRENCY."
            )

    p_config = sub.add_parser("check-config", help="Validate environment configuration (no API calls).")
    p_config.add_argument("--allow-missing-key", action="store_true")
    p_config.set_defaults(func=cmd_check_config)

    p_dataset = sub.add_parser("validate-dataset", help="Validate the dataset file structurally.")
    p_dataset.add_argument("--dataset", help="Path to the dataset JSONL file.")
    p_dataset.set_defaults(func=cmd_validate_dataset)

    p_smoke = sub.add_parser("smoke-test", help="Tiny pipeline check. NOT evidence of prompt quality.")
    _common(p_smoke, needs_network=True)
    p_smoke.set_defaults(func=cmd_smoke_test)

    p_dev = sub.add_parser("benchmark-dev", help="Run baseline vs candidate on the development split.")
    _common(p_dev, needs_network=True)
    p_dev.set_defaults(func=cmd_benchmark_dev)

    p_held = sub.add_parser(
        "benchmark-held-out", help="Run baseline vs candidate on the held-out split."
    )
    _common(p_held, needs_network=True)
    p_held.set_defaults(func=cmd_benchmark_held_out)

    p_analyze = sub.add_parser(
        "analyze", help="Recompute analysis/report from a saved run (no API calls)."
    )
    p_analyze.add_argument("--records", required=True, help="Path to a saved *.jsonl record file.")
    p_analyze.add_argument("--output", help="Directory for the regenerated report.")
    p_analyze.add_argument("--research-question", default=None)
    p_analyze.add_argument("--hypothesis", default=None)
    p_analyze.add_argument("--min-quality", type=float, default=None)
    p_analyze.add_argument("--max-cost-per-request", type=float, default=None)
    p_analyze.add_argument("--max-p95-latency-ms", type=float, default=None)
    p_analyze.add_argument("--min-pairs", type=int, default=10)
    p_analyze.set_defaults(func=cmd_analyze)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
