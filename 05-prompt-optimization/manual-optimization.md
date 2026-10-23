# Manual Prompt Optimization

## 1. Overview

Manual prompt optimization is the systematic process of improving a prompt through observation, controlled changes, and evaluation.

The objective is not to produce a prompt that looks more sophisticated. It is to improve measurable task performance while respecting constraints such as latency, token usage, output consistency, and maintainability.

A prompt may fail because its instructions are ambiguous, the required context is missing, the output contract is underspecified, or the task itself exceeds the model's capabilities. Rewriting the prompt without identifying the failure mechanism can waste time or make performance worse.

A reliable optimization process treats prompts as testable system components rather than static pieces of prose.

## 2. The Optimization Loop

A practical optimization workflow follows these stages:

1. Define the task and success criteria.
2. Establish a baseline prompt.
3. Build a representative evaluation dataset.
4. Run the baseline and record failures.
5. Classify errors by failure mechanism.
6. Form a specific hypothesis about the cause.
7. Change one major factor at a time.
8. Re-run the evaluation.
9. Compare quality, cost, and latency.
10. Retain, revise, or revert the change.

The process can be represented as:

`Baseline → Evaluate → Diagnose → Hypothesize → Modify → Re-evaluate`

This loop should continue until the prompt meets the acceptance criteria or the remaining failures require a different solution, such as better retrieval, deterministic validation, tool use, or a model change.

## 3. Define Success Before Editing

Prompt optimization is unreliable when success is judged only by whether a new response sounds better.

Define measurable criteria before making changes.

Depending on the application, these may include:

- Task accuracy.
- Required-field completeness.
- Instruction adherence.
- Structured-output validity.
- Evidence grounding.
- Appropriate abstention.
- Robustness to ambiguous inputs.
- Response latency.
- Token consumption and cost.

Separate mandatory requirements from preferences. For example, valid JSON may be mandatory, while a concise explanation may be a preference.

A prompt that improves style but increases factual errors is not necessarily an improvement.

### Example acceptance criteria

For an information-extraction task, acceptance criteria might include:

- All required fields are present.
- Missing values use an approved representation.
- Every extracted value is supported by the input.
- The output conforms to the required schema.
- The system does not invent unavailable information.

The exact criteria should reflect the task's risks and operational requirements.

## 4. Build a Representative Evaluation Dataset

A prompt should be evaluated on more than a handful of convenient examples.

Construct a dataset that reflects the expected input distribution and important edge cases.

Include examples such as:

- Typical inputs.
- Unusual but valid inputs.
- Missing information.
- Ambiguous wording.
- Contradictory information.
- Long inputs.
- Malformed input.
- Adversarial or instruction-conflicting content, where relevant.

For each example, define the expected behavior. The expected result may be an exact answer, a set of acceptable outputs, a validated structure, or an explicit abstention.

### Keep test cases stable

When comparing prompt variants, use the same test cases and evaluation rules. Otherwise, a change in measured performance may reflect a change in the dataset rather than a real improvement.

For ongoing optimization, separate data into:

- **Development set:** Used frequently to diagnose errors and improve prompts.
- **Validation set:** Used to compare candidate variants during development.
- **Held-out test set:** Used less frequently to estimate performance on unseen examples.

Repeatedly tuning against the held-out set can overfit the prompt to that dataset.

## 5. Establish a Baseline

The baseline is the reference configuration against which candidate prompts are compared.

Record:

- The exact prompt text and version.
- Model identifier and relevant configuration.
- Input dataset version.
- Sampling settings.
- Output constraints.
- Tool and retrieval configuration, if applicable.
- Evaluation procedure.
- Quality, latency, and cost measurements.

Keep unrelated components stable during an experiment. If the prompt, model, retrieval strategy, and sampling parameters all change at once, it becomes difficult to identify which change caused the result.

For stochastic generation, repeat runs where practical or use a suitable evaluation method to account for variation.

## 6. Diagnose Failures Before Rewriting

Classify failures according to their likely cause.

