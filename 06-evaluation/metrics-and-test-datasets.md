# Metrics and Test Datasets

## 1. Introduction

LLM evaluation depends on two tightly connected design decisions:

1. **What to measure:** The metrics used to represent correctness, quality, reliability, safety, and operational performance.
2. **What to test:** The dataset used to estimate how well a system performs across realistic inputs and failure conditions.

A metric cannot compensate for a poor dataset, and a representative dataset cannot compensate for a metric that measures the wrong property.

For example, a summarization system might achieve a high semantic-similarity score while omitting a critical exception. A structured extraction system might produce valid JSON while assigning incorrect values. A retrieval system might retrieve relevant documents but generate an unsupported answer.

The evaluation design must therefore connect each requirement to observable evidence.

This lesson covers metric selection, dataset construction, annotation, sampling, statistical interpretation, test maintenance, and practical implementation.

## 2. Start with a Measurement Model

Before selecting metrics, define the behavior that constitutes success.

A useful measurement model contains four layers:

| Layer | Purpose | Example |
|---|---|---|
| Requirement | States what must be true | Every extracted invoice total must be correct |
| Observable signal | Captures relevant behavior | Predicted total matches the verified total |
| Metric | Aggregates observations | Field-level exact-match rate |
| Decision threshold | Defines acceptable performance | At least 98% on the designated test set |

The threshold must be justified by task requirements, risk, and the consequences of errors. There is no universal accuracy threshold that applies to all LLM applications.

### 2.1 Primary and secondary metrics

Choose one primary metric for the main optimization objective when possible. Use secondary metrics to detect trade-offs.

For an information-extraction system:

- Primary: exact-match rate for critical fields
- Secondary: schema-validity rate
- Secondary: missing-value accuracy
- Secondary: unsupported-value rate
- Secondary: latency and cost per successful record

A candidate that improves the primary metric but substantially increases fabricated values may not be acceptable.

### 2.2 Hard constraints versus weighted scores

Some requirements should be enforced as hard constraints rather than averaged into a score.

For example:

- Output must be parseable.
- Unauthorized disclosure must not occur.
- Required fields must not contain fabricated values.
- Critical safety policies must be respected.

A weighted score can hide a serious failure behind improvements elsewhere. Use hard gates for non-negotiable requirements and weighted metrics only for dimensions where trade-offs are legitimate.

## 3. Classification Metrics

Classification maps an input to one or more predefined labels. Examples include routing a support request, detecting an intent, or assigning a document category.

### 3.1 Confusion matrix

For binary classification, predictions can be divided into four groups:

| | Actual positive | Actual negative |
|---|---:|---:|
| Predicted positive | True positive (TP) | False positive (FP) |
| Predicted negative | False negative (FN) | True negative (TN) |

These counts reveal the kinds of errors hidden by a single accuracy value.

### 3.2 Accuracy

\[
\text{Accuracy} = \frac{TP+TN}{TP+TN+FP+FN}
\]

Accuracy is useful when the class distribution and error costs make overall correctness meaningful.

It can be misleading on imbalanced datasets. If 99% of inputs belong to a negative class, a classifier that always predicts negative can achieve 99% accuracy while never detecting a positive case.

### 3.3 Precision and recall

\[
\text{Precision} = \frac{TP}{TP+FP}
\]

\[
\text{Recall} = \frac{TP}{TP+FN}
\]

Precision answers: “Of the cases predicted positive, how many were truly positive?”

Recall answers: “Of the truly positive cases, how many were detected?”

Choose according to error costs. High precision may be essential when a false positive triggers an expensive or disruptive action. High recall may be essential when missing an important case is more harmful.

### 3.4 F1 score

\[
F_1 = \frac{2PR}{P+R}
\]

where \(P\) is precision and \(R\) is recall.

F1 balances precision and recall through their harmonic mean. It does not account for true negatives and does not directly encode business-specific error costs.

The generalized \(F_\beta\) score gives more weight to recall when \(\beta > 1\) and more weight to precision when \(\beta < 1\).

### 3.5 Multiclass and multilabel evaluation

For multiclass classification, report per-class performance as well as an aggregate.

