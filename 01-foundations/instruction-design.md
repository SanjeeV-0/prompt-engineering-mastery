# Instruction Design

## 1. Overview

Instruction design is the process of specifying a task so that a language model can interpret the intended operation, constraints, and success criteria with minimal ambiguity.

A well-designed instruction defines what the model should do, what information it should use, and what constitutes an acceptable result.

Instruction design is not about making prompts longer. It is about reducing uncertainty that matters to the task.

## 2. Task Specification

A useful instruction typically defines four elements:

- **Action:** the operation to perform.
- **Object:** the input or subject of that operation.
- **Constraints:** the requirements the response must satisfy.
- **Success criteria:** the properties of an acceptable result.

Example:

Underspecified:
> Analyze these support tickets.

Specified:
> Classify each support ticket into one of the supplied categories. Preserve the ticket ID, assign exactly one category, and return a JSON array conforming to the specified schema.

The second instruction narrows the task and makes important requirements testable.

Not every task needs all four elements explicitly. Simple requests may need only an action and an input.

## 3. Specificity and Ambiguity

An instruction is ambiguous when multiple materially different interpretations are reasonable.

Consider:

> Make this report better.

Possible interpretations include:
- Correct grammar.
- Shorten the report.
- Improve its organization.
- Strengthen the evidence.
- Change the tone for a different audience.

A more precise instruction identifies the intended transformation:

> Edit this report for clarity and grammatical correctness. Preserve its claims, evidence, and overall structure. Do not introduce new factual assertions.

The goal is to remove task-relevant ambiguity without unnecessarily restricting useful responses.

### Operational rule

Specify a requirement explicitly when different reasonable interpretations would produce meaningfully different outcomes.

Do not over-specify details that are irrelevant to success.

## 4. Positive Requirements and Negative Constraints

Positive requirements state what the model should do.

Examples:
- Extract the invoice number.
- Explain the decision.
- Return three candidate titles.

Negative constraints state what the model must avoid.

Examples:
- Do not invent missing invoice values.
- Do not change quoted text.
- Do not include fields outside the permitted schema.

Positive requirements define the intended result. Negative constraints help prevent known failure modes.

However, negative constraints alone are often insufficient.

Weak:
> Do not include irrelevant information.

Stronger:
> Include only information directly supported by the supplied document. If a requested field is absent, return null.

The stronger version provides an actionable alternative for handling missing information.

## 5. Instruction Precedence and Conflicts

A prompt may contain requirements that conflict with one another.

Example:

- Return exactly one sentence.
- Provide five separate bullet points.

These requirements cannot both be satisfied under the ordinary meaning of each instruction.

A robust design should resolve conflicts before the model executes the task.

### Design principles

1. Establish an explicit precedence policy for requirements within the task.
2. Remove contradictions wherever possible.
3. Distinguish mandatory constraints from preferences.
4. Define a fallback when a valid result cannot satisfy all requirements.
5. Validate critical requirements outside the model.

In multi-message applications, system, developer, and user messages may have platform-defined precedence. The precise hierarchy depends on the model interface and documented semantics.

Within an individual application prompt, do not assume that placing a requirement later automatically makes it authoritative. Define the intended priority explicitly.

## 6. Output Requirements as Contracts

Output requirements should be expressed in terms that can be checked.

Weak:
> Return a useful JSON response.

Stronger:
> Return a JSON object with the required keys `ticket_id`, `category`, and `priority`. The category must be one of `billing`, `technical_support`, `account_access`, or `other`.

For production systems, validate the output against a schema or use a supported structured-output mechanism.

A prompt instruction is not a substitute for validation. A response can violate its requested format even when the instruction is clear.

## 7. Missing Information and Abstention

Instructions should define what happens when the input is insufficient.

Without an explicit policy, a model may produce plausible but unsupported details.

Example:

> Extract the contract's effective date. If the date is not explicitly stated, return null. Do not infer it from the signature date.

This defines both the target field and the treatment of missing evidence.

For tasks where an incorrect answer is costly, consider an explicit abstention option, evidence requirements, and external verification.

## 8. Controlled Instruction Comparison

Compare the following variants.

### Variant A

> Classify this customer message.

### Variant B

> Classify this customer message into exactly one category: billing, technical_support, account_access, or other. If the message does not provide enough information to select a category, choose other. Return only the category label.

### Evaluation questions

- Does the model choose a permitted category?
- Does it return exactly one label?
- Does it handle ambiguous messages consistently?
- Does it incorrectly classify messages that fall outside the intended categories?

Use the same model, test inputs, and inference settings for both variants.

The comparison should measure task accuracy and instruction compliance separately. A response can follow the format perfectly while choosing the wrong category.

## 9. Common Failure Modes

| Failure mode | Cause | Design response |
|---|---|---|
| Vague objective | The task is underspecified | Define the intended operation |
| Over-constrained output | Unnecessary restrictions | Retain only requirements that matter |
| Conflicting requirements | Incompatible instructions | Resolve conflicts before execution |
| Unsupported inference | Missing-data behavior is undefined | Specify abstention or null handling |
| Format violations | Output rules are not enforced | Validate with a schema |
| Inconsistent interpretation | Important terms are undefined | Provide definitions or examples |
| Fragile instructions | Success depends on incidental wording | Test paraphrases and edge cases |

## 10. Engineering Principles

Effective instruction design follows several principles:

1. **Clarity over verbosity:** express the task directly.
2. **Explicitness over assumption:** state critical requirements.
3. **Testability over subjective quality:** define observable acceptance criteria.
4. **Flexibility where appropriate:** avoid unnecessary restrictions.
5. **Failure-aware design:** specify how ambiguity and missing information should be handled.
6. **Defense in depth:** enforce important constraints with code and system controls rather than relying solely on prompt wording.

## 11. Key Takeaways

Instruction design converts a broad request into a more precise task specification.

The objective is to reduce meaningful ambiguity, define acceptable behavior, and make failures easier to detect.

Well-designed instructions improve controllability, but they do not guarantee correctness. Reliable systems combine instruction design with evaluation, validation, and appropriate application-level controls.

## References

- [OpenAI API Documentation](https://developers.openai.com/api/docs/)
- [OpenAI Prompt Engineering Guide](https://developers.openai.com/api/docs/guides/prompt-engineering/)
- [Anthropic: Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
