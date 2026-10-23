# Evaluation Fundamentals

## 1. Why LLM Evaluation Matters

Evaluating a large language model (LLM) system means measuring whether it satisfies its intended requirements across representative inputs, realistic operating conditions, and known failure cases.

A prompt that produces one excellent answer is not necessarily a reliable prompt. Model outputs can vary with input wording, context, sampling settings, model versions, and retrieved information. Evaluation turns prompt development from subjective trial and error into a repeatable engineering process.

A robust evaluation process should answer five questions:

1. **Correctness:** Does the system produce factually and logically correct results?
2. **Task performance:** Does it satisfy the actual task requirements?
3. **Reliability:** Does it continue to perform across different inputs and repeated runs?
4. **Safety:** Does it handle sensitive information, malicious instructions, and unsafe requests appropriately?
5. **Operational fitness:** Does it meet latency, cost, format, and availability requirements?

No single metric captures all five dimensions.

## 2. Define the Evaluation Target

Before choosing metrics, specify what is being evaluated. An LLM application may contain several independently failing components:

- Prompt instructions and examples
- Model selection and generation settings
- Context assembly and conversation state
- Retrieval and ranking
- Tool selection and execution
- Output parsing and validation
- Post-processing and application logic

Evaluating only the final answer can reveal a failure without identifying its cause. Component-level measurements make diagnosis more efficient.

For example, an incorrect answer in a retrieval-augmented generation (RAG) system might result from:

- The required document never being indexed
- Retrieval returning irrelevant passages
- The prompt failing to prioritize supplied evidence
- The model misinterpreting correct evidence
- A parser corrupting an otherwise correct response

A useful evaluation plan separates **component evaluation** from **end-to-end evaluation**.

### Define a task contract

Write down the expected behavior before testing. A task contract should identify:

| Element | Question |
|---|---|
| Objective | What must the system accomplish? |
| Input domain | What inputs and variations are expected? |
| Output contract | What must the response contain, and in what format? |
| Quality criteria | What makes an answer correct or useful? |
| Constraints | What must never happen? |
| Failure behavior | Should the system abstain, ask for clarification, retry, or return an error? |
| Operating limits | What are the latency and cost budgets? |

The contract prevents a common evaluation mistake: selecting a metric simply because it is easy to calculate rather than because it measures the intended outcome.

## 3. Build an Evaluation Dataset

An evaluation dataset is a collection of inputs paired with expected outcomes, scoring criteria, or reference evidence.

The dataset should represent the system's intended use, not merely examples that make the current prompt look good.

### 3.1 Dataset categories

A useful dataset combines several kinds of examples:

- **Typical cases:** Common inputs that represent normal usage.
- **Boundary cases:** Empty fields, unusually long inputs, ambiguous wording, and missing context.
- **Difficult cases:** Multi-step tasks, competing constraints, subtle distinctions, or complex formatting.
- **Adversarial cases:** Prompt injection, conflicting instructions, malformed data, and attempts to bypass constraints.
- **Negative cases:** Inputs that should be rejected, escalated, or answered with an explicit uncertainty statement.
- **Regression cases:** Previously observed failures that must not return.
- **Distribution-shift cases:** Inputs that differ from the development data but remain within the expected operating domain.

Keep the categories identifiable. A high aggregate score can conceal a severe failure affecting a small but important group.

### 3.2 Separate dataset splits

Use distinct data for different purposes:

- **Development set:** Used to inspect errors and improve the prompt.
- **Validation set:** Used to compare candidate changes and tune design choices.
- **Test set:** Held back for a more independent estimate of final performance.

For small projects, these can be modest datasets, but the separation of purpose still matters.

Repeatedly inspecting the test set and modifying the prompt in response gradually turns it into development data. The resulting score becomes an increasingly optimistic estimate of generalization.

When examples are correlated—for example, multiple paraphrases of the same underlying question—split them by source, topic, customer, or underlying problem where appropriate. Otherwise, similar examples can leak across splits and inflate measured performance.

### 3.3 Establish data quality

For every evaluation example, record as much of the following as is necessary:

- Stable example identifier
- Input and relevant context
- Expected answer, acceptable answer set, or rubric
- Task category and difficulty
- Required constraints
- Source provenance
- Annotation status and reviewer notes
- Known ambiguities

Reference answers are not always exact strings. Summarization, extraction, classification, and open-ended generation may require different forms of ground truth.

Where multiple outputs are acceptable, encode acceptable alternatives or define a rubric instead of forcing an artificial single reference.