Common aggregation methods include:

- **Macro average:** Compute the metric for each class and average the class scores equally.
- **Micro average:** Aggregate the underlying counts before computing the metric.
- **Weighted macro average:** Average class metrics weighted by class support.

Macro averages expose poor performance on minority classes. Micro averages reflect the overall distribution of decisions. Weighted averages can still conceal weaknesses in rare but important classes.

For multilabel tasks, evaluate each label and the complete predicted label set when both perspectives matter.

### 3.6 Undefined metric values

Precision is undefined when a system makes no positive predictions. Recall is undefined when there are no positive examples in the evaluation sample.

Evaluation code must define how such cases are handled. Do not silently treat undefined values as zero or one without documenting the convention.

## 4. Metrics for Information Extraction

Information extraction transforms unstructured text into structured entities, fields, or records.

A single overall score can conceal different failure modes, so use several levels of evaluation.

### 4.1 Field-level exact match

For a field such as `invoice_number`, compare the predicted value with the verified reference after applying task-appropriate normalization.

Normalization might include trimming surrounding whitespace or standardizing date formats. It should not erase meaningful distinctions.

For example, converting `"00127"` to `"127"` may be incorrect when leading zeros are significant.

### 4.2 Record-level exact match

A record is correct only if every required field is correct.

\[
\text{Record Accuracy} =
\frac{\text{Fully correct records}}{\text{Total records}}
\]

Record accuracy is stricter than field-level accuracy. If a record contains ten independently evaluated fields, a high per-field accuracy can still yield a much lower probability of a fully correct record.

Under the simplifying assumption that every field is independently correct with probability \(p\), the probability that all \(m\) fields are correct is:

\[
P(\text{record correct}) = p^m
\]

Real field errors are not necessarily independent, but the formula illustrates why field-level and record-level results should both be reported.

### 4.3 Entity-level precision and recall

For extraction tasks where the number of entities varies, evaluate the extracted entity set.

Define a matching rule for deciding when a predicted entity corresponds to a reference entity. Depending on the task, matching may require exact span boundaries, normalized text equality, or agreement on both entity text and type.

Then calculate precision, recall, and F1 over matched entities.

The matching rule must be fixed before comparing candidates. Otherwise, apparent improvements may reflect changes in scoring rather than actual model behavior.

### 4.4 Missing values and unsupported values

Treat missing information explicitly.

Measure at least:

- Correctly extracted values
- Correctly identified missing values
- Missing values that should have been extracted
- Fabricated values unsupported by the input

A system that fills every field may appear complete while inventing information. Conversely, a system that returns null for every field may avoid fabrication but fail the task.

The target behavior is accurate extraction combined with appropriate abstention.

## 5. Metrics for Generation and Summarization

Open-ended generation often lacks a single correct string. Evaluation therefore needs multiple complementary signals.

### 5.1 Reference-based metrics

Reference-based methods compare generated outputs with one or more human-written references.

They may measure lexical overlap, semantic similarity, or task-specific correspondence.

Limitations include:

- Valid paraphrases may receive low scores.
- A response may match reference wording while introducing an unsupported claim.
- A single reference may not represent every acceptable answer.
- A high similarity score does not guarantee that important information is preserved.

Use these metrics for what they measure, not as universal proxies for quality.

### 5.2 Rubric-based evaluation

A rubric defines criteria for judging generated outputs.

For a summary, criteria might include:

1. Coverage of important source facts
2. Factual consistency with the source
3. Preservation of qualifications and uncertainty
4. Relevance to the requested audience
5. Absence of unsupported details
6. Appropriate length

Define the scale with observable anchors. For instance, a high factual-consistency score might require that every substantive claim be supported by the source, while a low score might indicate multiple material contradictions.

Avoid vague dimensions such as “overall quality” unless they are decomposed into clearer criteria.

### 5.3 Claim-level factual consistency

For tasks where factual reliability matters, break a response into checkable claims and evaluate each against trusted evidence.

Possible measurements include:

- Fraction of claims supported by evidence
- Fraction of claims contradicted by evidence
- Rate of unsupported material claims
- Coverage of required source facts

