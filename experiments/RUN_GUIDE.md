# Run Guide: Invoice-Extraction Prompt Benchmark

A step-by-step guide for a new engineer to install, configure, run, and
interpret the prompt-optimization benchmark in this directory, starting
from a fresh clone of the repository.

For configuration details (every environment variable, CLI flag, and
code-level setting), see [`CONFIGURATION.md`](CONFIGURATION.md). For
the experimental methodology this tool implements, see
[`README.md`](README.md) and [`../evaluations/README.md`](../evaluations/README.md).

Every command below was run against the actual implementation in this
repository and verified to work, including one real OpenRouter smoke
test and one real `benchmark-dev` run (see §13, "Verified example
output").

## 1. Purpose and architecture

The benchmark measures whether a **candidate** prompt improves invoice-
field extraction (`invoice_id`, `vendor`, `date`, `total`, `currency`)
over a **baseline** prompt, on a small labeled dataset, served through
OpenRouter's free-model router. It produces auditable per-request
records, a run manifest, and a markdown report with an explicit
accept/reject/inconclusive decision — not just an aggregate score.

```text
experiments/
  prompt_optimization_benchmark.py   CLI entry point (this is what you run)
  prompt_benchmark/                  the package it imports
    config.py       environment variables -> BenchmarkConfig
    prompts.py      the baseline/candidate prompt templates
    dataset.py      dataset loading + structural validation
    evaluation.py   scores one response against one expected record
    client.py       talks to OpenRouter (or a fake transport in tests)
    schema.py       RequestRecord / RunManifest, secret redaction
    runner.py       runs a (case, variant) plan through client + evaluator
    analysis.py     aggregates records into metrics and a decision
    reporting.py    writes the *.jsonl / *_manifest.json / *_report.md files
  data/invoice_extraction.jsonl      the dataset (18 dev + 14 held_out cases)
  results/                          where every run's output lands (gitignored)
tests/                              offline unit tests (no network)
```

There are **no external dependencies**. Everything is Python 3.12
standard library (`urllib`, `json`, `argparse`, `dataclasses`,
`concurrent.futures`, `unittest`).

## 2. Prerequisites

- Python 3.12 (this repository was built and tested against 3.12.10;
  `python --version` to confirm). No virtual environment or package
  manager is required.
- An OpenRouter account and API key, **only** if you intend to run
  `smoke-test`, `benchmark-dev`, or `benchmark-held-out` against the
  real API. `check-config`, `validate-dataset`, `analyze`, and the
  offline test suite need no key and no network access.

## 3. Environment setup (Windows PowerShell)

From the repository root:

```powershell
python --version
```

Confirm it reports `Python 3.12.x`. If `python` resolves to something
else on your system, use `py -3.12` in place of `python` below.

## 4. Dependency installation

There is no `requirements.txt`, `pyproject.toml`, or virtual
environment to set up — the package uses only the standard library.
Nothing to install beyond Python itself.

## 5. Configure your OpenRouter API key safely

Never hard-code the key in a file that gets committed. Set it as an
environment variable for the current PowerShell session:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-...your-key..."
```

This value lives only in your shell session; it is not written to
disk, and the framework never prints, logs, or serializes it (verified
by `tests/test_prompt_client.py::SuccessPathTests::test_api_key_never_appears_in_result`
and `tests/test_prompt_reporting.py::RedactionTests`). To persist it
across sessions without committing it anywhere, set it in your user
environment variables (Windows Settings → Environment Variables), not
in a tracked file. If you keep a local `.env`-style file for your own
convenience, the root `.gitignore` already excludes `.env` and `.env.*`.

## 6. Verify configuration without exposing the key

```powershell
python experiments/prompt_optimization_benchmark.py check-config
```

This prints the resolved model, base URL, timeout, retry count,
concurrency, and **only a boolean** `API key present: True/False` — the
key itself is never printed. It makes zero network calls. Example
output:

```text
Model: openrouter/free
Base URL: https://openrouter.ai/api/v1
Timeout: 60.0s  Max retries: 3  Concurrency: 1
API key present: True
Configuration looks usable.
```

To check the configuration shape without having a key set yet (e.g. in
CI), add `--allow-missing-key`.

## 7. Validate the dataset

Also makes no network calls:

```powershell
python experiments/prompt_optimization_benchmark.py validate-dataset
```

Expected output against the shipped dataset:

```text
Loaded 32 cases from <repo>\experiments\data\invoice_extraction.jsonl
  dev: 18  held_out: 14
Dataset is structurally valid.
```

Run this after editing `data/invoice_extraction.jsonl` and before
spending any API requests against it.

## 8. Run the offline test suite

No API key or network access needed:

```powershell
python -m unittest discover -s tests -v
```

This repository's suite currently contains 104 tests across dataset
validation, deterministic evaluation, the client's retry/failure
handling (via a fake transport — no real HTTP), aggregation/analysis,
atomic-write/redaction behavior, and the CLI's `--limit` resolution
logic. Expected result: `OK`.

## 9. Run a minimal smoke test

```powershell
python experiments/prompt_optimization_benchmark.py smoke-test --limit 2
```

This is a **pipeline connectivity check, not evidence of prompt
quality** — the CLI prints that explicitly, and with only 2 cases the
decision will correctly come back `INCONCLUSIVE` every time (the
framework refuses to call 2 paired cases a confirmatory result). Use
it to confirm your API key and network access work before running a
real benchmark. `--limit 2` here caps the dev subset used for the
smoke test, not the overall request plan (see
[`CONFIGURATION.md`](CONFIGURATION.md) for the distinction between how
`--limit` behaves on `smoke-test` versus `benchmark-dev`/`benchmark-held-out`).

The subset is always the **first N `dev` cases in dataset file order**
(not a random sample) — with the default `--limit 2` against the
shipped dataset, that is `dev_001` and `dev_002`, both tagged
`happy_path` / difficulty `easy`. A repeated `PASS` on the smoke test
confirms connectivity, not robustness: it does not exercise any of the
dataset's decoy, ambiguous-date, prompt-injection, or malformed-input
cases. Use `benchmark-dev` (which shuffles across the full difficulty
range before any `--limit` is applied) for anything resembling a
quality signal.

## 10. Run the development benchmark

```powershell
python experiments/prompt_optimization_benchmark.py benchmark-dev
```

This runs **both** the baseline and candidate prompt against all 18
`dev` cases (36 requests total, in a seeded, shuffled, balanced order
between variants), scores every response, and writes three files to
`experiments/results/`. This is where prompt iteration happens — only
ever compare candidates on `dev`.

## 11. Run held-out evaluation (do this only once a candidate is chosen)

```powershell
python experiments/prompt_optimization_benchmark.py benchmark-held-out
```

The CLI prints a warning banner before running:

```text
HELD-OUT EVALUATION: this split must not be used to choose between prompt
revisions. Run it only to confirm a candidate already selected on
development data.
```

**Do not** iterate on the prompt based on held-out results and re-run
this command. If you do, `held_out` has effectively become development
data and its generalization estimate is no longer trustworthy — the
same principle the dataset's own `ANNOTATION_ASSUMPTIONS` and
`evaluations/README.md` describe for dev/held-out separation.

## 12. Analyze a saved run without making new API requests

```powershell
python experiments/prompt_optimization_benchmark.py analyze --records experiments/results/dev_20261023T125647Z.jsonl
```

Recomputes the full aggregation and regenerates a markdown report
(`<records-file-stem>_reanalysis_report.md`, next to the input file by
default, or under `--output <dir>`) purely from the saved `*.jsonl`
records. Useful for re-deriving metrics after a change to
`analysis.py`'s scoring logic, without spending further API requests.
Replace the filename above with whatever run you actually have in
`experiments/results/`.

## 13. Verified example output (real run, not fabricated)

A real `benchmark-dev` run was executed against the live OpenRouter API
on 2026-10-23 (run id `dev_20261023T125647Z`) as part of validating
this framework. Selected results, taken directly from the generated
report:

```text
Decision: ACCEPT
  - Candidate improves paired exact_match by 0.5556
    (95% CI [0.3333, 0.7778]), with no constraint violated.

Exact match rate (all requests): baseline 0.1111, candidate 0.6667
Model distribution divergence (TVD): 0.2222 (comparable; not confounded)
```

This single run is illustrative, not a permanent claim about the
candidate prompt's superiority — free-model routing selected nine
different underlying models across just 36 requests in this run (see
the report's "Model selection frequencies" section), and 18 dev cases
is a small sample. Re-running will very likely select a different mix
of models and produce different numbers.

## 14. Where output files are written

Every run that calls the API writes exactly three files to
`experiments/results/` (or the directory passed via `--output`), and
**never overwrites an existing run** — `reporting.write_*_atomic`
raises `FileExistsError` rather than clobbering a prior result:

| File | Contents |
|---|---|
| `<run_id>.jsonl` | One fully auditable JSON record per request: case, variant, prompt hash, requested/actual model, retries, latency, token usage, provider cost, raw response text, parsed JSON, every evaluation outcome. Secrets are redacted (there are none to redact here in practice, since the API key is never put into a record). |
| `<run_id>_manifest.json` | The experiment protocol: research question, hypothesis, primary/secondary metrics, prompt/dataset versions, constraints, and documented limitations. |
| `<run_id>_report.md` | The human-readable report: 9 sections from objective through recommended next experiment, ending in an explicit verdict. |

`<run_id>` is `<tag>_<UTC timestamp>`, e.g. `dev_20261023T125647Z`,
`held_out_20261023T...`, `smoke_20261023T...`. `analyze` additionally
writes `<input-stem>_reanalysis_report.md`.

Console output during a run (`[variant] case_id: PASS/MISMATCH/ERROR;
model=...`) is printed to stdout only; the framework does not write a
separate log file.

## 15. Interpreting the resulting metrics

Read [`../evaluations/README.md`](../evaluations/README.md) for full
metric definitions and denominators. The short version:

- **`exact_match_rate` (all requests)** is the primary, end-to-end
  metric: every request counts, including transport failures and
  unparseable responses, scored as misses.
- **`exact_match_rate` (completed requests only)** is a secondary,
  conditional view restricted to requests that actually produced a
  contract-valid JSON object — it isolates model *output* quality from
  *operational* reliability, which is reported separately
  (`task_completion_rate`, `request_success_rate`).
- **Model distribution divergence (TVD)**: if this exceeds the
  configured threshold (default 0.35), the decision is forced to
  `inconclusive` regardless of the quality numbers, because the
  baseline and candidate may simply have been served different models.
- **Paired exact-match bootstrap CI**: only case IDs scored under both
  variants are compared, repeated trials of the same case are averaged
  first, and the comparison is marked insufficient below
  `--min-pairs` (default 10) — in which case the verdict is
  `inconclusive`, not a forced winner.
- **`ACCEPT` / `REJECT` / `INCONCLUSIVE`** come with explicit, printed
  reasons (`analysis.decide`) — read the reasons, not just the verdict.

## 16. Common errors and troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `check-config` reports `OPENROUTER_API_KEY is not set.` | Env var not set in this shell session | `$env:OPENROUTER_API_KEY = "..."`, then re-run in the *same* PowerShell window |
| `benchmark-dev`/`held-out` exits 2 with "Cannot run benchmark" | `check-config`-equivalent validation failed | Run `check-config` first and fix every listed problem |
| `validate-dataset` exits 1 listing errors | A dataset record is malformed (duplicate ID, bad split, invalid date/currency format, etc.) | Fix the listed `case_id`s in `data/invoice_extraction.jsonl`, re-validate |
| `FileExistsError: Refusing to overwrite existing result file` | You re-ran a command fast enough to generate the same `run_id` (same UTC second), or pointed `--output` at a directory with a same-named file | Wait a second and re-run, or pass a different `--output` directory |
| A request shows `failure_category: rate_limited` in the `.jsonl` after exhausting retries | Free-tier rate limiting; `OPENROUTER_MAX_RETRIES` (default 3) exhausted | Lower `BENCHMARK_CONCURRENCY` (default is already `1`), increase `OPENROUTER_MAX_RETRIES`/`OPENROUTER_RETRY_MAX_DELAY_S`, or simply re-run later |
| Model selection looks wildly different between baseline and candidate | Expected behavior of `openrouter/free` | Check the report's TVD; if it diverges, treat the run as inconclusive rather than re-running until it looks better |
| `python: command not found` / wrong Python version | PATH points at a different interpreter | Use `py -3.12 experiments/prompt_optimization_benchmark.py ...` |

## 17. Cleaning up local generated artifacts safely

`experiments/results/*` is excluded from version control (see
`.gitignore`) except for a `.gitkeep` placeholder, so these files are
always safe to delete locally — they are regenerated on every run and
never committed:

```powershell
Remove-Item experiments/results/*.jsonl, experiments/results/*_manifest.json, experiments/results/*_report.md
```

Do **not** delete a result file without first opening it if you are
unsure whether it represents a run someone else cares about (e.g. a
teammate's held-out confirmation run) — per this repository's standing
practice, inspect before deleting. Python bytecode caches
(`experiments/**/__pycache__/`, `tests/__pycache__/`) are also
gitignored and safe to delete at any time:

```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

## 18. Security and repository hygiene notes

- The API key must be an environment variable (§5) — there is no
  config-file or CLI-flag mechanism for it, by design, so it cannot
  accidentally end up in a tracked file or shell history as a literal
  argument.
- Generated `*.jsonl` records contain **raw document text and raw
  model output** (`raw_response_text`, `parsed`, `expected`). The
  shipped dataset is synthetic and safe to share, but if you add real
  invoice data to `data/invoice_extraction.jsonl` for local testing,
  review `experiments/results/*.jsonl` before sharing it — it will
  contain that data verbatim in every per-request record.
- Never commit `experiments/results/*` (already gitignored) or paste
  its contents somewhere public without reviewing for anything
  sensitive first.
- Held-out labels exist only to confirm a prompt already chosen on
  `dev` — see §11. There is no code-level gate preventing you from
  running `benchmark-held-out` repeatedly; the discipline is a
  methodology requirement, not an enforced one.

## 19. Further reading

- [`CONFIGURATION.md`](CONFIGURATION.md) — every environment variable,
  CLI flag, and code-level setting, with defaults and reproducibility
  notes.
- [`README.md`](README.md) — experimental methodology, dataset/split
  policy, and how to interpret results responsibly.
- [`../evaluations/README.md`](../evaluations/README.md) — metric
  definitions and why free-model routing complicates causal claims.
