# Automatic Prompt Optimization

## 1. Overview

Automatic Prompt Optimization (APO) is the process of using algorithms, language models, evaluation systems, or search procedures to improve prompts with limited manual intervention.

Instead of relying entirely on a person to inspect outputs and rewrite instructions, an optimization system evaluates candidate prompts against a defined objective and uses the results to guide further revisions.

An automated workflow may:

1. Start with an initial prompt.
2. Evaluate it against a dataset.
3. Identify failure cases.
4. Generate candidate prompt variations.
5. Score the candidates.
6. Select promising variants.
7. Repeat until a stopping condition is reached.

The goal is to find a prompt that satisfies the task's quality requirements while balancing cost, latency, robustness, and maintainability.

Automatic optimization does not eliminate the need for human judgment. The quality of its results depends on the evaluation objective, dataset, search strategy, and safeguards against overfitting.

## 2. Formalizing the Optimization Problem

A prompt can be treated as a configurable component whose performance is measured on a dataset.

Let \(p\) denote a candidate prompt and \(D\) an evaluation dataset. A basic objective is:

\[
p^* = \arg\max_{p \in P} S(p, D)
\]

where:

- \(P\) is the set of candidate prompts.
- \(S(p,D)\) is the measured performance of prompt \(p\) on dataset \(D\).
- \(p^*\) is the selected prompt.

In practice, prompt quality is rarely a single unconstrained metric. A system may need to maximize accuracy while enforcing requirements such as valid output format, acceptable latency, and a token budget.

One formulation is:

\[
\max_p \quad Q(p)
\]

subject to:

\[
C(p) \leq C_{\max}
\]

\[
L(p) \leq L_{\max}
\]

\[
V(p) \geq V_{\min}
\]

where \(Q\) represents task quality, \(C\) cost, \(L\) latency, and \(V\) a validity or compliance measure.

The thresholds are application-specific. They should be defined before optimization begins.

A prompt that improves one metric while violating a mandatory constraint should not automatically be considered the winner.

## 3. Components of an Automatic Optimization System

A practical APO system typically contains the following components.

### Initial prompt

The starting configuration to be improved. It should already express the task, relevant constraints, and expected output.

### Evaluation dataset

A representative collection of inputs with expected outputs, acceptable behaviors, or evaluation criteria.

### Execution engine

Runs each candidate prompt against the dataset using a specified model and configuration.

### Scoring function

Measures the quality of each candidate's outputs. Depending on the task, scoring may use exact-match accuracy, deterministic checks, reference comparisons, or a calibrated model-based evaluator.

### Candidate generator

Creates alternative prompts by editing instructions, adding clarifications, reorganizing constraints, or generating entirely new formulations.

### Search strategy

Decides which candidates to evaluate next and how to use previous results.

### Selection and stopping logic

Chooses candidates according to the objective and decides when to stop based on a budget, performance target, or lack of improvement.

### Experiment record

Stores prompts, model settings, dataset versions, scores, failures, and decisions so results can be reproduced.

Separating these components makes it easier to debug an optimizer when its selected prompt performs poorly.

## 4. Evaluation Functions

The scoring function is one of the most consequential parts of automatic optimization.

If the scoring function does not represent the real task, the optimizer may learn to exploit the metric rather than improve actual performance.

### Deterministic evaluation

Use exact checks when the expected behavior can be expressed precisely.

Examples include:

- Exact-match answers.
- Numeric tolerances.
- JSON schema validation.
- Required-field completeness.
- Allowed-category membership.
- Code execution against unit tests.
- Citation identifiers that must exist.

Deterministic evaluation is reproducible and generally easier to audit, but it cannot fully capture open-ended qualities such as helpfulness or nuanced reasoning.

### Reference-based evaluation

Compare candidate outputs with reference answers using task-appropriate metrics.

This is useful when reference outputs are available, but multiple valid responses may make exact matching too restrictive.

### Model-based evaluation

A separate evaluator model scores outputs against a rubric.

A rubric might assess correctness, completeness, instruction adherence, evidence grounding, and style.

Model-based evaluation can support open-ended tasks, but the evaluator may be inconsistent, biased toward certain wording, or unable to detect subtle errors.

Use calibration examples, human review, and agreement analysis to determine whether the evaluator is reliable enough for the task.

### Composite scoring

A composite score can combine multiple measures:

