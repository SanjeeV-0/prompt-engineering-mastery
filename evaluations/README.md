# Evaluations

This directory documents the evaluation methodology used by the
experiments in `experiments/`. It does not duplicate code: the
deterministic evaluation engine itself lives in
`experiments/prompt_benchmark/evaluation.py` and `analysis.py`, and is
exercised directly by the test suite under `tests/`.

See also: [`06-evaluation/evaluation-fundamentals.md`](../06-evaluation/evaluation-fundamentals.md),
[`06-evaluation/metrics-and-test-datasets.md`](../06-evaluation/metrics-and-test-datasets.md),
and [`06-evaluation/robustness-testing.md`](../06-evaluation/robustness-testing.md) for the
underlying concepts this evaluation engine implements.

## What is evaluated

The invoice-extraction benchmark in `experiments/` evaluates a model
response along four independent dimensions, never collapsed into one
score:

1. **Parsing** — is the raw text a JSON object at all? (`ParseOutcome`:
   valid object, empty response, invalid JSON, non-object JSON, or no
   text available.)
2. **Contract compliance** — given a parsed JSON object, does it have
   exactly the required keys, string-typed values, a valid
   `YYYY-MM-DD` date, a 3-letter uppercase currency code, and a
   grouping-separator-free numeric total?
3. **Extraction quality** — strict field-level exact match (the
   primary metric), a secondary normalized/semantic match, per-field
   precision/recall/F1 (slot-filling definition), missing-value
   accuracy, hallucinated-value rate, and an authored-decoy-based
   unsupported-inference rate.
4. **Reliability** — request success rate, task-completion rate,
   retry/timeout rates, error-category frequencies, and a cautious
   heuristic refusal-like rate.

A response is never silently coerced into a pass. The strict,
contract-enforcing result is always reported alongside any normalized
secondary metric, never in place of it.

## Denominators matter

Every rate reported by `prompt_benchmark.analysis` states its
denominator:

- **End-to-end quality** (`VariantSummary.quality`) is computed over
  *all* requests, including transport failures and unparseable
  responses, which are scored as misses. This is the operationally
  honest number: a model that times out half the time does not get a
  high quality score just because its working half looks good.
- **Conditional quality** (`VariantSummary.quality_conditional`) is
  computed only over requests that completed the task (client
  success, valid JSON object, contract-valid). This isolates model
  *output* quality from *operational* reliability, which is reported
  separately under `VariantSummary.reliability`.

Both numbers are always shown together in the generated report so
neither can be used to hide the other.

## Why free-model routing changes what "evaluation" means here

OpenRouter's `openrouter/free` routing can serve a different
underlying model on every request. That means:

- A baseline-vs-candidate comparison is only a controlled experiment
  to the extent the two variants were served a comparable mix of
  models. `analysis.compare_model_distributions` computes the total
  variation distance between the baseline and candidate model-
  selection frequencies and flags the comparison as confounded when it
  diverges beyond a configurable threshold.
- Per-model breakdowns (`analysis.summarize_by_model`) let you check
  whether a quality difference is actually a *prompt* effect or a
  *which-model-answered* effect.
- A model that returns a safety refusal or an off-task response is not
  excluded from the denominator. It fails to parse as the expected
  JSON object and is scored as a miss, the same as any other failure
  to complete the task.

## Statistical honesty

`analysis.paired_exact_match_comparison` only compares cases evaluated
under both variants, averages repeated trials of the same case before
pairing (a case run three times is one data point, not three), and
reports a bootstrap 95% interval together with the sample size used.
Below a configurable minimum pair count, the comparison is marked
`sufficient_for_inference = False` and the accept/reject/inconclusive
decision in `analysis.decide` degrades to `"inconclusive"` rather than
forcing a verdict from too little evidence.

## Where results live

Evaluation is always run against the dataset in
`experiments/data/invoice_extraction.jsonl` (see
`experiments/README.md` for the dev/held-out split policy). Generated
per-run evidence (`*.jsonl` records, `*_manifest.json`, `*_report.md`)
is written to `experiments/results/`, which is excluded from version
control except for a placeholder — see the root `.gitignore`.