Claim-level evaluation can reveal errors hidden by an answer-level score.

The method still depends on reliable claim extraction, evidence selection, and adjudication. If the verifier cannot access the necessary evidence, it should not automatically treat the claim as false.

### 5.4 Pairwise preference

A judge can compare two candidate outputs and decide which better satisfies a defined objective.

Pairwise evaluation is useful when people can reliably express relative preferences but struggle to assign stable absolute scores.

Control for:

- Candidate ordering
- Differences in response length
- Inconsistent rubrics
- Judge preference for polished wording
- Ties and genuinely equivalent answers

A preference winner is not necessarily factually correct. Pairwise preference should be combined with correctness and safety checks when those properties matter.

## 6. Metrics for Retrieval-Augmented Generation

Retrieval-augmented generation (RAG) has at least two distinct evaluation targets: retrieving useful evidence and generating an answer that uses it correctly.

### 6.1 Retrieval Recall@k

Suppose a query has a set of known relevant documents \(R\), and the system retrieves a ranked list \(L_k\) containing the first \(k\) results.

\[
\text{Recall@k} =
\frac{|R \cap L_k|}{|R|}
\]

Recall@k measures the proportion of known relevant documents retrieved in the top \(k\).

It is useful when missing relevant evidence is costly, but it does not distinguish the ordering of retrieved documents.

### 6.2 Precision@k

\[
\text{Precision@k} =
\frac{|R \cap L_k|}{k}
\]

Precision@k measures the proportion of top-\(k\) results that are relevant.

When fewer than \(k\) results are returned, define the denominator convention explicitly. Some implementations divide by the number returned rather than \(k\); these conventions should not be mixed across experiments.

### 6.3 Mean reciprocal rank

Mean reciprocal rank (MRR) measures how highly the first relevant result appears.

For query \(i\), let \(r_i\) be the rank of the first relevant result. Its reciprocal rank is \(1/r_i\), with zero assigned when no relevant result appears.

\[
\text{MRR} = \frac{1}{N}\sum_{i=1}^{N}\frac{1}{r_i}
\]

MRR is useful when finding one highly relevant result early is important.

### 6.4 Normalized discounted cumulative gain

Normalized discounted cumulative gain (NDCG) supports graded relevance, allowing results to be more or less relevant rather than merely relevant or irrelevant.

It rewards highly relevant results near the top of the ranking and discounts lower-ranked results.

Use NDCG when relevance grades are meaningful and the order of retrieved results matters. Record the relevance scale and discount convention as part of the evaluation specification.

### 6.5 End-to-end RAG evaluation

A complete RAG scorecard may include:

- Retrieval recall and ranking quality
- Evidence coverage
- Citation correctness
- Claim support
- Answer correctness
- Appropriate abstention when evidence is insufficient
- Latency and cost

A system can retrieve the correct document but generate an incorrect answer. It can also produce a plausible answer using prior model knowledge despite poor retrieval.

Therefore, retrieval quality and final-answer quality should be measured separately.

## 7. Metrics for Structured Output and Tool Use

### 7.1 Syntax validity

Measure the proportion of outputs that can be parsed according to the required format.

For JSON, this means the response is valid JSON—not necessarily that it has the correct keys or values.

### 7.2 Schema validity

Measure whether parsed output conforms to the expected schema, including:

- Required properties
- Data types
- Enumerated values
- Additional-property rules
- Field-specific constraints

Report syntax and schema validity separately when both failure types matter.

### 7.3 Semantic correctness

Check whether the values represent the intended meaning.

For example, a valid object containing a customer identifier from the wrong record is syntactically and structurally correct but semantically incorrect.

### 7.4 Tool-use metrics

For tool-using systems, consider:

- Correct tool selection
- Correct argument construction
- Successful execution
- Appropriate response to tool errors
- Completion of the requested task
- Unnecessary or repeated tool calls
- Policy compliance

Do not reward raw tool-call volume. A system that uses fewer calls may be more efficient, but only if it still completes the task correctly.

## 8. Construct a Representative Test Dataset

A dataset should reflect the actual distribution of inputs and the consequences of errors.

### 8.1 Define the target population

