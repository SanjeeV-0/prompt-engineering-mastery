# Configuration Reference

Every setting that actually exists in `experiments/prompt_benchmark/`
and `experiments/prompt_optimization_benchmark.py`, verified against
the implementation (not aspirational). See
[`RUN_GUIDE.md`](RUN_GUIDE.md) for a task-oriented walkthrough of using
these settings.

Settings are grouped into three tiers, per how they're actually
controlled:

- **Environment configuration** — read once per process by
  `prompt_benchmark.config.load_config_from_env()` (`config.py`).
- **CLI configuration** — `argparse` options on
  `prompt_optimization_benchmark.py`, some of which override an
  environment value for that invocation.
- **Code-level configuration** — values that currently require editing
  a source file; there is no environment variable or flag for them.

## 1. Environment configuration

All of these are read by `load_config_from_env()` into a
`BenchmarkConfig`. Unset or empty values fall back to the default
silently (an unparseable numeric value also falls back to the
default — it is not rejected until `validate_config` runs).

| Variable | Type | Default | Required | Effect |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | string | *(none)* | Yes, for any live request | Bearer token sent as `Authorization: Bearer <key>`. Never printed, logged, or included in any `.jsonl`/`.json`/`.md` artifact (`schema.redact` strips any key containing `api_key`, `authorization`, `secret`, `password`, or `bearer`; the client additionally scrubs the literal key value out of any error message). `check-config` reports only `bool(api_key)`. |
| `OPENROUTER_MODEL` | string | `openrouter/free` | No | The **requested** model. With free routing, the **actual** model that serves each request can differ and is recorded per-request (`actual_model`); changing this away from `openrouter/free` to a specific paid model changes what you are measuring and is not comparable to a free-routed run. |
| `OPENROUTER_BASE_URL` | string (URL) | `https://openrouter.ai/api/v1` | No | API base URL; trailing slash is stripped. Must start with `http://` or `https://` or `check-config`/any run command reports it invalid. |
| `OPENROUTER_TIMEOUT_S` | float, seconds | `60.0` | No | Per-request socket timeout passed to `urllib.request.urlopen`. Must be `> 0`. |
| `OPENROUTER_MAX_RETRIES` | int | `3` | No | Maximum retry attempts for **transient** failures only: request timeout, connection error, HTTP 429 (rate limited), HTTP 5xx. HTTP 4xx other than 429 (e.g. 401, 400) is never retried. Must be `>= 0`; `0` disables retries entirely. |
| `OPENROUTER_RETRY_BASE_DELAY_S` | float, seconds | `1.0` | No | Base delay for exponential backoff: `base * 2^(retry_number-1)`, capped at `retry_max_delay_s`, plus up to 25% random jitter. When the provider sends a `Retry-After` header, that value is used instead (still capped at `retry_max_delay_s`). |
| `OPENROUTER_RETRY_MAX_DELAY_S` | float, seconds | `20.0` | No | Upper bound on any single backoff delay. Must be `>= OPENROUTER_RETRY_BASE_DELAY_S`. |
| `BENCHMARK_CONCURRENCY` | int | `1` | No | Worker threads (`concurrent.futures.ThreadPoolExecutor`) used to issue requests. `1` runs strictly sequentially (the common case against a free-tier rate limit). Must be `>= 1`. Can be overridden per-invocation with `--concurrency` on `smoke-test`/`benchmark-dev`/`benchmark-held-out`. |
| `BENCHMARK_TEMPERATURE` | float | `0.0` | No | Sampling temperature sent in every request payload. Validated to lie within `[0.0, 2.0]`. Changing this changes model behavior and invalidates direct comparison with a run at a different temperature. |
| `BENCHMARK_CASE_LIMIT` | positive int | *(none — no limit)* | No | Fallback value for the request-plan cap when `--limit` is **not** passed on `benchmark-dev`/`benchmark-held-out` (see `_effective_limit` in the CLI). An explicit `--limit` always takes precedence over this variable. Non-positive or non-digit values are ignored (treated as unset). |

### Example: safe configuration

```powershell
$env:OPENROUTER_API_KEY = "sk-or-...your-key..."     # required, never printed
$env:OPENROUTER_MODEL = "openrouter/free"              # default; explicit here for clarity
$env:OPENROUTER_MAX_RETRIES = "5"                      # more tolerant of a flaky free endpoint
$env:BENCHMARK_CONCURRENCY = "1"                       # stay sequential against free-tier limits
python experiments/prompt_optimization_benchmark.py check-config
```

### Validation

