"""Tests for prompt_benchmark.evaluation: deterministic scoring."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark import evaluation as ev

EXPECTED = {
    "invoice_id": "INV-1",
    "vendor": "Acme",
    "date": "2026-01-01",
    "total": "100.00",
    "currency": "USD",
}


def _text(**fields) -> str:
    return json.dumps(fields)


class ParseResponseTests(unittest.TestCase):
    def test_none_text_is_unsupported_shape(self) -> None:
        outcome, parsed = ev.parse_response(None)
        self.assertEqual(outcome, ev.ParseOutcome.UNSUPPORTED_SHAPE)
        self.assertIsNone(parsed)

    def test_empty_string_is_empty_response(self) -> None:
        outcome, _ = ev.parse_response("   ")
        self.assertEqual(outcome, ev.ParseOutcome.EMPTY_RESPONSE)

    def test_invalid_json_is_invalid_json(self) -> None:
        outcome, _ = ev.parse_response("{not valid json")
        self.assertEqual(outcome, ev.ParseOutcome.INVALID_JSON)

    def test_json_array_is_non_json_response(self) -> None:
        outcome, _ = ev.parse_response("[1, 2, 3]")
        self.assertEqual(outcome, ev.ParseOutcome.NON_JSON_RESPONSE)

    def test_json_string_is_non_json_response(self) -> None:
        outcome, _ = ev.parse_response('"just a string"')
        self.assertEqual(outcome, ev.ParseOutcome.NON_JSON_RESPONSE)

    def test_valid_object_parses(self) -> None:
        outcome, parsed = ev.parse_response('{"a": 1}')
        self.assertEqual(outcome, ev.ParseOutcome.VALID_JSON_OBJECT)
        self.assertEqual(parsed, {"a": 1})


class EvaluateContractTests(unittest.TestCase):
    def test_fully_compliant_object_is_valid(self) -> None:
        parsed = dict(EXPECTED)
        report = ev.evaluate_contract(parsed)
        self.assertTrue(report.contract_valid)

    def test_missing_keys_detected(self) -> None:
        parsed = {"invoice_id": "X"}
        report = ev.evaluate_contract(parsed)
        self.assertFalse(report.contract_valid)
        self.assertIn("vendor", report.missing_keys)

    def test_unexpected_keys_detected(self) -> None:
        parsed = dict(EXPECTED)
        parsed["notes"] = "extra"
        report = ev.evaluate_contract(parsed)
        self.assertFalse(report.contract_valid)
        self.assertIn("notes", report.unexpected_keys)

    def test_wrong_type_is_type_violation_not_format_violation(self) -> None:
        parsed = dict(EXPECTED)
        parsed["total"] = 100.0  # numeric total instead of string
        report = ev.evaluate_contract(parsed)
        self.assertFalse(report.contract_valid)
        self.assertEqual(report.type_violations.get("total"), "float")
        self.assertNotIn("total", report.invalid_total_fields)

    def test_invalid_date_format_detected(self) -> None:
        parsed = dict(EXPECTED)
        parsed["date"] = "01/02/2026"
        report = ev.evaluate_contract(parsed)
        self.assertIn("date", report.invalid_date_fields)

    def test_invalid_currency_format_detected(self) -> None:
        parsed = dict(EXPECTED)
        parsed["currency"] = "us"
        report = ev.evaluate_contract(parsed)
        self.assertIn("currency", report.invalid_currency_fields)

    def test_invalid_total_with_grouping_separator_detected(self) -> None:
        parsed = dict(EXPECTED)
        parsed["total"] = "1,000.00"
        report = ev.evaluate_contract(parsed)
        self.assertIn("total", report.invalid_total_fields)

    def test_null_values_are_not_format_violations(self) -> None:
        parsed = dict(EXPECTED)
        parsed["date"] = None
        parsed["currency"] = None
        report = ev.evaluate_contract(parsed)
        self.assertNotIn("date", report.invalid_date_fields)
        self.assertNotIn("currency", report.invalid_currency_fields)


class EvaluateRecordTests(unittest.TestCase):
    def test_exact_match_on_correct_json(self) -> None:
        result = ev.evaluate_record(_text(**EXPECTED), EXPECTED)
        self.assertTrue(result.exact_match)
        self.assertEqual(result.field_accuracy, 1.0)
        self.assertEqual(result.parse_outcome, ev.ParseOutcome.VALID_JSON_OBJECT)

    def test_invalid_json_scores_every_field_as_incorrect(self) -> None:
        result = ev.evaluate_record("not json at all", EXPECTED)
        self.assertFalse(result.exact_match)
        self.assertEqual(result.field_accuracy, 0.0)
        for outcome in result.field_outcomes.values():
            self.assertFalse(outcome.strict_match)

    def test_empty_response_scores_every_field_as_incorrect(self) -> None:
        result = ev.evaluate_record("", EXPECTED)
        self.assertFalse(result.exact_match)
        self.assertEqual(result.field_accuracy, 0.0)

    def test_missing_keys_do_not_silently_pass(self) -> None:
        result = ev.evaluate_record(_text(invoice_id="INV-1"), EXPECTED)
        self.assertFalse(result.exact_match)
        self.assertFalse(result.contract.contract_valid)

    def test_unexpected_keys_fail_contract_even_if_fields_match(self) -> None:
        payload = dict(EXPECTED)
        payload["extra_field"] = "oops"
        result = ev.evaluate_record(json.dumps(payload), EXPECTED)
        self.assertFalse(result.contract.contract_valid)
        self.assertFalse(result.exact_match)

    def test_numeric_total_fails_strict_match_even_though_value_is_right(self) -> None:
        payload = dict(EXPECTED)
        payload["total"] = 100.00  # number, not string
        result = ev.evaluate_record(json.dumps(payload), EXPECTED)
        self.assertFalse(result.field_outcomes["total"].strict_match)
        self.assertFalse(result.exact_match)

    def test_missing_expected_field_scored_correctly_when_both_null(self) -> None:
        expected = dict(EXPECTED)
        expected["date"] = None
        result = ev.evaluate_record(_text(**{**EXPECTED, "date": None}), expected)
        self.assertTrue(result.field_outcomes["date"].strict_match)

    def test_hallucination_flagged_when_expected_null(self) -> None:
        expected = dict(EXPECTED)
        expected["currency"] = None
        result = ev.evaluate_record(_text(**{**EXPECTED, "currency": "USD"}), expected)
        self.assertTrue(result.field_outcomes["currency"].hallucinated)
        self.assertFalse(result.field_outcomes["currency"].strict_match)

    def test_missing_flagged_when_expected_value_present(self) -> None:
        result = ev.evaluate_record(_text(**{**EXPECTED, "vendor": None}), EXPECTED)
        self.assertTrue(result.field_outcomes["vendor"].missing)

    def test_decoy_selection_detected(self) -> None:
        decoys = {"invoice_id": ("PO-999",)}
        result = ev.evaluate_record(
            _text(**{**EXPECTED, "invoice_id": "PO-999"}), EXPECTED, decoys
        )
        self.assertTrue(result.field_outcomes["invoice_id"].decoy_selected)

    def test_decoy_not_selected_is_false_not_none(self) -> None:
        decoys = {"invoice_id": ("PO-999",)}
        result = ev.evaluate_record(_text(**EXPECTED), EXPECTED, decoys)
        self.assertFalse(result.field_outcomes["invoice_id"].decoy_selected)

    def test_decoy_field_without_label_is_none(self) -> None:
        result = ev.evaluate_record(_text(**EXPECTED), EXPECTED, {})
        self.assertIsNone(result.field_outcomes["invoice_id"].decoy_selected)

    def test_semantic_match_normalizes_total_formatting_but_strict_still_fails(self) -> None:
        payload = dict(EXPECTED)
        payload["total"] = "100.0"  # same value, different formatting
        result = ev.evaluate_record(json.dumps(payload), EXPECTED)
        self.assertFalse(result.field_outcomes["total"].strict_match)
        self.assertTrue(result.field_outcomes["total"].semantic_match)
        self.assertFalse(result.exact_match)
        self.assertTrue(result.semantic_exact_match)

    def test_safety_classification_text_is_not_treated_as_valid_data(self) -> None:
        refusal = "I'm sorry, but I can't help with that request."
        result = ev.evaluate_record(refusal, EXPECTED)
        self.assertEqual(result.parse_outcome, ev.ParseOutcome.INVALID_JSON)
        self.assertFalse(result.exact_match)
        self.assertEqual(result.field_accuracy, 0.0)


if __name__ == "__main__":
    unittest.main()
