# Experimental Methodology

## Purpose

This directory contains reproducible experiments for evaluating and optimizing prompt-driven systems. Experiments should produce evidence that supports engineering decisions, not merely demonstrate prompting techniques.

Every experiment must define a measurable objective, establish a credible baseline, control relevant variables, and document the limitations of its conclusions.

## Experimental Requirements

### 1. Hypothesis and Objective

Each experiment must specify:

- **Research question:** What engineering decision is the experiment intended to inform?
- **Hypothesis:** What measurable change is expected, and why?
- **Primary metric:** The metric used to determine whether the hypothesis is supported.
- **Constraints:** Applicable limits on latency, token usage, monetary cost, reliability, or other operational requirements.
- **Decision rule:** The conditions under which a candidate is accepted, rejected, or investigated further.

Distinguish exploratory experiments from confirmatory evaluations. Do not present exploratory findings as conclusive evidence.

### 2. Baselines and Comparisons

Every proposed improvement must be compared against an appropriate baseline.

- Preserve a reproducible baseline configuration.
- Change one factor at a time when attributing effects to individual prompt changes.
- Use factorial or other suitable designs when interactions between factors are part of the research question.
- Compare candidates on the same evaluation cases wherever possible.
- Include ablations when they help establish which components contribute to observed performance.
- Avoid comparisons that confound prompt changes with model, sampling, context, or evaluation changes.

A more complex prompt is not inherently a better prompt.

### 3. Evaluation Data

Evaluation datasets must reflect the intended task and its relevant failure modes.

Document:

- Dataset provenance, version, and licensing where applicable.
- Inclusion and exclusion criteria.
- Expected outputs and annotation procedures.
- Coverage of common, ambiguous, adversarial, and boundary cases.
- Known sampling biases and gaps.
- Separation between development data and held-out evaluation data.

Avoid tuning prompts against the final test set. Where repeated optimization is necessary, use separate development and final evaluation sets, and reserve the latter for final assessment.

### 4. Metrics and Statistical Reliability

Select metrics according to the task contract rather than convenience.

Depending on the experiment, report:

- Task quality and error rates.
- Constraint violations and structured-output validity.
- Robustness across input variations.
- Token consumption and monetary cost.
- Latency, including relevant percentile measurements.
- Failure rates, abstentions, and fallback behavior.

For stochastic systems, document the number of independent runs, sampling configuration, and sources of variability. Report uncertainty when the sample size and experimental design support it.

Use paired comparisons when candidates are evaluated on the same cases. Select statistical methods appropriate to the metric and sampling design. Do not infer practical significance from a small numerical difference alone.

### 5. Cost and Operational Constraints

Prompt optimization is a constrained engineering problem, not simply a search for maximum task accuracy.

Define the objective explicitly. For example:

- Maximize task quality subject to cost and latency limits.
- Minimize cost while maintaining a specified quality threshold.
- Improve robustness without exceeding a token budget.
- Compare candidates on a quality-cost-latency Pareto frontier.

Measure actual usage and latency when available. Clearly distinguish measured values from estimates. Document model pricing assumptions and the date of the pricing reference when reporting monetary costs.

### 6. Reproducibility and Run Metadata

Record enough information for another engineer to understand and reproduce the experiment.

At minimum, capture:

- Experiment identifier and timestamp.
- Hypothesis and protocol version.
- Prompt template and version or hash.
- Model identifier and available model-version metadata.
- Generation parameters and seed, if supported.
- Dataset version and evaluation configuration.
- Software dependencies and relevant environment details.
- Per-case outputs, expected results, and evaluation outcomes.
- Token usage, latency, and cost when available.
- Errors, retries, timeouts, and incomplete runs.

Do not assume a fixed seed guarantees deterministic behavior from a hosted model. Record provider-side changes or unavailable metadata as limitations.

Never commit API keys, credentials, private evaluation data, or sensitive production traces.

### 7. Failure Analysis

Aggregate scores are insufficient to explain why a candidate succeeds or fails.

Classify material failures into relevant categories, such as:

- Instruction ambiguity or conflict.
- Missing or irrelevant context.
- Unsupported inference or hallucination.
- Output-contract violations.
- Sensitivity to input wording or ordering.
- Prompt injection or trust-boundary failures.
- Tool-use errors and invalid arguments.
- Excessive cost, latency, or retry behavior.

Compare failure distributions between candidates. Preserve representative examples in a privacy-safe form and distinguish observed failures from hypothesized causes.

### 8. Result Reporting

Every completed experiment should include:

1. Research question and hypothesis.
2. Experimental design and baseline.
3. Dataset and evaluation methodology.
4. Results with relevant uncertainty.
5. Cost, latency, and constraint compliance.
6. Failure analysis and regressions.
7. Limitations and threats to validity.
8. Engineering recommendation and follow-up work.

Report negative and inconclusive results. Do not omit failed runs or selectively report favorable metrics without a documented reason.

## Suggested Experiment Layout

Use the smallest structure that supports reproducibility. Not every experiment requires a separate package or multiple files.

```text
experiments/
├── README.md
└── <experiment-name>/
    ├── README.md          # Protocol, findings, limitations
    ├── run.py             # Execution entry point, if needed
    ├── config.yaml        # Versioned experiment configuration
    ├── data/              # Small, permitted, versioned datasets
    ├── results/           # Generated metrics and reports
    └── tests/             # Protocol and evaluation tests, if needed
```

Large datasets, private data, secrets, and bulky generated artifacts should remain outside version control or use an appropriate artifact-storage mechanism. Record their identifiers and checksums when needed for reproducibility.

## Acceptance Criteria

An experiment is ready for review when:

