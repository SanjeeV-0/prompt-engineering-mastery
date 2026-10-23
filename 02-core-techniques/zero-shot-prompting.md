# Zero-Shot Prompting

## 1. Overview

Zero-shot prompting is a prompting approach in which a model is asked to perform a task without being given task-specific input-output examples in the prompt.

The model relies on its pretrained capabilities, the supplied instructions, the provided input, and any available context to generate a response.

Zero-shot does not mean that the model has never encountered similar tasks during training. It means that the current prompt does not provide demonstrations of the desired task behavior.

Zero-shot prompting is commonly used for classification, extraction, summarization, transformation, question answering, and other tasks that can be described directly.

## 2. Mechanism

Language models generate outputs conditioned on their input and model parameters. Instructions help define the desired task, while context and input data supply information needed to perform it.

A zero-shot prompt typically contains:
- A task instruction
- The task input
- Optional context
- Optional constraints and output specifications

It does not include explicit demonstrations of the task's expected input-output mapping.

For example:

```text
Classify the sentiment of the following review as positive,
neutral, or negative.

Review: The battery lasts all day, but the screen is difficult
to read outdoors.

Return only the label.
```

The model must infer how to apply the requested classification scheme from the instruction and its learned capabilities.

## 3. Instruction Specificity

Zero-shot performance can depend heavily on how the task is specified.

### Underspecified prompt

```text
Analyze this review:

"The battery lasts all day, but the screen is difficult
to read outdoors."
```

The model has no explicit task or output requirements.

### Task-specific prompt

```text
Classify the overall sentiment of the review as positive,
neutral, or negative.

Review:
"The battery lasts all day, but the screen is difficult
to read outdoors."

Return exactly one label from the permitted categories.
```

The second prompt defines the task, available labels, input, and output format.

Whether this improves task accuracy must be measured. Clearer instructions can improve compliance, but ambiguity in the label definitions may remain.

## 4. Suitable Use Cases

Zero-shot prompting is a useful starting point when:

- The task is familiar and can be described clearly.
- The output requirements are straightforward.
- No specialized demonstration examples are available.
- Low setup cost and prompt simplicity are priorities.
- A baseline is needed before trying more complex techniques.

Examples include:
- Summarizing a passage
- Extracting a date from text
- Classifying a clearly defined category
- Rewriting text in a specified tone
- Converting text into a simple structured representation

For high-stakes or highly specialized tasks, zero-shot output should not be assumed reliable without task-specific evaluation.

## 5. Failure Modes

### 5.1 Ambiguous instructions

An instruction such as "classify this message" does not define the label set or the decision policy.

**Mitigation:** specify the categories and how uncertain cases should be handled.

### 5.2 Undefined terminology

Terms such as "urgent," "high quality," or "relevant" may have multiple reasonable interpretations.

**Mitigation:** define operational criteria or supply examples when necessary.

### 5.3 Domain-specific conventions

The model may not infer a specialized taxonomy or organization-specific policy correctly.

**Mitigation:** provide authoritative definitions, relevant context, or demonstrations.

### 5.4 Output inconsistency

The model may produce explanations, alternative labels, or malformed structured output when a strict format is required.

**Mitigation:** state the output contract and validate the response programmatically.

### 5.5 Unsupported inference

The model may fill gaps in the input with plausible assumptions.

**Mitigation:** define how missing information should be handled and verify important claims.

## 6. Zero-Shot Versus Few-Shot Prompting

| Dimension | Zero-shot | Few-shot |
|---|---|---|
| Task examples in prompt | None | One or more |
| Prompt complexity | Usually lower | Usually higher |
| Demonstration overhead | None | Requires example selection |
| Specialized conventions | May need detailed instructions | Examples may clarify conventions |
| Main risks | Ambiguity and underspecification | Poor examples, bias, and example sensitivity |
| Evaluation requirement | Required | Required |

Few-shot prompting is not automatically better. Examples can improve task alignment but may also introduce misleading patterns or consume valuable context.

Choose the simplest approach that satisfies the task's quality and reliability requirements.

## 7. Evaluation Methodology

A zero-shot prompt should be evaluated against a predefined test set rather than a handful of favorable examples.

For a classification task, useful measurements include:

- Accuracy against labeled reference data
- Precision and recall for important classes
- Macro F1 when class balance matters
- Output-format compliance
- Performance on ambiguous and out-of-distribution inputs
- Latency and token usage

For extraction or summarization, the metrics should match the task. Exact-match accuracy may be appropriate for canonical fields, while factual consistency or human review may be needed for generated summaries.

### Controlled comparison

When comparing two zero-shot prompt variants:

1. Use the same model version.
2. Keep inference settings constant.
3. Use the same test inputs.
4. Define scoring criteria before inspecting results.
5. Preserve raw outputs.
6. Report aggregate metrics and representative failures.

A prompt that performs well on a small test set may not generalize to production inputs.

## 8. Example Experimental Design

### Research question

Does explicitly specifying the permitted labels improve classification reliability?

### Baseline

```text
Classify the review:

"The battery lasts all day, but the screen is difficult
to read outdoors."
```

### Variant

```text
Classify the overall sentiment as positive, neutral, or
negative. Return exactly one permitted label.

Review:
"The battery lasts all day, but the screen is difficult
to read outdoors."
```

### Measurements

- Whether the output is a permitted label
- Whether the label matches a predefined reference
- Whether performance is consistent across the test set

### Interpretation

If the second prompt produces more valid labels, that is evidence of improved format compliance.

It is not sufficient evidence of improved classification accuracy unless the correctness metric also improves.

No empirical result should be claimed until the experiment has actually been executed.

## 9. Advanced Considerations

### Model dependence

Different models may respond differently to the same prompt because of differences in training, instruction tuning, architecture, and inference behavior.

A zero-shot prompt should be evaluated against the actual deployment model.

### Inference configuration

Sampling parameters, output-token limits, and other generation settings can affect observed behavior. Comparisons should control these settings wherever possible.

### Cost and latency

Zero-shot prompting often requires fewer input tokens than few-shot prompting, but actual cost and latency depend on the model, provider, output length, and surrounding system.

### Security

A zero-shot instruction does not establish a security boundary. Applications that process untrusted content must enforce permissions, validate tool calls, and protect sensitive information outside the prompt.

## 10. Key Takeaways

Zero-shot prompting is the simplest useful baseline for many language-model tasks. It relies on explicit instructions, available context, and the model's existing capabilities rather than task demonstrations in the prompt.

Its strengths are simplicity and low demonstration overhead. Its weaknesses include ambiguity, inconsistent compliance, and limited adaptation to specialized conventions.

The correct engineering workflow is to establish a zero-shot baseline, evaluate it against representative data, and introduce additional techniques only when evidence shows they are needed.

## References

- [OpenAI Prompt Engineering Guide](https://developers.openai.com/api/docs/guides/prompt-engineering/)
- [Anthropic: Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Brown et al. (2020), Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)