\[
S(p) = \sum_{i=1}^{m} w_i s_i(p)
\]

where \(s_i\) is a component metric and \(w_i\) is its weight.

This is useful when trade-offs matter, but weights can hide important failures. A high style score should not compensate for a violation of a mandatory safety or correctness requirement.

For hard requirements, use explicit constraints or rejection rules instead of relying exclusively on weighted averages.

## 5. Candidate Generation Strategies

An optimizer needs a way to propose new prompts.

### LLM-based rewriting

A language model examines an existing prompt and proposes a revision based on observed failures.

For example, if outputs repeatedly omit a required field, the generator might clarify the output contract or define explicit missing-value behavior.

**Strength:** Can produce semantically meaningful revisions.

**Limitation:** May make unsupported changes, introduce contradictions, or generate longer prompts without improving performance.

### Error-guided refinement

The optimizer groups failed examples and asks a generator to propose a change that addresses a specific error category.

For example:

- Missing fields suggest output-contract improvements.
- Unsupported claims suggest stronger evidence requirements.
- Incorrect classification suggests clearer decision boundaries.
- Invalid types suggest stricter schema constraints.

This approach connects candidate generation to observed failure mechanisms.

### Template search

A system varies predefined prompt components, such as instruction order, example selection, or output format.

**Strength:** Easier to reproduce and compare.

**Limitation:** Search is limited to the configurations represented by the templates.

### Mutation and recombination

An optimizer modifies parts of candidate prompts or combines components from promising variants.

These strategies can explore a wider candidate space, but they need safeguards against semantic drift and unnecessary complexity.

## 6. Search Strategies

Candidate generation creates possibilities; search determines which ones are worth evaluating.

### Random search

Generate candidates from a defined space and evaluate them.

Random search is simple and can be a useful baseline when the search space is small or the cost of each evaluation is manageable.

### Greedy search

At each iteration, select a candidate that improves the current score.

This is straightforward but can become trapped in a local optimum and may reject changes that help only when combined with other changes.

### Beam search

Maintain several promising candidates rather than only the current best one.

This preserves alternative directions of exploration, at the cost of evaluating and tracking more candidates.

### Evolutionary search

Maintain a population of candidate prompts and generate new candidates through mutation, selection, or recombination.

This can explore diverse prompt variants but may consume substantial evaluation resources.

### Bayesian or surrogate-guided search

Use a model of previous evaluations to prioritize promising configurations when evaluations are expensive.

This can be useful for structured search spaces or costly experiments, although prompt text is a complex search variable and surrogate models may be imperfect.

No strategy is universally best. The appropriate method depends on evaluation cost, candidate diversity, search-space structure, and the amount of compute available.

## 7. A Basic APO Workflow

A general optimization loop can be expressed as:

1. Define the task objective and constraints.
2. Create an initial prompt and baseline evaluation.
3. Run the prompt against the development dataset.
4. Record failed examples and their error categories.
5. Generate a bounded set of candidate revisions.
6. Evaluate candidates using the same model configuration and dataset.
7. Reject candidates that violate hard requirements.
8. Rank the remaining candidates by the optimization objective.
9. Retain promising candidates and repeat.
10. Evaluate the selected prompt on held-out data before deployment.

The workflow should preserve the best-known candidate, not merely the most recently generated prompt.

Every iteration should have a reason for consuming additional evaluation resources.

## 8. Example: Optimizing an Information-Extraction Prompt

Suppose a system extracts structured records from customer support messages.

The required output includes:

- Issue category.
- Product identifier.
- Urgency.
- Evidence excerpt.
- A missing-value representation when the identifier is unavailable.

The initial prompt produces outputs with two recurring failures:

1. The product identifier is sometimes invented when it is absent.
2. The urgency field is occasionally returned as free-form prose.

An error-guided optimizer could proceed as follows.

### Baseline evaluation

Run the initial prompt against a fixed dataset and measure:

- Field-level accuracy.
- Missing-value correctness.
- Schema-validity rate.
- Unsupported-value rate.

### Candidate generation

Generate variants that:

- Explicitly prohibit inventing identifiers.
- Define the allowed urgency labels.
- Specify how missing values should be represented.
- Clarify the evidence requirement for extracted fields.

### Candidate evaluation

Run all variants on the same dataset, using the same model configuration and scoring rules.

### Selection

Choose a candidate that improves the required metrics without increasing unsupported extraction or breaking the schema.