| Failure category      | Example symptom                                 | Possible intervention                                  |
| --------------------- | ----------------------------------------------- | ------------------------------------------------------ |
| Instruction ambiguity | Different interpretations of the task           | Clarify the objective and decision rules               |
| Missing context       | The model lacks required facts                  | Improve retrieval or input selection                   |
| Constraint violation  | The answer ignores a requirement                | Make constraints explicit and test compliance          |
| Output-format failure | Invalid JSON or missing fields                  | Define a schema and validate outputs                   |
| Reasoning error       | Incorrect intermediate calculation              | Decompose the task or use deterministic tools          |
| Grounding failure     | Claims lack supporting evidence                 | Supply relevant sources and validate claims            |
| Context overload      | Important facts are overlooked                  | Reduce noise and organize evidence                     |
| Capability limitation | The model cannot reliably perform the operation | Use tools, a different model, or another system design |

These categories can overlap. A prompt failure may actually be caused by poor retrieval or an unreliable downstream parser.

The intervention should address the underlying mechanism, not merely the visible symptom.

## 7. Form Testable Hypotheses

Every prompt modification should have a reason that can be tested.

A useful hypothesis specifies:

- The observed failure.
- The suspected cause.
- The proposed change.
- The expected improvement.
- The metrics that will determine success.
- Potential regressions.

For example:

**Observation:** The model returns a string instead of a numeric value for a field that must contain a number.

**Hypothesis:** The output contract does not make the field type sufficiently explicit.

**Change:** Specify the required numeric type, give one valid example, and add schema validation.

**Evaluation:** Measure schema-validity rate and extraction accuracy on the same test dataset.

This is more informative than changing several unrelated sentences and judging the output informally.

## 8. Change One Major Factor at a Time

Controlled experiments help identify why a prompt change succeeds or fails.

Potential variables include:

- Instruction wording.
- Task decomposition.
- Output schema.
- Number and selection of examples.
- Context organization.
- Explicit handling of missing information.
- Error and abstention policies.
- Role framing.
- Output length constraints.

Changing one major factor at a time is a useful diagnostic approach, especially early in optimization.

However, prompt components can interact. Once individual changes are understood, factorial experiments or other systematic comparison methods can help identify interactions.

Do not assume that a modification that helps one example will improve the entire evaluation set.

## 9. Optimize Instructions

Instructions should describe the required behavior precisely enough to distinguish acceptable from unacceptable outputs.

Useful improvements include:

### Clarify the objective

Replace vague requests such as “analyze this carefully” with a concrete operation and expected result.

### Resolve ambiguity

Specify how to handle conflicting evidence, missing fields, units, dates, or multiple possible interpretations.

### Define constraints

State mandatory requirements, prohibited behavior, and relevant boundaries.

### Specify the decision procedure

For tasks with important conditional behavior, define the conditions under which the system should take each action.

### Define failure behavior

Explain when the model should report uncertainty, request clarification, or abstain rather than invent missing information.

### Remove contradictions

Conflicting instructions can make compliance unpredictable. Establish a clear hierarchy among requirements and remove unnecessary duplication.

The objective is to reduce uncertainty about what constitutes a correct result, not to make the prompt longer.

## 10. Optimize Output Contracts

Output requirements should be treated as an interface specification.

For structured tasks, define:

- Required fields.
- Data types.
- Allowed values.
- Missing-value behavior.
- Formatting rules.
- Validation constraints.
- Error behavior.

For example, an extraction prompt might specify that a missing date must be represented as `null`, not an empty string or an invented date.

For critical applications, enforce output constraints through supported structured-generation features and validate the resulting data in application code.

Prompt wording alone cannot guarantee that every output is syntactically or semantically valid.

## 11. Optimize Examples

Few-shot examples can improve performance when they demonstrate the intended mapping between inputs and outputs.

When adjusting examples, consider:

- Whether the examples represent the target distribution.
- Whether they cover difficult or ambiguous cases.
- Whether they demonstrate correct handling of missing information.
- Whether their output formats match the required contract.
- Whether they accidentally encourage unwanted behavior.
- Whether the examples consume context needed for the actual task.

Avoid adding examples simply to increase their number. A small, well-selected set may be more effective than a larger collection of redundant or inconsistent examples.

Evaluate example selection on the same dataset used to compare the prompt variants.

## 12. Optimize Context and Retrieval Separately

A prompt may appear ineffective because the necessary evidence never reaches the model.

Before changing instructions, check:

- Was the relevant source available?
- Did retrieval select the correct passages?
- Were important qualifications removed during compression?
- Was the context truncated?
- Were conflicting sources presented without sufficient metadata?
- Was untrusted content clearly distinguished from governing instructions?

If the context is deficient, rewrite the retrieval or context-assembly process rather than expecting stronger prompt wording to compensate for missing information.