Specify what future requests the evaluation is intended to represent.

Examples include:

- Support tickets from a specific product
- Documents produced by known business processes
- Questions asked by a particular user group
- Requests handled by a production workflow

Without a defined target population, the meaning of an aggregate score is unclear.

### 8.2 Stratified sampling

Divide the population into meaningful groups and sample from each group.

Possible strata include:

- Task category
- Language
- Input length
- Difficulty
- Source document type
- Frequency of a critical class
- Risk level

Stratification makes it easier to measure performance on important subgroups. However, a deliberately balanced evaluation set may not match production prevalence.

If the test distribution differs from the production distribution, report subgroup metrics or use documented weights to estimate target-population performance.

For subgroup \(j\), let \(w_j\) be its expected production share and \(s_j\) its measured score. A weighted estimate is:

\[
S = \sum_{j=1}^{J} w_j s_j
\]

The weights should represent the intended deployment distribution, not be chosen to make a candidate look better.

### 8.3 Include rare, high-impact cases

Frequency alone should not determine test coverage.

A rare case involving sensitive-data disclosure may deserve more attention than a common, low-impact formatting issue.

Maintain a separate critical-case suite when failures have serious consequences. Evaluate those cases directly instead of relying solely on a prevalence-weighted average.

### 8.4 Include realistic variation

Test semantically equivalent inputs with differences such as:

- Paraphrased instructions
- Different ordering of information
- Minor spelling errors
- Missing optional fields
- Long or nested documents
- Different formatting conventions
- Distracting but irrelevant context

These variations help reveal brittle prompt behavior. They should preserve the intended task so that the test measures robustness rather than introducing a different problem.

## 9. Create Reliable Reference Labels

The quality of an evaluation dataset is limited by the quality of its labels and scoring rules.

### 9.1 Annotation guidelines

Document:

- Definitions of each label
- Inclusion and exclusion rules
- Normalization procedures
- How to handle ambiguous examples
- How to represent missing or unavailable information
- When to mark an example unscorable
- How disagreements are resolved

Provide positive examples, negative examples, and boundary cases.

### 9.2 Multiple annotators

For subjective or ambiguous tasks, independent annotation can expose unclear definitions and inconsistent judgments.

A typical process is:

1. Have annotators label a shared sample independently.
2. Measure agreement using an appropriate method.
3. Inspect disagreements and recurring ambiguity.
4. Refine the guidelines.
5. Adjudicate unresolved examples.
6. Re-annotate affected cases if the rules materially changed.

Raw agreement is easy to understand but does not account for agreement expected by chance. Depending on the task, Cohen's kappa, Fleiss' kappa, or Krippendorff's alpha may be appropriate. The assumptions and limitations of each method should be considered.

High agreement does not prove that the labels are correct; annotators may share the same misconception.

### 9.3 Track label uncertainty

Not every example has a unique objectively correct answer.

Possible approaches include:

- Multiple accepted answers
- A range of acceptable scores
- Explicitly ambiguous labels
- Reviewer notes explaining the uncertainty
- Exclusion from a metric that assumes a definitive answer

Do not force uncertain examples into precise ground truth merely to simplify computation.

## 10. Statistical Reliability of Metrics

Measured performance is an estimate, not a guarantee of future performance.

### 10.1 Confidence intervals

For a binary success rate, let \(k\) be the number of successes out of \(N\) independent examples:

\[
\hat{p} = \frac{k}{N}
\]

A confidence interval expresses uncertainty about the underlying rate under a statistical model.

Simple normal-approximation intervals can behave poorly with small samples or observed rates near zero or one. Wilson intervals or exact binomial intervals are often more suitable for binary outcomes.

The interval does not correct for a biased dataset, incorrect labels, or repeated tuning against the same test set.

### 10.2 Paired candidate comparisons

When comparing two prompts, evaluate both on the same examples.

For each example, record whether the candidate:

- Improves over the baseline
- Regresses relative to the baseline
- Produces an equivalent outcome

This paired design reduces noise caused by different example difficulty. For binary outcomes, McNemar's test can be appropriate for analyzing discordant paired predictions. For other metrics, paired bootstrap procedures may be useful.