### 3.4 Avoid contamination

Examples used in prompt demonstrations should not silently become evidence of generalization. Keep demonstration examples separate from held-out evaluation examples where feasible.

For systems using external knowledge, check whether the expected answer is available to the system at evaluation time. Otherwise, the test may measure missing information rather than the model's ability to use available information.

## 4. Establish a Baseline

A baseline is the measured performance of a known configuration against a fixed dataset.

Before optimizing a prompt, record:

- Model identifier and version, when available
- System and task prompts
- Few-shot examples
- Generation parameters
- Retrieval configuration
- Tool definitions and relevant application code
- Dataset version
- Evaluation procedure and metric definitions
- Runtime environment and evaluation date

A baseline allows later changes to be judged against a consistent reference.

Useful baselines include:

1. The current production implementation
2. A simple prompt with minimal instructions
3. A non-LLM or deterministic solution, when one is feasible
4. A previous model or prompt version

A more complex prompt should justify its additional complexity through measurable improvements.

## 5. Select Metrics That Match the Task

Metrics should reflect the task contract. A metric is useful only when its relationship to the desired outcome is understood.

### 5.1 Exact-match accuracy

Exact match counts a prediction as correct only when it matches the reference according to a specified comparison rule.

For \(N\) examples:

\[
\text{Accuracy} =
\frac{\text{Number of correct predictions}}{N}
\]

Exact match works well for normalized classification labels, fixed identifiers, and deterministic extraction tasks. It is often too strict for natural-language responses with multiple valid formulations.

Normalization rules must be explicit. Lowercasing, whitespace normalization, or ignoring punctuation can be reasonable for some tasks but harmful for others, such as case-sensitive identifiers.

### 5.2 Precision, recall, and F1

For binary classification or extraction:

\[
\text{Precision} = \frac{TP}{TP + FP}
\]

\[
\text{Recall} = \frac{TP}{TP + FN}
\]

\[
F_1 = 2 \cdot
\frac{\text{Precision}\cdot\text{Recall}}
{\text{Precision}+\text{Recall}}
\]

Where:

- \(TP\): True positives
- \(FP\): False positives
- \(FN\): False negatives

Precision matters when incorrect positive outputs are costly. Recall matters when missing a valid item is costly. F1 summarizes both but does not represent every business trade-off.

For example, extracting every possible entity may improve recall while introducing many unsupported entities and reducing precision.

### 5.3 Semantic similarity

Semantic similarity metrics compare the meaning of a generated response with a reference rather than requiring an exact string match.

They can be useful for paraphrases and semantically similar answers, but similarity is not equivalent to correctness. A fluent answer can be semantically close to a reference while introducing a crucial factual error.

Use similarity as one signal, not as a universal correctness test.

### 5.4 Rubric-based scoring

A rubric defines criteria and scoring rules for outputs that cannot be judged reliably through exact matching.

For a support-response task, a rubric might score:

- Factual correctness
- Relevance to the question
- Completeness
- Compliance with policy
- Clarity
- Appropriate handling of uncertainty

Define what each score means with concrete examples. A score of 4 should have a reproducible interpretation, not simply mean “good.”

Whenever possible, score dimensions separately. One overall score can hide the difference between a correct but incomplete answer and a complete but fabricated one.

### 5.5 Task-specific metrics

Different tasks require different measures:

| Task | Potential measurements |
|---|---|
| Classification | Accuracy, precision, recall, F1, confusion matrix |
| Information extraction | Field-level exact match, entity precision and recall |
| Summarization | Coverage, factual consistency, omission rate, redundancy |
| RAG | Retrieval recall, ranking quality, evidence support, answer correctness |
| Structured generation | Parse success, schema validity, semantic correctness |
| Tool use | Tool-selection accuracy, argument validity, execution success |
| Agentic workflows | Task completion, unnecessary actions, policy violations, recovery rate |
| Production systems | Latency percentiles, cost per successful task, failure rate |

These measurements are complementary. Valid JSON, for instance, does not imply that its values are correct.

## 6. Evaluate Multiple Dimensions

A practical evaluation scorecard separates quality from operational and safety requirements.

### Quality

- Correctness
- Completeness
- Relevance
- Evidence support
- Instruction adherence

### Reliability

- Success rate across repeated runs
- Performance across input categories
- Sensitivity to paraphrasing
- Failure recovery
- Output consistency

### Safety and security

- Resistance to prompt injection
- Protection against unauthorized disclosure
- Appropriate refusal and escalation
- Safe handling of untrusted inputs
- Compliance with application policies