### Held-out verification

Evaluate the selected prompt on unseen messages, including messages with ambiguous product references and conflicting information.

This example illustrates a search process, not a claim that any particular prompt revision will improve performance. The measured results determine whether a candidate is retained.

## 9. Overfitting and Data Leakage

An optimizer can overfit its evaluation dataset.

If it repeatedly modifies prompts to address specific examples, it may learn accidental patterns in those examples rather than general rules that transfer to unseen inputs.

Common warning signs include:

- Development scores improving while held-out scores stagnate or decline.
- Prompt instructions becoming excessively specific to known examples.
- Candidate outputs matching reference wording without improving underlying correctness.
- Performance dropping on rare or previously unseen inputs.

Use separate data partitions:

- **Development set:** Supports error analysis and iterative prompt changes.
- **Validation set:** Supports candidate comparison and selection.
- **Held-out test set:** Estimates generalization after optimization decisions are finalized.

Avoid using the held-out set to repeatedly choose new prompt revisions. If it becomes part of the optimization process, it is no longer an independent test set.

Also ensure that examples derived from the same source, customer, or document are not inadvertently split across partitions when that could leak information.

## 10. Evaluator Reliability

An automatic optimizer is only as reliable as its evaluation procedure.

A model-based evaluator may favor outputs that are longer, more confident, or stylistically similar to its preferred format, even when they are not more correct.

Potential evaluator failure modes include:

- Position bias when comparing candidate A with candidate B.
- Inconsistent scores across repeated evaluations.
- Sensitivity to irrelevant wording.
- Failure to detect factual errors.
- Preference for verbose responses.
- Rewarding outputs that satisfy the rubric superficially.

Mitigations include:

- Prefer deterministic checks for objective requirements.
- Define explicit scoring rubrics.
- Test evaluator agreement with human judgments.
- Randomize candidate order in pairwise comparisons where appropriate.
- Use multiple evaluations when uncertainty justifies the cost.
- Audit high-scoring outputs for hidden failures.
- Separate hard constraints from subjective quality scores.

Do not assume that an evaluator score is a calibrated probability of correctness.

## 11. Robustness and Generalization

A prompt optimized for typical inputs may fail under distribution shifts.

Robustness testing should include:

- Ambiguous wording.
- Missing required information.
- Long and unusually structured inputs.
- Contradictory evidence.
- Rare categories.
- Malformed input.
- Adversarial content relevant to the application.
- Inputs that should trigger abstention or escalation.

Evaluate the optimized prompt across relevant subgroups rather than relying only on one aggregate score.

A useful selection strategy can favor candidates that meet minimum performance thresholds across all critical categories, even if another candidate achieves a higher overall average.

For high-impact systems, regression testing should be repeated whenever the prompt, model, retrieval configuration, or evaluation logic changes materially.

## 12. Cost-Aware Optimization

Automatic optimization can become expensive because each candidate may require many model calls.

A rough evaluation budget can be estimated as:

\[
C_{\text{total}} \approx
N_{\text{candidates}}
\times N_{\text{examples}}
\times C_{\text{evaluation per example}}
\]

This is an approximation. Actual cost depends on input and output token counts, model pricing, retries, parallelism, caching, and the evaluator design.

Cost controls include:

- Use a small development dataset for early screening.
- Evaluate promising candidates on a larger dataset.
- Cache deterministic evaluation results when safe and valid.
- Limit candidate counts and iteration budgets.
- Stop when improvements no longer justify their cost.
- Reserve held-out testing for final candidates.
- Track cost per successful task, not only cost per model call.

Be careful with early screening. A small dataset can cheaply reject weak candidates, but it may also reject a prompt that performs well on important rare cases.

## 13. Prompt Complexity and Maintainability

An optimizer can improve benchmark scores while producing prompts that are difficult to understand or maintain.

Potential symptoms include:

- Excessive instruction length.
- Repeated or contradictory constraints.
- Rules that apply only to a few benchmark examples.
- Complex conditional instructions with unclear precedence.
- Fragile dependence on exact wording.

Include maintainability in the selection process.

A practical approach is to prefer the simplest prompt among candidates with comparable quality and acceptable operational cost. This can be expressed as a regularized objective:

\[
J(p) = Q(p) - \lambda K(p)
\]

where \(Q(p)\) is task quality, \(K(p)\) is a complexity measure, and \(\lambda\) controls the penalty for complexity.

