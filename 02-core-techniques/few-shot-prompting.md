# Few-Shot Prompting

## 1. Overview

Few-shot prompting provides a language model with a small number of input-output demonstrations before asking it to perform a new instance of the task.

The demonstrations illustrate the expected mapping between inputs and outputs. The model uses these examples as part of the current context when generating its response.

This behavior is commonly discussed as **in-context learning**. It does not require updating the model's parameters or performing gradient-based training.

Few-shot prompting is useful when instructions alone do not adequately communicate a task's conventions, label boundaries, or expected output format.

## 2. Structure of a Few-Shot Prompt

A typical few-shot prompt contains:

1. Task instructions
2. Demonstration examples
3. The new input to process
4. Optional output constraints

For example, consider sentiment classification with a specialized annotation policy.

```text
Classify each message as POSITIVE, NEUTRAL, or NEGATIVE.

Message: "The replacement arrived quickly and works perfectly."
Label: POSITIVE

Message: "The replacement arrived, but I have not tested it yet."
Label: NEUTRAL

Message: "The replacement stopped working after one day."
Label: NEGATIVE

Message: "The replacement works, but delivery took two weeks."
Label:
```

The demonstrations provide reference patterns for the classification task. The model must infer how the examples relate to the final input.

The examples are part of the prompt context; they do not permanently modify the model.

## 3. Why Demonstrations Matter

Instructions describe a task symbolically. Demonstrations show concrete instances of how that task should be performed.

Examples can communicate:

- Label definitions and decision boundaries
- Domain-specific terminology
- Input-output mappings
- Formatting conventions
- The intended level of detail
- How particular edge cases should be handled

However, demonstrations are not guarantees of correct generalization. A model may imitate superficial patterns instead of learning the intended distinction.

## 4. Example Selection

The usefulness of few-shot prompting depends on which examples are included.

### 4.1 Representative examples

Examples should reflect the intended task and the diversity of inputs expected in deployment.

For classification, this may mean covering different classes, common phrasing variations, and important borderline cases.

### 4.2 Boundary examples

Borderline examples help clarify distinctions between labels.

For instance, a positive product review containing a complaint about delivery may require a defined policy for determining overall sentiment.

If the annotation policy is unclear, demonstrations may reinforce inconsistency rather than resolve it.

### 4.3 Diversity versus redundancy

Several nearly identical examples may add little information. A smaller set of diverse examples can communicate more distinct patterns.

The appropriate balance depends on the task and the available context budget.

### 4.4 Example quality

Incorrect or contradictory demonstrations can mislead the model.

Before using examples:
- Verify their labels.
- Ensure consistent annotation rules.
- Remove irrelevant details.
- Check that examples do not unintentionally reveal answers to evaluation cases.

## 5. Example Ordering and Selection Effects

Few-shot performance can depend on example order, the composition of the demonstration set, and the position of the target input.

Possible reasons include differences in local patterns, recency, attention, and interactions between examples and instructions.

Therefore, example ordering should be treated as an experimental variable rather than a universal rule.

For important applications, compare multiple valid demonstration sets and orderings on the same evaluation data.

Do not assume that putting the most similar example last or balancing the number of examples per class will always improve performance. These are hypotheses to test.

## 6. Zero-Shot Versus Few-Shot

| Dimension | Zero-shot | Few-shot |
|---|---|---|
| Demonstrations | None | Included in context |
| Task specification | Primarily instructions and context | Instructions plus concrete examples |
| Context consumption | Usually lower | Higher |
| Specialized conventions | Must be communicated through instructions or other context | Can be demonstrated directly |
| Sensitivity to example quality | No demonstration-specific risk | Incorrect examples can mislead |
| Maintenance | Often simpler | Examples require curation and updates |

Few-shot prompting is most useful when the additional information provided by examples outweighs their cost and potential for introducing bias.

A strong zero-shot prompt may outperform a poorly designed few-shot prompt.

## 7. Experimental Design

To measure the value of demonstrations, compare zero-shot and few-shot variants under controlled conditions.

### Research question

Do demonstrations improve classification performance on inputs that were not included in the prompt?

### Experimental variants

**Variant A — Zero-shot**

Provide the task definition and the target input without examples.

**Variant B — Few-shot**

Use the same task definition and target input, adding a fixed set of labeled demonstrations.

### Controls

Keep the following consistent where possible:

- Model version
- Task instructions
- Target inputs
- Inference settings
- Output contract
- Evaluation procedure

Only the presence or composition of the demonstrations should change in the initial comparison.

### Evaluation metrics

For classification, consider:

- Accuracy
- Macro F1
- Per-class precision and recall
- Output-format compliance
- Performance on borderline examples

Use held-out evaluation cases that are distinct from the demonstrations. Otherwise, results may overstate generalization.

## 8. Failure Modes

| Failure mode | Cause | Mitigation |
|---|---|---|
| Misleading demonstrations | Examples contain incorrect labels or patterns | Verify and audit demonstrations |
| Poor coverage | Important classes or edge cases are absent | Select representative examples |
| Example overfitting | Examples are too narrow or repetitive | Evaluate on diverse held-out inputs |
| Order sensitivity | Performance varies with demonstration ordering | Test alternative orderings |
| Context overload | Too many demonstrations consume available context | Measure marginal benefit per example |
| Inconsistent labels | Demonstrations use conflicting annotation rules | Establish a consistent labeling policy |
| Example leakage | Evaluation cases overlap with demonstrations | Separate demonstration and evaluation data |

## 9. Efficiency and Context Budget

Each demonstration consumes input tokens, potentially increasing inference cost and latency.

The value of an additional example should therefore be evaluated against its marginal cost.

A practical selection objective is to maximize task performance subject to constraints on context length, latency, and budget.

More demonstrations do not necessarily lead to better performance. Redundant or misleading examples can make a prompt less effective.

## 10. When to Use Few-Shot Prompting

Consider few-shot prompting when:

- A task has specialized conventions that are difficult to describe concisely.
- The desired output pattern is easier to demonstrate than explain.
- Zero-shot performance is inadequate on a representative evaluation set.
- Reliable, representative examples are available.
- The improvement justifies the additional context and maintenance costs.

Prefer zero-shot prompting when it already meets the required quality threshold and demonstrations do not provide meaningful additional value.

## 11. Key Takeaways

Few-shot prompting uses in-context demonstrations to communicate task behavior through examples rather than relying exclusively on instructions.

Its effectiveness depends on example quality, diversity, consistency, ordering, and relevance to the target task.

The correct comparison is not whether a few-shot prompt looks more sophisticated. It is whether demonstrations improve performance on held-out data enough to justify their cost and complexity.

## References

- [Brown et al. (2020), Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)
- [OpenAI Prompt Engineering Guide](https://developers.openai.com/api/docs/guides/prompt-engineering/)
- [Liu et al. (2022), What Makes Good In-Context Examples for GPT-3?](https://arxiv.org/abs/2101.06804)