`prompt_benchmark.config.validate_config(config, require_api_key=...)`
checks every one of the above (except the key's own value) and returns
a list of human-readable problems — empty means usable. It is called
automatically by `check-config`, `smoke-test`, `benchmark-dev`, and
`benchmark-held-out` before any request is sent; a non-empty problem
list causes those commands to exit without calling the API (exit code
`1` for `check-config`, `2` for the run commands).

## 2. CLI configuration

Exposed by `argparse` in `prompt_optimization_benchmark.py`. Run `python
experiments/prompt_optimization_benchmark.py <command> --help` for the
authoritative, live list — the table below was generated from that
output.

### Shared across `smoke-test`, `benchmark-dev`, `benchmark-held-out`

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--dataset PATH` | path | `experiments/data/invoice_extraction.jsonl` | Dataset file to load. |
| `--experiment-id ID` | string | `invoice-extraction-benchmark` | Recorded in every request record and the manifest; does not otherwise change behavior. |
| `--seed N` | int | `20261023` | Seeds the shuffle of the (case, variant) request plan in `runner.build_plan`. Changing it changes request *order* (balancing exposure to model drift over a run's wall-clock duration), not which cases or variants run. |
| `--output DIR` | path | `experiments/results` | Directory the three run artifacts are written to. |
| `--min-quality FLOAT` | float | *(none — no constraint)* | Reject the candidate if `exact_match_rate < this value`. |
| `--max-cost-per-request FLOAT` | float | *(none)* | Reject the candidate if its mean provider-reported cost per request exceeds this. |
| `--max-p95-latency-ms FLOAT` | float | *(none)* | Reject the candidate if its p95 latency exceeds this. |
| `--min-pairs N` | int | `10` | Minimum paired dev/held-out cases required before the bootstrap comparison is treated as sufficient for a confirmatory accept/reject verdict; below this, the verdict is forced to `inconclusive`. |
| `--limit N` | int | *(none, falls back to `BENCHMARK_CASE_LIMIT`)* | **On `benchmark-dev`/`benchmark-held-out`:** caps the total number of planned requests across both variants (e.g. `--limit 10` runs only the first 10 of the 36 planned dev requests, in seeded-shuffle order). **On `smoke-test`:** caps the number of *dev cases* used for the subset (default 2), not the resulting request count (which is `2 × variants`). |
| `--concurrency N` | int | *(none, uses `BENCHMARK_CONCURRENCY`)* | Overrides `BENCHMARK_CONCURRENCY` for this invocation only. |

### `check-config`

| Flag | Effect |
|---|---|
| `--allow-missing-key` | Skip the "API key is set" check (everything else is still validated). Useful for confirming the rest of the configuration in an environment without a key yet. |

### `validate-dataset`

| Flag | Effect |
|---|---|
| `--dataset PATH` | Dataset file to validate (same default as above). |

### `analyze`

| Flag | Required | Effect |
|---|---|---|
| `--records PATH` | **Yes** | The saved `*.jsonl` run to re-analyze. Makes no API calls. |
| `--output DIR` | No | Where to write the regenerated `*_reanalysis_report.md` (default: same directory as `--records`). |
| `--research-question TEXT` | No | Cosmetic only — fills the report's §1 when the original manifest's isn't being re-read. |
| `--hypothesis TEXT` | No | Same, cosmetic only. |
| `--min-quality`, `--max-cost-per-request`, `--max-p95-latency-ms`, `--min-pairs` | No | Same meaning as above; lets you re-run the accept/reject decision under different constraints without re-querying the API. |

### Reproducibility impact of CLI flags

| Changing this... | ...invalidates direct comparison with a prior run because |
|---|---|
| `--dataset` | Different cases entirely. |
| `--seed` | Different request order (minor effect on free-routing exposure; same cases/variants). |
| `--limit` | Fewer cases evaluated; smaller, noisier sample. |
| `--min-quality` / `--max-cost-per-request` / `--max-p95-latency-ms` / `--min-pairs` | Does **not** change what was measured, only the accept/reject/inconclusive threshold applied to the same numbers — safe to vary when re-analyzing a fixed `.jsonl` via `analyze`. |
| `--concurrency` | Does not change the prompts or scoring, but can change observed latency and whether rate limiting is triggered — don't compare latency numbers across runs with different concurrency. |

## 3. Code-level configuration

These require editing a source file; there is currently no
environment variable or CLI flag for them. This is deliberate for some
(the prompt text and dataset are the artifacts under experiment, not
incidental settings) and a known limitation for others (noted below).

| Setting | Location | How to change it safely |
|---|---|---|
| Baseline / candidate prompt text | `prompt_benchmark/prompts.py` — `BASELINE_TEMPLATE`, `CANDIDATE_TEMPLATE` | Edit the template string (must keep exactly one `{document}` placeholder). The template's `prompt_hash` (first 12 hex chars of its SHA-256) is computed automatically and recorded on every request — if you change the text, the hash changes, and a `.jsonl` record's `prompt_hash` lets you tell which exact wording produced it. **Bump `version="v1"` to `"v2"` on the `PromptVariant` when making a hypothesis-driven change you want to track as a distinct, nameable version** (the registry key becomes `"candidate:v2"`, etc.); for a throwaway edit during iteration the hash alone is enough to distinguish runs. |
| A third/fourth prompt variant | `prompt_benchmark/prompts.py` — add a new `PromptVariant(...)` and include it in `all_variants()` | The runner and analysis code are not hardcoded to exactly two variants at the data-structure level, but the CLI's `_persist_and_report` currently filters records by the literal names `"baseline"` and `"candidate"` for the paired comparison and report — adding a third variant will run and record correctly, but the paired-comparison / accept-reject logic as shipped only compares those two names. Treat a third variant as something you'd currently analyze via `analyze` with custom filtering, not out of the box. |
| System message sent with every request | `prompt_benchmark/prompts.py` — `SYSTEM_MESSAGE` | Edit directly. Not versioned/hashed separately from the module; a change here is not visible in a `.jsonl` record's `prompt_hash` (which only covers the user-turn template). |
| Dataset version string | `prompt_benchmark/dataset.py` — `DATASET_VERSION` | Bump this (e.g. `"invoice-extraction-v3"`) whenever you add, remove, or relabel cases in `data/invoice_extraction.jsonl`, so recorded `dataset_version` fields let you tell which dataset produced a given run. |
| Annotation conventions (what counts as "the total", how ambiguous dates are labeled, etc.) | `prompt_benchmark/dataset.py` — `ANNOTATION_ASSUMPTIONS` | Update the docstring-style constant alongside any labeling-convention change, and re-label affected dataset cases to match. |
| Contract-format rules (date/currency/total regexes) | `prompt_benchmark/evaluation.py` — `_is_valid_date_string`, `_is_valid_currency_code`, `_is_valid_total_string` | Edit directly; these define what counts as a contract violation versus a type violation. Covered by `tests/test_prompt_evaluation.py`. |
| Model-distribution divergence threshold | `prompt_benchmark/schema.py` — `Constraints.max_model_distribution_tvd` (default `0.35`) | Edit the dataclass default, or construct `Constraints(max_model_distribution_tvd=...)` directly if scripting against the package. **Not exposed as a CLI flag** — this is a real, current limitation (see §4). |
| Bootstrap resample count / RNG seed for the paired comparison | `prompt_benchmark/analysis.py` — `paired_exact_match_comparison(n_bootstrap=2000, seed=20261023, ...)` | Edit the default arguments, or call the function directly with different values if scripting against the package. Not exposed as a CLI flag. |
| Minimum sample size before a latency percentile is flagged "small" | `prompt_benchmark/analysis.py` — `MIN_SAMPLE_FOR_PERCENTILE = 20` | Edit the module constant. |
| Refusal-detection keyword list | `prompt_benchmark/analysis.py` — `_REFUSAL_MARKERS` | A deliberately small, conservative list (documented as a heuristic that likely under-counts refusals). Extend with care — a broader list risks false positives on legitimate extraction output. |
| Dataset dev/held-out assignment | `data/invoice_extraction.jsonl` — each record's `"split"` field (`"dev"` or `"held_out"`) | Edit the field directly, then re-run `validate-dataset`. Moving a case between splits after it has been used for prompt iteration defeats the purpose of the held-out split — see `RUN_GUIDE.md` §11. |

## 4. Known configuration limitations

- **No config file.** All environment-level settings must be set as
  actual process environment variables (or passed programmatically to
  `load_config_from_env(env=...)`, which the test suite uses). There is
  no `.ini`/`.toml`/`.yaml` config file mechanism. This is intentional:
  the only secret in play (the API key) is kept out of any file by
  design, and every other setting is small enough that environment
  variables plus CLI flags cover it without adding a config-parsing
  dependency.
- **`max_model_distribution_tvd` and the bootstrap parameters are
  code-level only**, not CLI flags (see table above). If you need to
  tune these per-run without editing source, that is a real gap — the
  minimal fix would be two additional `argparse` options threaded into
  `Constraints(...)` and `paired_exact_match_comparison(...)` the same
  way `--min-pairs` already is. This was not added here as part of this
  documentation pass.
- **`BENCHMARK_CASE_LIMIT` only affects `benchmark-dev` /
  `benchmark-held-out`.** It is intentionally *not* consulted by
  `smoke-test`, which has its own `--limit`/default-2 subset-sizing
  behavior for a different purpose (see §2).
- **A third prompt variant is not fully wired through the CLI's
  report/decision path** (see the code-level table above) — the
  underlying `runner`/`evaluation`/`analysis` functions operate on
  arbitrary `RequestRecord` lists and don't assume exactly two variant
  names, but `prompt_optimization_benchmark.py`'s `_persist_and_report`
  currently does.