### 10.3 Sample size and uncertainty

A small test set may be useful for fast development checks but insufficient for a confident estimate of production performance.

Required sample size depends on:

- Expected success rate
- Desired precision of the estimate
- Acceptable false-positive and false-negative risks
- Importance of subgroup performance
- Correlation among examples
- Variability between model runs

Rare events require particular care. Observing zero failures in a small sample does not prove that the failure probability is zero.

For critical safety and security behaviors, combine statistical testing with targeted adversarial cases, independent review, and defense-in-depth controls.

## 11. Prevent Dataset Leakage and Overfitting

Dataset leakage occurs when information from the evaluation target improperly influences model development or evaluation.

Common sources include:

- Duplicate or near-duplicate examples across splits
- Evaluation answers included in prompt demonstrations
- Test examples repeatedly inspected during optimization
- Future information leaking into historical test records
- Retrieval indexes containing information that should not be available at test time
- Synthetic examples generated directly from reference answers without independent review

Mitigations include:

- Deduplicating before splitting
- Grouping related examples into the same split
- Holding back a test set
- Versioning prompts and datasets
- Reviewing data provenance
- Recreating the test environment with appropriate information boundaries
- Maintaining a separate regression suite for known failures

A test set should be difficult to influence accidentally and should not become a growing collection of examples that the prompt memorizes.

## 12. Regression and Robustness Suites

A regression suite preserves examples associated with previous defects.

Each regression case should identify:

- The original failure
- The expected behavior
- The severity
- The affected component
- The conditions required to reproduce it

A robustness suite tests behavior under controlled variations and adversarial inputs.

For example, a prompt-injection test might place a malicious instruction inside a document that the model is supposed to summarize. The expected behavior is determined by the task contract: the document should be treated as content, not automatically elevated to a trusted instruction.

Keep regression and robustness results visible separately from ordinary average performance. Passing common cases does not imply resilience to adversarial inputs.

## 13. Build a Small Evaluation Harness

The following Python example illustrates a basic field-level exact-match evaluator. It assumes predictions and references have already been collected and that their keys correspond to the same examples.

```python
from collections import defaultdict
from typing import Any


def normalize(value: Any) -> Any:
    """Normalize only distinctions that are irrelevant to the task."""
    if isinstance(value, str):
        return value.strip()
    return value


def evaluate_fields(
    predictions: list[dict[str, Any]],
    references: list[dict[str, Any]],
    required_fields: list[str],
) -> dict[str, Any]:
    if len(predictions) != len(references):
        raise ValueError(
            "Predictions and references must have equal lengths."
        )

    if not predictions:
        raise ValueError("Evaluation dataset must not be empty.")

    field_counts = defaultdict(lambda: {"correct": 0, "total": 0})
    record_correct = 0

    for prediction, reference in zip(predictions, references):
        record_is_correct = True

        for field in required_fields:
            predicted_value = normalize(prediction.get(field))
            reference_value = normalize(reference.get(field))

            field_counts[field]["total"] += 1

            if predicted_value == reference_value:
                field_counts[field]["correct"] += 1
            else:
                record_is_correct = False

        if record_is_correct:
            record_correct += 1

    field_accuracy = {
        field: counts["correct"] / counts["total"]
        for field, counts in field_counts.items()
    }

    return {
        "example_count": len(predictions),
        "field_accuracy": field_accuracy,
        "record_accuracy": record_correct / len(predictions),
    }


predictions = [
    {"name": "Ada", "country": "UK"},
    {"name": "Grace", "country": "US"},
]

references = [
    {"name": "Ada", "country": "UK"},
    {"name": "Grace", "country": "USA"},
]

results = evaluate_fields(
    predictions,
    references,
    required_fields=["name", "country"],
)

print(results)
```

This implementation is intentionally minimal. It assumes that missing keys should compare as `None`, does not distinguish missing keys from explicit null values, and treats all required fields equally.

For production evaluation, consider adding:

- Stable example IDs and key-based alignment
- Duplicate and missing-ID checks
- Explicit missing-value semantics
- Field-specific normalization
- Schema validation
- Per-category metrics
- Confidence intervals
- Structured error reports
- Dataset and prompt version identifiers
- Exportable machine-readable results

