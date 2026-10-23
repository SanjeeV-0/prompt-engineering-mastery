"""Tests for prompt_benchmark.reporting: atomic I/O, redaction, round-tripping."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark import reporting as rpt
from prompt_benchmark.analysis import (
    compare_model_distributions,
    decide,
    paired_exact_match_comparison,
    summarize_variant,
)
from prompt_benchmark.schema import SCHEMA_VERSION, Constraints, RequestRecord, RunManifest, redact, utc_now_iso

from test_prompt_analysis import make_record


class RedactionTests(unittest.TestCase):
    def test_api_key_like_field_is_redacted(self) -> None:
        data = {"api_key": "sk-abc123", "other": "fine"}
        result = redact(data)
        self.assertEqual(result["api_key"], "<redacted>")
        self.assertEqual(result["other"], "fine")

    def test_token_count_fields_are_not_redacted(self) -> None:
        data = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        result = redact(data)
        self.assertEqual(result, data)

    def test_nested_secret_is_redacted(self) -> None:
        data = {"headers": {"Authorization": "Bearer xyz"}}
        result = redact(data)
        self.assertEqual(result["headers"]["Authorization"], "<redacted>")

    def test_list_of_dicts_is_redacted(self) -> None:
        data = [{"secret": "x"}, {"fine": "y"}]
        result = redact(data)
        self.assertEqual(result[0]["secret"], "<redacted>")
        self.assertEqual(result[1]["fine"], "y")


class AtomicWriteTests(unittest.TestCase):
    def test_write_json_atomic_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            rpt.write_json_atomic(path, {"a": 1})
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text()), {"a": 1})

    def test_write_json_atomic_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            rpt.write_json_atomic(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                rpt.write_json_atomic(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})

    def test_write_json_atomic_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            rpt.write_json_atomic(path, {"api_key": "sk-123"})
            self.assertEqual(json.loads(path.read_text())["api_key"], "<redacted>")

    def test_write_jsonl_atomic_round_trips_records(self) -> None:
        records = [make_record(case_id="a"), make_record(case_id="b")]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            rpt.write_jsonl_atomic(path, records)
            loaded = rpt.load_records_jsonl(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].case_id, "a")
            self.assertIsInstance(loaded[0], RequestRecord)

    def test_write_jsonl_atomic_refuses_to_overwrite(self) -> None:
        records = [make_record()]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            rpt.write_jsonl_atomic(path, records)
            with self.assertRaises(FileExistsError):
                rpt.write_jsonl_atomic(path, records)

    def test_write_text_atomic_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            rpt.write_text_atomic(path, "hello")
            with self.assertRaises(FileExistsError):
                rpt.write_text_atomic(path, "world")
            self.assertEqual(path.read_text(), "hello")


class MarkdownReportTests(unittest.TestCase):
    def test_report_contains_all_required_sections(self) -> None:
        baseline = [make_record(case_id=str(i), actual_model="m1", exact_match=False) for i in range(12)]
        candidate = [make_record(case_id=str(i), actual_model="m1", exact_match=True) for i in range(12)]

        baseline_summary = summarize_variant(baseline)
        candidate_summary = summarize_variant(candidate)
        constraints = Constraints()
        paired = paired_exact_match_comparison(baseline, candidate, min_pairs=constraints.min_pairs_for_decision)
        model_cmp = compare_model_distributions(baseline, candidate)
        decision = decide(baseline_summary, candidate_summary, paired, model_cmp, constraints)

        manifest = RunManifest(
            experiment_id="exp-1",
            run_id="run-1",
            created_utc=utc_now_iso(),
            research_question="Does the candidate improve quality?",
            hypothesis="Yes, via clearer rules.",
            primary_metric="exact_match_rate",
            secondary_metrics=["mean_field_accuracy"],
            baseline_variant="baseline:v1",
            candidate_variant="candidate:v1",
            dataset_version="invoice-extraction-v2",
            dataset_split="dev",
            requested_model="openrouter/free",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.0,
            trial_count=1,
            constraints=constraints,
            limitations=["Small synthetic dataset."],
        )

        report = rpt.build_markdown_report(
            manifest, baseline_summary, candidate_summary, paired, model_cmp, decision,
            dataset_warnings=[], next_experiment="Run held-out evaluation next.",
        )

        for heading in [
            "## 1. Objective and Hypothesis",
            "## 2. Configuration and Dataset",
            "## 3. Prompt Versions",
            "## 4. Aggregate and Per-Model Metrics",
            "## 5. Failure Analysis",
            "## 6. Cost and Latency",
            "## 7. Uncertainty and Limitations",
            "## 8. Acceptance Decision",
            "## 9. Recommended Next Experiment",
        ]:
            self.assertIn(heading, report)

        self.assertIn("ACCEPT", report)

    def test_report_text_never_contains_literal_api_key_marker(self) -> None:
        # The report is built from summaries/manifests which never carry a
        # raw API key, so a defensive scan should find nothing to redact.
        baseline = [make_record(case_id="a")]
        candidate = [make_record(case_id="a")]
        baseline_summary = summarize_variant(baseline)
        candidate_summary = summarize_variant(candidate)
        constraints = Constraints()
        paired = paired_exact_match_comparison(baseline, candidate, min_pairs=1)
        model_cmp = compare_model_distributions(baseline, candidate)
        decision = decide(baseline_summary, candidate_summary, paired, model_cmp, constraints)
        manifest = RunManifest(
            experiment_id="exp-1", run_id="run-1", created_utc=utc_now_iso(),
            research_question="q", hypothesis="h", primary_metric="m",
            secondary_metrics=[], baseline_variant="baseline:v1", candidate_variant="candidate:v1",
            dataset_version="v2", dataset_split="dev", requested_model="openrouter/free",
            base_url="https://openrouter.ai/api/v1", temperature=0.0, trial_count=1,
            constraints=constraints, limitations=[],
        )
        report = rpt.build_markdown_report(
            manifest, baseline_summary, candidate_summary, paired, model_cmp, decision, [], "next"
        )
        self.assertNotIn("sk-", report)
        self.assertNotIn("Bearer ", report)


if __name__ == "__main__":
    unittest.main()