### Operations

- Input and output token counts
- Cost per request and per successful task
- Median and tail latency
- Timeout and parsing failure rates
- Tool and retrieval error rates

Some dimensions should be **hard gates**, not weighted components of a single score. A severe data leak should not be offset by excellent formatting or low cost.

## 7. Design a Reproducible Evaluation Loop

A disciplined evaluation process makes every prompt change testable.

1. **Freeze the baseline.** Record the prompt, model, configuration, dataset, and metrics.
2. **Run the baseline.** Save raw outputs, scores, errors, latency, and token usage.
3. **Classify failures.** Group errors by cause rather than only counting incorrect answers.
4. **Form a hypothesis.** Identify a specific mechanism that may improve performance.
5. **Change one factor where practical.** Avoid simultaneously changing instructions, examples, model settings, and retrieval.
6. **Run the same evaluation set.** Keep the dataset and scoring procedure fixed for a fair comparison.
7. **Inspect regressions.** Check both aggregate scores and important subgroups.
8. **Validate the improvement.** Use held-out data or additional tests to reduce the risk of overfitting.
9. **Record the result.** Preserve the experiment configuration, outcomes, and decision.
10. **Add regression tests.** Turn important newly discovered failures into permanent test cases.

A prompt change should have an explicit hypothesis. For example:

> Adding an explicit missing-value rule should reduce unsupported field completion without materially reducing extraction recall.

This hypothesis is more useful than “make the prompt better” because it defines an expected improvement and a potential trade-off.

## 8. Account for Stochasticity and Statistical Uncertainty

LLM outputs may vary between runs, particularly when sampling is enabled. A single run can produce a misleading estimate of quality.

For stochastic tasks:

- Repeat selected examples or the full evaluation set.
- Record generation parameters and model versions.
- Report means and variability where appropriate.
- Compare candidates on the same examples.
- Investigate examples whose outcomes change frequently.

For a binary success metric, an estimated success rate is:

\[
\hat{p} = \frac{k}{N}
\]

where \(k\) is the number of successes among \(N\) evaluated cases.

The estimate is not the same as the true underlying success probability. Small datasets produce substantial uncertainty, especially when observed success is close to either 0% or 100%.

For paired comparisons, where the baseline and candidate are tested on the same examples, analyze per-example changes rather than treating the two results as unrelated samples. Bootstrap confidence intervals or appropriate paired statistical tests can help quantify uncertainty.

Do not use statistical significance as the only decision rule. Practical importance, safety requirements, operating costs, and the evaluation dataset's representativeness also matter.

## 9. Diagnose Failures Before Rewriting Prompts

A useful error taxonomy makes evaluation actionable.

| Failure category | Example | Possible response |
|---|---|---|
| Instruction ambiguity | The model interprets “brief” inconsistently | Define a measurable length or scope |
| Missing information | Required facts are absent from context | Retrieve data or ask a clarifying question |
| Context selection | Relevant evidence is omitted | Improve context assembly or retrieval |
| Reasoning error | Correct facts lead to an incorrect conclusion | Decompose the task or add intermediate validation |
| Format violation | Output includes prose outside required JSON | Strengthen the output contract and validate programmatically |
| Unsupported claim | The model invents a missing value | Define abstention and evidence requirements |
| Instruction conflict | A document contains commands that contradict the task | Separate trusted instructions from untrusted content |
| Tool failure | Invalid arguments are sent to a tool | Validate arguments and handle tool errors |
| Evaluation defect | A valid alternative answer is marked wrong | Correct the reference or scoring rubric |
| Model variability | Equivalent runs produce different decisions | Repeat tests and examine sampling sensitivity |

Do not assume every failure can be fixed by adding more prompt text. Some problems require better data, retrieval, deterministic validation, application logic, or a different model.

## 10. Compare Prompt Candidates Fairly

A controlled comparison changes as little as possible between candidates.

For each candidate, report:

- Overall score
- Per-category scores
- Critical failure counts
- Output validity
- Latency and token usage
- Number of evaluated examples
- Uncertainty or run-to-run variability
- Known limitations

Avoid comparing results from different datasets, model versions, or scoring procedures as though they were a controlled experiment.

When multiple changes are unavoidable, document them and consider a factorial or staged experiment to identify which changes contributed to the result.

A useful selection rule is:

> Choose the simplest candidate that meets the required quality, safety, and operational thresholds.