Do not silently pair predictions and references by position if the data may be reordered. Use stable identifiers and validate that every expected example has exactly one corresponding prediction.

## 14. Record Metric Definitions and Results

Metrics are only reproducible when their calculation rules are recorded.

For each metric, document:

- Name and purpose
- Formal definition
- Unit of analysis: field, record, claim, query, or complete task
- Normalization and matching rules
- Treatment of missing or invalid outputs
- Aggregation method
- Relevant limitations
- Decision threshold, if applicable

For each evaluation run, record:

- Dataset version and example count
- Prompt and model versions
- Model parameters
- Retrieval and tool configuration
- Metric results and subgroup results
- Latency and cost
- Known anomalies
- Whether any test examples influenced development

This record makes it possible to distinguish genuine performance changes from changes in evaluation procedure.

## 15. Common Evaluation Mistakes

### Mistake 1: Using one metric for every task

Accuracy, exact match, semantic similarity, and judge scores measure different properties.

**Improvement:** Map each requirement to a metric that directly measures it.

### Mistake 2: Reporting only an aggregate score

A high overall score may hide failures in a rare class or critical subgroup.

**Improvement:** Report relevant slices and hard-gate failures separately.

### Mistake 3: Changing normalization between runs

A candidate can appear better simply because the comparison became more permissive.

**Improvement:** Version normalization and scoring rules alongside the dataset.

### Mistake 4: Treating valid format as correct content

A response can pass JSON validation while containing fabricated values.

**Improvement:** Evaluate syntax, schema, and semantic correctness separately.

### Mistake 5: Treating a balanced dataset as production-representative

A balanced dataset can improve subgroup analysis but distort estimates of overall production performance.

**Improvement:** Report unweighted subgroup results and, when justified, a separately weighted production estimate.

### Mistake 6: Tuning repeatedly on the test set

Repeated test-driven changes make the final result less independent.

**Improvement:** Use development data for iteration and reserve held-out data for final validation.

### Mistake 7: Assuming zero observed failures means zero risk

A finite test cannot establish that an event is impossible.

**Improvement:** Report sample sizes, uncertainty, and complementary targeted tests.

### Mistake 8: Optimizing the metric instead of the task

A metric can be improved without improving the user outcome.

**Improvement:** Review actual failure examples and verify that the metric remains aligned with the task contract.

## 16. Practical Checklist

### Metrics

- [ ] Each metric is tied to an explicit requirement.
- [ ] Primary and secondary metrics are identified.
- [ ] Hard safety and correctness gates are defined.
- [ ] Normalization and matching rules are documented.
- [ ] Subgroup results are available for important categories.
- [ ] Missing values and invalid outputs have explicit handling rules.

### Datasets

- [ ] The target population is defined.
- [ ] Typical, difficult, boundary, and adversarial cases are included.
- [ ] Data splits prevent duplicate and related-example leakage.
- [ ] Reference labels have documented guidelines.
- [ ] Ambiguous cases are handled consistently.
- [ ] Critical rare cases receive dedicated coverage.
- [ ] Dataset provenance and version are recorded.

### Statistical quality

- [ ] Sample size is appropriate for the decision.
- [ ] Uncertainty is considered for measured rates.
- [ ] Candidate comparisons use paired examples when appropriate.
- [ ] Test data is not repeatedly used as development data.
- [ ] Zero observed failures are not interpreted as proof of zero risk.

### Operations

- [ ] Evaluation runs are reproducible.
- [ ] Prompt, model, dataset, and metric versions are recorded.
- [ ] Cost and latency are measured where relevant.
- [ ] Regression tests cover important known failures.
- [ ] Production feedback is reviewed before being added to the dataset.

## Conclusion

Metrics and test datasets form the measurement foundation of reliable LLM engineering. Good metrics make failures observable; good datasets make the measurements representative; and disciplined statistical and data practices make the conclusions credible.

The central principle is to evaluate the behavior that matters, preserve the distinctions between different kinds of failure, and ensure that each reported result can be reproduced and interpreted correctly.