When possible, evaluate prompt quality with fixed, known-good context before evaluating the full retrieval pipeline.

## 13. Measure Quality, Cost, and Latency

A candidate prompt should be compared across multiple dimensions.

| Metric                   | Purpose                                           |
| ------------------------ | ------------------------------------------------- |
| Task accuracy            | Measures correctness                              |
| Constraint adherence     | Measures compliance with required behavior        |
| Schema-validity rate     | Measures structural correctness                   |
| Groundedness             | Measures whether claims are supported by evidence |
| Failure rate by category | Identifies remaining weaknesses                   |
| Latency                  | Measures response time                            |
| Token usage              | Measures input and output consumption             |
| Cost per successful task | Relates resource usage to useful outcomes         |

A prompt that produces slightly better answers but dramatically increases cost may not be the best choice for a high-volume application.

Likewise, a cheaper prompt that frequently requires manual correction may have a higher total operational cost.

Define the trade-offs that matter before selecting the final configuration.

## 14. Statistical Reliability and Variance

LLM outputs can vary with sampling settings, model updates, and other runtime factors.

A small observed improvement may reflect random variation rather than a robust benefit.

For stochastic tasks:

- Repeat runs where appropriate.
- Use a sufficiently representative dataset.
- Report sample sizes alongside aggregate scores.
- Inspect failures as well as averages.
- Estimate uncertainty when comparing important performance differences.
- Test the selected prompt on held-out examples.

For paired comparisons, running two prompt variants on the same examples can reduce noise caused by differences in input difficulty.

When the evaluation dataset is small, be cautious about claiming that a minor score difference establishes a real improvement.

## 15. Common Optimization Mistakes

### Optimizing by intuition alone

**Problem:** Changes are accepted because a few responses look better.

**Correction:** Use predefined evaluation criteria and a stable dataset.

### Editing several components simultaneously

**Problem:** The cause of a performance change becomes unclear.

**Correction:** Isolate major variables during diagnosis and use systematic experiments to investigate interactions.

### Overfitting to examples

**Problem:** The prompt performs well on known cases but fails on new inputs.

**Correction:** Use held-out test data and diverse edge cases.

### Making prompts unnecessarily long

**Problem:** Extra instructions introduce redundancy, contradictions, or additional token cost.

**Correction:** Retain only instructions that improve behavior or are necessary for correctness.

### Treating every failure as a prompt problem

**Problem:** Retrieval defects, missing data, or model limitations are addressed with more instructions.

**Correction:** Diagnose the complete system and select the intervention appropriate to the failure source.

### Ignoring regressions

**Problem:** One metric improves while another important requirement deteriorates.

**Correction:** Track multiple metrics and preserve mandatory acceptance criteria.

### Failing to version prompts

**Problem:** A regression cannot be traced to a specific change.

**Correction:** Store prompt versions, experiment configurations, evaluation results, and change rationale.

## 16. Practical Experiment Template

Use a consistent record for each experiment.

```text
Experiment ID:
Prompt version:
Model and configuration:
Dataset version:

Observed failure:
Hypothesis:
Proposed change:
Expected outcome:

Primary metric:
Secondary metrics:
Regression risks:

Baseline result:
Candidate result:
Interpretation:

Decision:
- Keep
- Revise
- Revert

Next experiment:
```

This record creates a traceable history of why a prompt changed and whether the change improved the intended behavior.

For team environments, store experiment records alongside the prompt or in an evaluation system that supports reproducible comparisons.

## 17. Deployment and Regression Testing

A prompt that passes development evaluation can still fail after deployment because real inputs, source data, model behavior, or application dependencies change.

Before release:

1. Run the selected prompt against the regression suite.
2. Verify mandatory output and safety constraints.
3. Compare cost and latency against the current production version.
4. Record the prompt version and configuration.
5. Roll out changes with appropriate monitoring.
6. Retain a rollback path when feasible.

After release, monitor failure patterns and collect representative examples for future evaluation. Handle user data according to the application's privacy and retention requirements.

When a model or retrieval system changes, re-evaluate the prompt rather than assuming its previous results remain valid.

## 18. Key Takeaways

Manual prompt optimization is an empirical engineering process: establish a baseline, diagnose failures, form hypotheses, make controlled changes, and measure outcomes.

The strongest improvements come from addressing specific failure mechanisms rather than adding more instructions indiscriminately.

Treat prompts as versioned components, evaluate them against representative data, and select changes based on measurable quality, reliability, and operational cost.