- [ ] Its hypothesis and primary metric are explicit.
- [ ] The baseline and candidate configurations are reproducible.
- [ ] The evaluation data and scoring procedure are documented.
- [ ] The comparison controls relevant confounding variables.
- [ ] Cost, latency, and operational constraints are measured or clearly marked unavailable.
- [ ] Material regressions and representative failures are analyzed.
- [ ] Conclusions are supported by the evidence and bounded by stated limitations.
- [ ] The recommended engineering decision follows from predefined or explicitly justified criteria.

The objective is not to maximize the number of experiments. It is to produce a small body of reliable evidence that improves prompt-engineering decisions.

## Implemented Experiment: Invoice-Extraction Prompt Benchmark

`prompt_optimization_benchmark.py` and the `prompt_benchmark/` package
implement the methodology above end to end for a structured
information-extraction task (see also
[`09-applications/information-extraction.md`](../09-applications/information-extraction.md)).

### What it measures

- Whether a candidate prompt improves invoice-field extraction quality
  over a baseline, under an explicit, versioned output contract.
- Which error categories (missing fields, decoy/distractor selection,
  hallucinated values, contract violations) improve or regress.
- Whether a development-set improvement persists on a held-out split.
- Token, latency, and provider-reported cost trade-offs.
- Sensitivity to OpenRouter's free-model routing, including whether
  baseline and candidate were served comparable model distributions.
- An explicit accept / reject / inconclusive decision, with the
  reasoning that produced it — including when the evidence is simply
  insufficient to decide.

Metric definitions, denominators, and the free-routing confounding
issue are documented in detail in [`evaluations/README.md`](../evaluations/README.md).

### Architecture

```text
experiments/
  prompt_optimization_benchmark.py   CLI entry point
  prompt_benchmark/
    config.py       environment-driven configuration and validation
    prompts.py      versioned, content-hashed prompt templates
    dataset.py      dataset loading and structural validation
    evaluation.py   deterministic, provider-independent scoring
    client.py       OpenRouter client: injectable transport, bounded retries
    schema.py       RequestRecord / RunManifest schemas, secret redaction
    runner.py       executes a benchmark plan through the client + evaluator
    analysis.py     aggregation, model-distribution and paired comparisons
    reporting.py    atomic artifact writes and the markdown report
  data/
    invoice_extraction.jsonl   versioned, labeled dataset (dev + held_out)
  results/          generated per-run artifacts (not committed; see .gitignore)
```

### Setup, configuration, and the CLI

Installation, environment setup, every CLI command with verified
example output, troubleshooting, and cleanup live in
[`RUN_GUIDE.md`](RUN_GUIDE.md) — start there to actually run something.

Every environment variable, CLI flag, and code-level setting (with
defaults, validation rules, and what changing each one does to
reproducibility) is documented in
[`CONFIGURATION.md`](CONFIGURATION.md).

### Dataset and split policy

`data/invoice_extraction.jsonl` (dataset version `invoice-extraction-v2`)
contains 32 synthetic, hand-labeled cases: 18 in the `dev` split, 14 in
`held_out`. Edge cases include missing fields, subtotal/tax-vs-total
and prior-balance/disputed-amount distractors, purchase-order-vs-
invoice-ID confusion, similar sibling identifiers, ambiguous dates,
explicit negation/correction, embedded prompt-injection text, a
malformed/truncated document, empty and very short inputs, irrelevant
marketing boilerplate, and a long-context case. Several cases label
specific "decoy" strings — plausible-but-wrong values physically
present in the document — which `analysis.py` uses to compute an
honest, narrowly-scoped unsupported-inference rate.

Annotation assumptions (what counts as the "real" total when a
subtotal/prior-balance/disputed amount is also present, how currency
and ambiguous dates are labeled, how embedded instructions are treated)
are documented in `prompt_benchmark/dataset.py::ANNOTATION_ASSUMPTIONS`.

**Split discipline:** prompt iteration (`benchmark-dev`) must only use
`dev`. `held_out` is evaluated once a candidate is already chosen, to
check generalization — never used to pick between prompt revisions. 32
cases is a small dataset; treat any single run's numbers as indicative,
not as proof of production-scale generalization.

### Interpreting results

Each run writes three artifacts to `experiments/results/` (never
overwriting a prior run): `<run_id>.jsonl` (one fully auditable record
per request), `<run_id>_manifest.json` (the experiment protocol:
hypothesis, metrics, constraints, limitations), and
`<run_id>_report.md` (the human-readable report with an explicit
accept/reject/inconclusive verdict and reasons).

**Responsible conclusions look like:**

- "On this 18-case dev split, the candidate's paired exact-match rate
  was 0.22 higher (95% CI [0.05, 0.38], n=18 pairs), baseline and
  candidate model distributions were comparable (TVD=0.08) — accept,
  pending held-out confirmation."
- "n=2 is a smoke test; the INCONCLUSIVE verdict is correct and
  expected. This is a pipeline check, not evidence."
- "The model distributions diverged sharply (TVD=0.6) between variants
  in this run; any quality difference is confounded with model
  selection and the result is reported as inconclusive rather than a
  prompt-only effect."

**Not responsible:** treating a single smoke-test run, an aggregate
score with failed requests silently excluded, or a quality difference
on a diverging model mix as proof that the candidate prompt is better.

### Reproduction

See [`RUN_GUIDE.md`](RUN_GUIDE.md) for the full step-by-step walkthrough
(environment setup, API-key configuration, each command, and verified
example output from a real run). Minimal path once `OPENROUTER_API_KEY`
is set in your shell session:

```powershell
python experiments/prompt_optimization_benchmark.py check-config
python experiments/prompt_optimization_benchmark.py validate-dataset
python experiments/prompt_optimization_benchmark.py benchmark-dev
```

Offline (no API key, no network): `python -m unittest discover -s tests -v`.