The highest average score is not always the best production candidate if it is substantially more expensive, less reliable, or unsafe in a critical subgroup.

## 11. Use LLM-Based Grading Carefully

An LLM judge can score outputs against a rubric, compare candidates, or identify likely factual problems. It is useful for evaluation tasks where exact matching is inadequate, but it introduces another source of error.

Potential judge biases include:

- Preferring longer or more polished answers
- Favoring a particular answer position
- Rewarding agreement with its own assumptions
- Missing subtle factual errors
- Applying rubrics inconsistently
- Being influenced by irrelevant wording

Reduce these risks by defining explicit criteria, testing the judge against human-reviewed examples, checking inter-rater agreement, and periodically auditing disagreements.

For high-impact decisions, do not rely exclusively on an unvalidated automated judge. Human review, deterministic checks, and independent evidence may be necessary.

## 12. Prevent Evaluation Overfitting

Repeated prompt tuning against a fixed dataset can produce a prompt that performs well on those examples but poorly on new inputs.

Common causes include:

- Writing special-case instructions for individual test examples
- Adding examples that closely resemble the evaluation set
- Repeatedly adjusting a prompt based on judge scores
- Removing difficult examples because they reduce the aggregate score
- Changing the rubric after seeing candidate outputs

Mitigations include:

- Keeping a genuinely held-out test set
- Maintaining diverse and representative examples
- Using error categories instead of memorizing individual failures
- Reviewing changes against regression and adversarial cases
- Rotating or refreshing evaluation data where appropriate
- Rechecking performance after model or dependency changes

Do not remove difficult cases merely to improve a score. If an example is invalid or outside scope, document the reason for excluding it.

## 13. Evaluation in Production

Offline evaluation is necessary but insufficient. Real inputs and operational conditions can differ from development assumptions.

Production monitoring can track:

- Task success and failure rates
- Distribution shifts in input categories
- Schema and parsing errors
- Retrieval quality and evidence availability
- Tool-call failures
- Latency and cost distributions
- User corrections, escalations, and abandonment
- Safety incidents and unexpected disclosures

Log only information that is appropriate and necessary for the application. Sensitive inputs and outputs should be protected through access controls, retention limits, and redaction where appropriate.

Production signals should feed back into the evaluation dataset after review and sanitization. User behavior is useful evidence, but it is not automatically a reliable ground-truth label.

When changing prompts, models, or retrieval configurations, use staged deployment where practical. Compare candidate performance, retain rollback options, and monitor for regressions after release.

## 14. Evaluation Experiment Record

For every meaningful experiment, record a compact, reproducible entry:

```yaml
experiment_id: eval-001
objective: Improve structured extraction accuracy
baseline:
  prompt_version: v1
  model: recorded-model-version
candidate:
  prompt_version: v2
dataset:
  name: extraction-eval
  version: 1.0
  examples: 200
metrics:
  primary: field_exact_match
  secondary:
    - schema_validity
    - unsupported_value_rate
    - latency_ms
results:
  baseline_score: null
  candidate_score: null
decision: pending
notes: Record observed errors, trade-offs, and limitations
```

The values above are a template, not measured results. Replace placeholders with actual experiment data. Store sensitive evaluation inputs separately when required by the project's data-handling policy.

## 15. Practical Evaluation Checklist

Before accepting a prompt or model change, verify the following:

- [ ] The task contract and success criteria are explicit.
- [ ] The evaluation set represents realistic inputs and known edge cases.
- [ ] Development and final test examples are appropriately separated.
- [ ] The baseline configuration and results are recorded.
- [ ] Metrics match the task rather than merely being convenient.
- [ ] Safety-critical requirements are enforced as hard gates.
- [ ] Important failure categories are tracked separately.
- [ ] Repeated runs or statistical uncertainty are considered where relevant.
- [ ] Candidate comparisons use a consistent evaluation procedure.
- [ ] The prompt has been checked for regressions and overfitting.
- [ ] Cost, latency, and output validity are included where relevant.
- [ ] Evaluation results are reproducible and documented.
- [ ] Production monitoring and rollback plans exist for deployed changes.

## Conclusion

LLM evaluation is an engineering discipline built around explicit requirements, representative data, meaningful metrics, controlled experiments, and continuous failure analysis.

The goal is not simply to maximize a benchmark score. It is to establish credible evidence that a system performs the intended task reliably, safely, and within operational constraints.

A strong evaluation process makes prompt improvements measurable, exposes weaknesses that anecdotal testing misses, and provides a defensible basis for deciding whether a change should be deployed.