The complexity measure might incorporate token length, number of conditional rules, or a human maintainability assessment. It should be chosen carefully: shorter prompts are not automatically simpler or better.

## 14. Practical Pseudocode

The following pseudocode illustrates the control flow of a basic optimizer.

```python
def optimize_prompt(
    initial_prompt,
    dataset,
    generate_candidates,
    evaluate,
    max_iterations=10,
):
    best_prompt = initial_prompt
    best_score = evaluate(best_prompt, dataset)

    history = [{
        "prompt": best_prompt,
        "score": best_score,
    }]

    for iteration in range(max_iterations):
        candidates = generate_candidates(
            current_prompt=best_prompt,
            evaluation_history=history,
        )

        scored_candidates = []

        for candidate in candidates:
            score = evaluate(candidate, dataset)

            scored_candidates.append({
                "prompt": candidate,
                "score": score,
            })

        if not scored_candidates:
            break

        candidate_best = max(
            scored_candidates,
            key=lambda item: item["score"],
        )

        history.extend(scored_candidates)

        if candidate_best["score"] > best_score:
            best_prompt = candidate_best["prompt"]
            best_score = candidate_best["score"]
        else:
            break

    return {
        "best_prompt": best_prompt,
        "best_score": best_score,
        "history": history,
    }
```

This is illustrative pseudocode, not a complete production optimizer. It assumes a numeric score where higher is better and uses a simple greedy selection rule.

A production implementation should additionally:

- Enforce hard constraints.
- Track model and dataset versions.
- Handle stochastic evaluation.
- Separate development and held-out data.
- Deduplicate candidates.
- Set token and cost budgets.
- Preserve a rollback path.
- Avoid stopping solely because one iteration fails to improve.
- Use robust comparison rules for noisy scores.

Most importantly, the returned development score should not be treated as an unbiased estimate of generalization after repeated optimization.

## 15. Automatic vs. Manual Optimization

| Dimension | Manual optimization | Automatic optimization |
|---|---|---|
| Candidate generation | Human-written revisions | Algorithmic or model-generated revisions |
| Error interpretation | Human analysis | Automated analysis, human analysis, or both |
| Evaluation scale | Often limited by manual effort | Can evaluate many candidates |
| Reproducibility | Depends on experiment discipline | Can be systematic with versioned experiments |
| Main cost | Human time and repeated testing | Model calls, evaluation infrastructure, and compute |
| Main risk | Subjective decisions and inconsistent testing | Metric exploitation and dataset overfitting |
| Best fit | Small or nuanced tasks | Repeatable tasks with measurable objectives |

The approaches are complementary. Human expertise is often valuable for defining the objective and diagnosing unusual failures, while automation can explore candidate variations and execute repetitive evaluations.

## 16. When to Use Automatic Prompt Optimization

Consider APO when:

- The task is repeated at meaningful scale.
- A representative evaluation dataset exists.
- Performance can be measured reliably.
- Candidate evaluation can be automated or partially automated.
- The potential benefit justifies the search cost.
- Prompt versions and experiments can be tracked.

Manual optimization may be more appropriate when the task is novel, evaluation criteria are unclear, examples are scarce, or outputs require nuanced human judgment.

Do not automate prompt search before establishing a reliable evaluation process. An optimizer can efficiently discover prompts that exploit a flawed metric.

## 17. Deployment Checklist

Before deploying an automatically optimized prompt, verify that:

- [ ] The optimization objective reflects real task requirements.
- [ ] Hard constraints are enforced independently of aggregate scores.
- [ ] The evaluation dataset represents expected use cases.
- [ ] Candidate generation is bounded and reproducible.
- [ ] Prompt, model, and dataset versions are recorded.
- [ ] Evaluator reliability has been tested.
- [ ] Overfitting and data leakage risks are addressed.
- [ ] Robustness and regression tests pass.
- [ ] Cost, latency, and prompt complexity are acceptable.
- [ ] The selected prompt passes held-out evaluation.
- [ ] Deployment monitoring and rollback procedures exist.

## 18. Key Takeaways

Automatic Prompt Optimization turns prompt refinement into a measurable search process.

Its effectiveness depends on the quality of the objective, the reliability of evaluation, the diversity of candidate generation, and the discipline of the search procedure.

The central principle is to optimize for real task performance—not merely for a benchmark score—and to verify the selected prompt on data that was not used to choose it.