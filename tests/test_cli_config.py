"""Tests for prompt_optimization_benchmark._effective_limit.

Confirms BENCHMARK_CASE_LIMIT (parsed into BenchmarkConfig.request_limit)
actually takes effect when --limit is not passed on the command line,
and that an explicit --limit always wins.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import prompt_optimization_benchmark as cli
from prompt_benchmark.config import BenchmarkConfig


def _config(request_limit: int | None) -> BenchmarkConfig:
    return BenchmarkConfig(api_key="k", request_limit=request_limit)


class EffectiveLimitTests(unittest.TestCase):
    def test_explicit_cli_limit_wins(self) -> None:
        args = argparse.Namespace(limit=5)
        self.assertEqual(cli._effective_limit(args, _config(request_limit=20)), 5)

    def test_falls_back_to_config_request_limit(self) -> None:
        args = argparse.Namespace(limit=None)
        self.assertEqual(cli._effective_limit(args, _config(request_limit=20)), 20)

    def test_none_when_neither_is_set(self) -> None:
        args = argparse.Namespace(limit=None)
        self.assertIsNone(cli._effective_limit(args, _config(request_limit=None)))

    def test_missing_limit_attribute_falls_back_to_config(self) -> None:
        args = argparse.Namespace()  # e.g. analyze/validate-dataset args have no --limit
        self.assertEqual(cli._effective_limit(args, _config(request_limit=7)), 7)


class ApplyOverridesTests(unittest.TestCase):
    """--concurrency 0 must still override (so validate_config rejects it),
    not be silently dropped by a truthiness check -- same bug class as
    the --limit 0 issue in _effective_limit."""

    def test_concurrency_zero_overrides_not_ignored(self) -> None:
        config = BenchmarkConfig(api_key="k", concurrency=1)
        args = argparse.Namespace(concurrency=0)
        result = cli._apply_overrides(config, args)
        self.assertEqual(result.concurrency, 0)

    def test_concurrency_negative_overrides(self) -> None:
        config = BenchmarkConfig(api_key="k", concurrency=1)
        args = argparse.Namespace(concurrency=-3)
        result = cli._apply_overrides(config, args)
        self.assertEqual(result.concurrency, -3)

    def test_concurrency_none_keeps_existing_config(self) -> None:
        config = BenchmarkConfig(api_key="k", concurrency=5)
        args = argparse.Namespace(concurrency=None)
        result = cli._apply_overrides(config, args)
        self.assertEqual(result.concurrency, 5)

    def test_missing_concurrency_attribute_keeps_existing_config(self) -> None:
        config = BenchmarkConfig(api_key="k", concurrency=5)
        args = argparse.Namespace()
        result = cli._apply_overrides(config, args)
        self.assertEqual(result.concurrency, 5)


class LimitProblemsTests(unittest.TestCase):
    """--limit 0 or negative must fail clearly before any API call, not
    silently run the full plan (0 is falsy) or an off-by-one subset
    (Python's plan[:-1] slicing) -- see runner.execute_plan's docstring."""

    def test_none_is_fine(self) -> None:
        self.assertEqual(cli._limit_problems(None), [])

    def test_positive_is_fine(self) -> None:
        self.assertEqual(cli._limit_problems(5), [])

    def test_zero_is_rejected(self) -> None:
        problems = cli._limit_problems(0)
        self.assertEqual(len(problems), 1)
        self.assertIn("positive integer", problems[0])

    def test_negative_is_rejected(self) -> None:
        problems = cli._limit_problems(-3)
        self.assertEqual(len(problems), 1)
        self.assertIn("-3", problems[0])


if __name__ == "__main__":
    unittest.main()
