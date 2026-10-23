"""Tests for prompt_benchmark.analysis: aggregation, comparisons, decisions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark import analysis as an
from prompt_benchmark.schema import SCHEMA_VERSION, Constraints, RequestRecord

EXPECTED = {
    "invoice_id": "INV-1",
    "vendor": "Acme",
    "date": "2026-01-01",
    "total": "100.00",
    "currency": "USD",
}


def make_record(
    case_id: str = "c1",
    variant_name: str = "baseline",
    success: bool = True,
    parse_outcome: str = "valid_json_object",
    contract_valid: bool | None = True,
    exact_match: bool = True,
    semantic_exact_match: bool = True,
    field_accuracy: float = 1.0,
    actual_model: str | None = "model-a",
    failure_category: str | None = None,
    latency_ms: float = 100.0,
    total_tokens: int | None = 50,
    prompt_tokens: int | None = 30,
    completion_tokens: int | None = 20,
    provider_cost: float | None = 0.001,
    retries: int = 0,
    raw_response_text: str | None = '{"invoice_id": "INV-1"}',
    expected: dict | None = None,
    parsed: dict | None = None,
    field_matches_strict: dict | None = None,
    field_matches_semantic: dict | None = None,
    decoy_selected: dict | None = None,
) -> RequestRecord:
    exp = expected if expected is not None else dict(EXPECTED)
    par = parsed if parsed is not None else (dict(EXPECTED) if parse_outcome == "valid_json_object" else None)
    strict = field_matches_strict if field_matches_strict is not None else {
        f: (par.get(f) == exp.get(f) if par else False) for f in EXPECTED
    }
    semantic = field_matches_semantic if field_matches_semantic is not None else dict(strict)

    return RequestRecord(
        schema_version=SCHEMA_VERSION,
        experiment_id="exp-1",
        run_id="run-1",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        dataset_version="invoice-extraction-v2",
        case_id=case_id,
        split="dev",
        variant_name=variant_name,
        variant_version="v1",
        prompt_hash="abc123",
        requested_model="openrouter/free",
        actual_model=actual_model,
        temperature=0.0,
        attempts=1,
        retries=retries,
        success=success,
        failure_category=failure_category,
        error_message=None,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        provider_cost=provider_cost,
        request_id="req-1",
        raw_response_text=raw_response_text,
        parse_outcome=parse_outcome,
        contract_valid=contract_valid,
        missing_keys=[],
        unexpected_keys=[],
        type_violations={},
        invalid_date_fields=[],
        invalid_currency_fields=[],
        invalid_total_fields=[],
        expected=exp,
        parsed=par,
        field_matches_strict=strict,
        field_matches_semantic=semantic,
        exact_match=exact_match,
        semantic_exact_match=semantic_exact_match,
        field_accuracy=field_accuracy,
        decoy_selected=decoy_selected or {},
    )


class ReliabilityTests(unittest.TestCase):
    def test_empty_records_handled_without_crashing(self) -> None:
        metrics = an.compute_reliability([])
        self.assertEqual(metrics.total_requests, 0)
        self.assertIsNone(metrics.request_success_rate)

    def test_failed_requests_count_in_denominator(self) -> None:
        records = [
            make_record(success=True, parse_outcome="valid_json_object", contract_valid=True),
            make_record(success=False, parse_outcome="unsupported_shape", contract_valid=None, raw_response_text=None),
        ]
        metrics = an.compute_reliability(records)
        self.assertEqual(metrics.total_requests, 2)
        self.assertEqual(metrics.successful_requests, 1)
        self.assertEqual(metrics.request_success_rate, 0.5)
        self.assertEqual(metrics.task_completion_rate, 0.5)

    def test_retry_rate_computed(self) -> None:
        records = [make_record(retries=1), make_record(retries=0)]
        metrics = an.compute_reliability(records)
        self.assertEqual(metrics.requests_with_retries, 1)
        self.assertEqual(metrics.retry_rate, 0.5)

    def test_unknown_actual_model_rate(self) -> None:
        records = [make_record(actual_model=None), make_record(actual_model="m")]
        metrics = an.compute_reliability(records)
        self.assertEqual(metrics.unknown_actual_model_rate, 0.5)

    def test_error_category_counts(self) -> None:
        records = [
            make_record(success=False, failure_category="timeout", parse_outcome="unsupported_shape", contract_valid=None),
            make_record(success=False, failure_category="timeout", parse_outcome="unsupported_shape", contract_valid=None),
            make_record(success=False, failure_category="rate_limited", parse_outcome="unsupported_shape", contract_valid=None),
        ]
        metrics = an.compute_reliability(records)
        self.assertEqual(metrics.error_category_counts, {"timeout": 2, "rate_limited": 1})


class QualityTests(unittest.TestCase):
    def test_quality_denominator_includes_failed_requests(self) -> None:
        records = [
            make_record(exact_match=True, field_accuracy=1.0),
            make_record(
                success=False, exact_match=False, field_accuracy=0.0,
                parse_outcome="unsupported_shape", contract_valid=None,
                parsed=None, field_matches_strict={f: False for f in EXPECTED},
                field_matches_semantic={f: False for f in EXPECTED},
                raw_response_text=None,
            ),
        ]
        quality = an.compute_quality(records)
        self.assertEqual(quality.sample_size, 2)
        self.assertEqual(quality.exact_match_rate, 0.5)

    def test_hallucinated_value_rate(self) -> None:
        expected = {**EXPECTED, "currency": None}
        records = [
            make_record(
                expected=expected,
                parsed={**EXPECTED, "currency": "USD"},
                field_matches_strict={**{f: True for f in EXPECTED}, "currency": False},
                field_matches_semantic={**{f: True for f in EXPECTED}, "currency": False},
            )
        ]
        quality = an.compute_quality(records)
        self.assertEqual(quality.per_field["currency"].hallucinated_value_rate, 1.0)
        self.assertEqual(quality.per_field["currency"].n_expected_null, 1)

    def test_missing_value_accuracy(self) -> None:
        expected = {**EXPECTED, "currency": None}
        records = [
            make_record(
                expected=expected,
                parsed={**EXPECTED, "currency": None},
                field_matches_strict={f: True for f in EXPECTED},
                field_matches_semantic={f: True for f in EXPECTED},
            )
        ]
        quality = an.compute_quality(records)
        self.assertEqual(quality.per_field["currency"].missing_value_accuracy, 1.0)

    def test_precision_recall_f1_with_wrong_value(self) -> None:
        records = [
            make_record(
                parsed={**EXPECTED, "vendor": "Wrong Vendor"},
                field_matches_strict={**{f: True for f in EXPECTED}, "vendor": False},
                field_matches_semantic={**{f: True for f in EXPECTED}, "vendor": False},
            )
        ]
        quality = an.compute_quality(records)
        vendor = quality.per_field["vendor"]
        self.assertEqual(vendor.precision, 0.0)
        self.assertEqual(vendor.recall, 0.0)
        self.assertIsNotNone(vendor.f1)  # f1 should be computed (0.0), not None, here
        self.assertEqual(vendor.f1, 0.0)

    def test_unsupported_inference_rate_uses_decoy_labels(self) -> None:
        records = [
            make_record(
                parsed={**EXPECTED, "invoice_id": "PO-999"},
                field_matches_strict={**{f: True for f in EXPECTED}, "invoice_id": False},
                field_matches_semantic={**{f: True for f in EXPECTED}, "invoice_id": False},
                decoy_selected={"invoice_id": True},
            ),
            make_record(decoy_selected={"invoice_id": False}),
        ]
        quality = an.compute_quality(records)
        self.assertEqual(quality.per_field["invoice_id"].unsupported_inference_n, 2)
        self.assertEqual(quality.per_field["invoice_id"].unsupported_inference_rate, 0.5)

    def test_empty_records_returns_zeroed_metrics(self) -> None:
        quality = an.compute_quality([])
        self.assertEqual(quality.sample_size, 0)
        self.assertEqual(quality.exact_match_rate, 0.0)
        for field_metrics in quality.per_field.values():
            self.assertIsNone(field_metrics.precision)


class ContractAndParsingTests(unittest.TestCase):
    def test_parsing_counts(self) -> None:
        records = [
            make_record(parse_outcome="valid_json_object"),
            make_record(parse_outcome="invalid_json", contract_valid=None, parsed=None, raw_response_text="bad"),
        ]
        parsing = an.compute_parsing(records)
        self.assertEqual(parsing.counts["valid_json_object"], 1)
        self.assertEqual(parsing.counts["invalid_json"], 1)

    def test_contract_sample_size_excludes_unparsed(self) -> None:
        records = [
            make_record(parse_outcome="valid_json_object", contract_valid=True),
            make_record(parse_outcome="invalid_json", contract_valid=None, parsed=None, raw_response_text="bad"),
        ]
        contract = an.compute_contract(records)
        self.assertEqual(contract.sample_size, 1)


class CostLatencyTests(unittest.TestCase):
    def test_percentiles_and_sample_size_flagged_small(self) -> None:
        records = [make_record(latency_ms=float(i)) for i in range(1, 6)]
        cl = an.compute_cost_latency(records, completed_count=5)
        self.assertEqual(cl.n_latency_samples, 5)
        self.assertTrue(cl.latency_sample_is_small)
        self.assertIsNotNone(cl.median_latency_ms)
        self.assertIsNotNone(cl.p95_latency_ms)

    def test_missing_cost_is_none_not_zero(self) -> None:
        records = [make_record(provider_cost=None)]
        cl = an.compute_cost_latency(records, completed_count=1)
        self.assertEqual(cl.n_with_cost, 0)
        self.assertIsNone(cl.total_provider_cost)
        self.assertIsNone(cl.mean_cost_per_request)

    def test_cost_per_successful_task(self) -> None:
        records = [make_record(provider_cost=0.002), make_record(provider_cost=0.002)]
        cl = an.compute_cost_latency(records, completed_count=2)
        self.assertAlmostEqual(cl.cost_per_successful_task, 0.002, places=6)


class ModelDistributionTests(unittest.TestCase):
    def test_identical_distributions_do_not_diverge(self) -> None:
        baseline = [make_record(actual_model="m1"), make_record(actual_model="m2")]
        candidate = [make_record(actual_model="m1"), make_record(actual_model="m2")]
        comparison = an.compare_model_distributions(baseline, candidate)
        self.assertEqual(comparison.total_variation_distance, 0.0)
        self.assertFalse(comparison.distributions_diverge)

    def test_fully_disjoint_distributions_diverge(self) -> None:
        baseline = [make_record(actual_model="m1"), make_record(actual_model="m1")]
        candidate = [make_record(actual_model="m2"), make_record(actual_model="m2")]
        comparison = an.compare_model_distributions(baseline, candidate)
        self.assertEqual(comparison.total_variation_distance, 1.0)
        self.assertTrue(comparison.distributions_diverge)


class PairedComparisonTests(unittest.TestCase):
    def test_no_shared_cases_is_insufficient(self) -> None:
        baseline = [make_record(case_id="a")]
        candidate = [make_record(case_id="b")]
        paired = an.paired_exact_match_comparison(baseline, candidate)
        self.assertEqual(paired.n_pairs, 0)
        self.assertFalse(paired.sufficient_for_inference)

    def test_repeated_trials_for_same_case_are_averaged(self) -> None:
        baseline = [make_record(case_id="a", exact_match=True), make_record(case_id="a", exact_match=False)]
        candidate = [make_record(case_id="a", exact_match=True)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=1)
        self.assertEqual(paired.n_pairs, 1)
        self.assertAlmostEqual(paired.mean_difference, 1.0 - 0.5)

    def test_small_sample_marked_insufficient(self) -> None:
        baseline = [make_record(case_id=str(i), exact_match=False) for i in range(3)]
        candidate = [make_record(case_id=str(i), exact_match=True) for i in range(3)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        self.assertFalse(paired.sufficient_for_inference)

    def test_sufficient_sample_with_consistent_improvement(self) -> None:
        baseline = [make_record(case_id=str(i), exact_match=False) for i in range(12)]
        candidate = [make_record(case_id=str(i), exact_match=True) for i in range(12)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        self.assertTrue(paired.sufficient_for_inference)
        self.assertGreater(paired.ci_low, 0)


class DecisionTests(unittest.TestCase):
    def _summary(self, records):
        return an.summarize_variant(records)

    def test_insufficient_pairs_is_inconclusive(self) -> None:
        baseline = [make_record(case_id=str(i)) for i in range(2)]
        candidate = [make_record(case_id=str(i)) for i in range(2)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        model_cmp = an.compare_model_distributions(baseline, candidate)
        decision = an.decide(
            self._summary(baseline), self._summary(candidate), paired, model_cmp, Constraints()
        )
        self.assertEqual(decision.verdict, "inconclusive")

    def test_diverging_models_force_inconclusive(self) -> None:
        baseline = [make_record(case_id=str(i), actual_model="m1", exact_match=False) for i in range(12)]
        candidate = [make_record(case_id=str(i), actual_model="m2", exact_match=True) for i in range(12)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        model_cmp = an.compare_model_distributions(baseline, candidate)
        decision = an.decide(
            self._summary(baseline), self._summary(candidate), paired, model_cmp, Constraints()
        )
        self.assertEqual(decision.verdict, "inconclusive")
        self.assertTrue(any("diverge" in r for r in decision.reasons))

    def test_clear_improvement_with_comparable_models_is_accepted(self) -> None:
        baseline = [make_record(case_id=str(i), actual_model="m1", exact_match=False) for i in range(12)]
        candidate = [make_record(case_id=str(i), actual_model="m1", exact_match=True) for i in range(12)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        model_cmp = an.compare_model_distributions(baseline, candidate)
        decision = an.decide(
            self._summary(baseline), self._summary(candidate), paired, model_cmp, Constraints()
        )
        self.assertEqual(decision.verdict, "accept")

    def test_quality_constraint_violation_is_rejected(self) -> None:
        baseline = [make_record(case_id=str(i), actual_model="m1", exact_match=False) for i in range(12)]
        candidate = [make_record(case_id=str(i), actual_model="m1", exact_match=True) for i in range(12)]
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        model_cmp = an.compare_model_distributions(baseline, candidate)
        # candidate's exact_match_rate is 1.0; an unreachable threshold forces the
        # quality-constraint branch regardless of the (otherwise passing) comparison.
        constraints = Constraints(min_quality=1.5)
        decision = an.decide(
            self._summary(baseline), self._summary(candidate), paired, model_cmp, constraints
        )
        self.assertEqual(decision.verdict, "reject")


if __name__ == "__main__":
    unittest.main()
