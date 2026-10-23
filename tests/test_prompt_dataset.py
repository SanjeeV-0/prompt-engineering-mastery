"""Tests for prompt_benchmark.dataset: loading and structural validation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from prompt_benchmark import dataset as ds


class LoadDatasetTests(unittest.TestCase):
    def _write(self, lines: list[str]) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        tmp.write("\n".join(lines))
        tmp.close()
        return Path(tmp.name)

    def test_loads_real_dataset_file(self) -> None:
        cases = ds.load_dataset(ds.default_dataset_path())
        self.assertGreater(len(cases), 20)
        self.assertTrue(any(c.split == "dev" for c in cases))
        self.assertTrue(any(c.split == "held_out" for c in cases))

    def test_real_dataset_is_structurally_valid(self) -> None:
        cases = ds.load_dataset(ds.default_dataset_path())
        report = ds.validate_dataset(cases)
        self.assertEqual(report.errors, [], msg=f"Unexpected errors: {report.errors}")

    def test_dev_and_held_out_filters(self) -> None:
        cases = ds.load_dataset(ds.default_dataset_path())
        dev = ds.dev_cases(cases)
        held = ds.held_out_cases(cases)
        self.assertEqual(len(dev) + len(held), len(cases))
        self.assertTrue(all(c.split == "dev" for c in dev))
        self.assertTrue(all(c.split == "held_out" for c in held))

    def test_malformed_json_line_raises(self) -> None:
        path = self._write(['{"case_id": "x", "split": "dev", "document": "d", not json'])
        with self.assertRaises(ValueError):
            ds.load_dataset(path)

    def test_non_object_line_raises(self) -> None:
        path = self._write(["[1, 2, 3]"])
        with self.assertRaises(ValueError):
            ds.load_dataset(path)

    def test_missing_case_id_raises(self) -> None:
        path = self._write(['{"split": "dev", "document": "d", "expected": {}}'])
        with self.assertRaises(ValueError):
            ds.load_dataset(path)

    def test_decoys_parsed_as_tuples(self) -> None:
        path = self._write(
            [
                '{"case_id": "c1", "split": "dev", "document": "d", '
                '"expected": {"invoice_id": "A", "vendor": null, "date": null, '
                '"total": null, "currency": null}, "decoys": {"invoice_id": ["PO-1"]}}'
            ]
        )
        cases = ds.load_dataset(path)
        self.assertEqual(cases[0].decoys["invoice_id"], ("PO-1",))

    def test_blank_lines_are_skipped(self) -> None:
        path = self._write(
            [
                "",
                '{"case_id": "c1", "split": "dev", "document": "d", '
                '"expected": {"invoice_id": null, "vendor": null, "date": null, '
                '"total": null, "currency": null}}',
                "   ",
            ]
        )
        cases = ds.load_dataset(path)
        self.assertEqual(len(cases), 1)


class ValidateDatasetTests(unittest.TestCase):
    def _case(self, **overrides) -> ds.Case:
        base = dict(
            case_id="c1",
            split="dev",
            document="doc",
            expected={"invoice_id": "A", "vendor": "V", "date": "2026-01-01", "total": "1.00", "currency": "USD"},
        )
        base.update(overrides)
        return ds.Case(**base)

    def test_valid_case_has_no_errors(self) -> None:
        report = ds.validate_dataset([self._case()])
        self.assertTrue(report.is_valid)

    def test_duplicate_case_id_is_an_error(self) -> None:
        report = ds.validate_dataset([self._case(), self._case()])
        self.assertFalse(report.is_valid)
        self.assertTrue(any("duplicate" in e.message for e in report.errors))

    def test_invalid_split_is_an_error(self) -> None:
        report = ds.validate_dataset([self._case(split="unknown_split")])
        self.assertFalse(report.is_valid)

    def test_missing_expected_field_is_an_error(self) -> None:
        case = self._case(expected={"invoice_id": "A", "vendor": "V", "date": None, "total": None})
        report = ds.validate_dataset([case])
        self.assertFalse(report.is_valid)
        self.assertTrue(any("missing fields" in e.message for e in report.errors))

    def test_non_string_expected_value_is_an_error(self) -> None:
        case = self._case(
            expected={"invoice_id": "A", "vendor": "V", "date": None, "total": 100, "currency": None}
        )
        report = ds.validate_dataset([case])
        self.assertFalse(report.is_valid)

    def test_invalid_date_format_is_an_error(self) -> None:
        case = self._case(
            expected={
                "invoice_id": "A", "vendor": "V", "date": "01/02/2026", "total": "1.00", "currency": "USD",
            }
        )
        report = ds.validate_dataset([case])
        self.assertFalse(report.is_valid)

    def test_invalid_currency_code_is_an_error(self) -> None:
        case = self._case(
            expected={"invoice_id": "A", "vendor": "V", "date": None, "total": "1.00", "currency": "us"}
        )
        report = ds.validate_dataset([case])
        self.assertFalse(report.is_valid)

    def test_empty_document_without_tag_warns(self) -> None:
        case = self._case(document="", tags=())
        report = ds.validate_dataset([case])
        self.assertTrue(report.is_valid)
        self.assertTrue(any("empty document" in w.message for w in report.warnings))

    def test_empty_document_with_tag_does_not_warn(self) -> None:
        case = self._case(document="", tags=("empty_input",))
        report = ds.validate_dataset([case])
        self.assertFalse(any("empty document" in w.message for w in report.warnings))

    def test_unexpected_extra_field_warns_not_errors(self) -> None:
        case = self._case(
            expected={
                "invoice_id": "A", "vendor": "V", "date": None, "total": "1.00",
                "currency": "USD", "extra": "x",
            }
        )
        report = ds.validate_dataset([case])
        self.assertTrue(report.is_valid)
        self.assertTrue(any("unexpected fields" in w.message for w in report.warnings))


if __name__ == "__main__":
    unittest.main()
