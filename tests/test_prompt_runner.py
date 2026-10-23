"""Tests for prompt_benchmark.runner: plan construction and execution.

No test here performs real network I/O -- `OpenRouterClient` is wired
to the same `FakeTransport` used by test_prompt_client.py. This file
exists specifically to exercise the full client -> evaluator -> record
pipeline end to end (previously only unit-tested in isolated pieces),
and to prove the "all requests fail -> never a misleading ACCEPT"
invariant through the real runner/analysis code, not just hand-built
fixtures.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark import analysis as an
from prompt_benchmark.client import OpenRouterClient, TransportTimeout
from prompt_benchmark.dataset import Case
from prompt_benchmark.prompts import BASELINE_V1, CANDIDATE_V1, all_variants
from prompt_benchmark.runner import RunPlanItem, build_plan, execute_plan
from prompt_benchmark.schema import Constraints

from test_prompt_client import FakeTransport, _config, _no_sleep, _success_body


def _case(case_id: str) -> Case:
    return Case(
        case_id=case_id,
        split="dev",
        document="Invoice INV-1 from Acme. Date: 2026-01-01. Total: USD 100.00.",
        expected={
            "invoice_id": "INV-1", "vendor": "Acme", "date": "2026-01-01",
            "total": "100.00", "currency": "USD",
        },
    )


class BuildPlanTests(unittest.TestCase):
    def test_plan_contains_every_case_variant_pair(self) -> None:
        cases = [_case("a"), _case("b")]
        plan = build_plan(cases, all_variants(), seed=1)
        pairs = {(item.case.case_id, item.variant.name) for item in plan}
        self.assertEqual(
            pairs, {("a", "baseline"), ("a", "candidate"), ("b", "baseline"), ("b", "candidate")}
        )
        self.assertEqual(len(plan), 4)

    def test_same_seed_is_deterministic(self) -> None:
        cases = [_case(str(i)) for i in range(10)]
        plan_a = build_plan(cases, all_variants(), seed=42)
        plan_b = build_plan(cases, all_variants(), seed=42)
        order_a = [(i.case.case_id, i.variant.name) for i in plan_a]
        order_b = [(i.case.case_id, i.variant.name) for i in plan_b]
        self.assertEqual(order_a, order_b)

    def test_shuffle_false_preserves_case_major_order(self) -> None:
        cases = [_case(str(i)) for i in range(5)]
        plan = build_plan(cases, [BASELINE_V1], seed=1, shuffle=False)
        self.assertEqual([item.case.case_id for item in plan], ["0", "1", "2", "3", "4"])


class ExecutePlanLimitTests(unittest.TestCase):
    """Reproduces and fixes: non-positive `limit` must not silently run
    the full plan (via `if limit:` truthiness on 0) nor an off-by-one
    subset (via Python's `plan[:-1]` negative-slice semantics)."""

    def _plan(self, n: int) -> list[RunPlanItem]:
        cases = [_case(str(i)) for i in range(n)]
        return build_plan(cases, [BASELINE_V1], seed=1, shuffle=False)

    def _client(self, n_responses: int) -> OpenRouterClient:
        transport = FakeTransport([_success_body() for _ in range(n_responses)])
        return OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)

    def test_limit_none_runs_everything(self) -> None:
        plan = self._plan(5)
        records = execute_plan(
            plan, self._client(5), _config(), experiment_id="e", run_id="r",
            dataset_version="v", limit=None,
        )
        self.assertEqual(len(records), 5)

    def test_limit_zero_runs_nothing(self) -> None:
        plan = self._plan(5)
        records = execute_plan(
            plan, self._client(0), _config(), experiment_id="e", run_id="r",
            dataset_version="v", limit=0,
        )
        self.assertEqual(records, [])

    def test_negative_limit_runs_nothing_not_almost_everything(self) -> None:
        plan = self._plan(5)
        records = execute_plan(
            plan, self._client(0), _config(), experiment_id="e", run_id="r",
            dataset_version="v", limit=-1,
        )
        self.assertEqual(records, [])

    def test_positive_limit_takes_first_n_in_plan_order(self) -> None:
        plan = self._plan(5)
        records = execute_plan(
            plan, self._client(2), _config(), experiment_id="e", run_id="r",
            dataset_version="v", limit=2,
        )
        self.assertEqual([r.case_id for r in records], ["0", "1"])


class RecordProvenanceTests(unittest.TestCase):
    def test_record_captures_case_variant_and_model_identity(self) -> None:
        plan = [RunPlanItem(case=_case("c1"), variant=CANDIDATE_V1)]
        transport = FakeTransport([_success_body(model="some-free-model/v1")])
        client = OpenRouterClient(_config(), transport=transport, sleep=_no_sleep)
        records = execute_plan(
            plan, client, _config(), experiment_id="exp", run_id="run1", dataset_version="v2",
        )
        record = records[0]
        self.assertEqual(record.case_id, "c1")
        self.assertEqual(record.variant_name, "candidate")
        self.assertEqual(record.variant_version, "v1")
        self.assertEqual(record.prompt_hash, CANDIDATE_V1.prompt_hash)
        self.assertEqual(record.requested_model, "openrouter/free")
        self.assertEqual(record.actual_model, "some-free-model/v1")
        self.assertEqual(record.experiment_id, "exp")
        self.assertEqual(record.run_id, "run1")


class AllRequestsFailTests(unittest.TestCase):
    """Phase-6 critical invariant: a run where every request fails at the
    transport layer must never produce a misleading ACCEPT decision."""

    def test_all_timeouts_never_yield_accept(self) -> None:
        cases = [_case(str(i)) for i in range(12)]
        variants = all_variants()
        plan = build_plan(cases, variants, seed=1)

        # Every attempt times out; max_retries=0 keeps this fast and finite.
        transport = FakeTransport([TransportTimeout("down")] * len(plan))
        client = OpenRouterClient(_config(max_retries=0), transport=transport, sleep=_no_sleep)

        records = execute_plan(
            plan, client, _config(), experiment_id="e", run_id="r", dataset_version="v",
        )
        self.assertEqual(len(records), len(plan))
        self.assertTrue(all(not r.success for r in records))
        self.assertTrue(all(not r.exact_match for r in records))

        baseline = [r for r in records if r.variant_name == "baseline"]
        candidate = [r for r in records if r.variant_name == "candidate"]
        baseline_summary = an.summarize_variant(baseline)
        candidate_summary = an.summarize_variant(candidate)
        paired = an.paired_exact_match_comparison(baseline, candidate, min_pairs=10)
        model_cmp = an.compare_model_distributions(baseline, candidate)
        decision = an.decide(baseline_summary, candidate_summary, paired, model_cmp, Constraints())

        self.assertEqual(baseline_summary.reliability.request_success_rate, 0.0)
        self.assertEqual(candidate_summary.quality.exact_match_rate, 0.0)
        self.assertNotEqual(decision.verdict, "accept")


if __name__ == "__main__":
    unittest.main()
