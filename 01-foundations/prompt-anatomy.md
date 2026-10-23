# Prompt Anatomy

## 1. Overview

A prompt is the structured input provided to a language model to condition its next output. It can contain instructions, contextual information, task data, examples, constraints, and output specifications.

Prompt engineering is the process of designing and refining these inputs to improve task performance, reliability, and controllability.

A prompt is not merely a question. It is an interface between the intended task and the model's learned behavior.

The effectiveness of a prompt depends on the model, the task, the available context, the inference configuration, and the criteria used to evaluate the result.

## 2. Structural Components

A prompt may contain the following components. These are conceptual building blocks, not mandatory fields or a universal serialization format.

### 2.1 Instructions

Instructions define the operation the model should perform.

Examples:
- Classify a customer review.
- Extract named entities from a document.
- Summarize a technical report.
- Transform unstructured text into a specified schema.

Effective instructions identify the intended task and make important requirements explicit.

Ambiguous instruction:

> Analyze this document.

More specific instruction:

> Extract the document's main claims, supporting evidence, and explicitly stated limitations. Return one entry for each claim.

The second instruction narrows the expected operation and gives the response a clearer evaluation target.

### 2.2 Context

Context supplies information needed to interpret the task correctly.

Examples include:
- Domain definitions
- Business rules
- User preferences
- Conversation history
- Retrieved documents
- Relevant application state

Context should be selected for relevance, not simply maximized. Irrelevant or contradictory context can distract the model or introduce ambiguity.

### 2.3 Input Data

Input data is the material on which the model operates.

Examples:
- A customer review
- A code snippet
- A contract excerpt
- A collection of retrieved passages
- A structured record

Separating task instructions from input data makes prompts easier to understand, test, and maintain.

For applications processing untrusted input, the boundary between instructions and data must also be enforced through appropriate system design. Delimiters alone are not a security guarantee.

### 2.4 Constraints

Constraints specify acceptable behavior or limit the solution space.

Common constraints include:
- Maximum output length
- Permitted categories
- Required fields
- Allowed operations
- Prohibited assumptions
- Required handling of missing information

Constraints should be relevant and verifiable. Unnecessary constraints can reduce flexibility or introduce conflicting requirements.

### 2.5 Output Contract

An output contract specifies the expected response structure and, where appropriate, semantic requirements.

For example:

```json
{
  "category": "billing",
  "priority": "high",
  "reason": "The customer reports an incorrect charge."
}
```

For machine-consumed outputs, use schema validation, constrained decoding, or structured-output features when supported. Instructions requesting JSON do not by themselves guarantee valid JSON.

An output contract should define:
- Required fields
- Field types
- Allowed values
- Missing-value behavior
- Validation requirements

### 2.6 Examples

Examples demonstrate the desired relationship between inputs and outputs.

They are particularly useful when the task involves:
- A specialized label taxonomy
- Domain-specific conventions
- A subtle output format
- A task that is difficult to describe completely in prose

Examples introduce their own risks. Poorly selected or inconsistent examples can teach unintended patterns, bias outputs, or reduce generalization.

## 3. A Conceptual Prompt Model

A useful way to reason about prompt design is:

**Prompt = Instructions + Relevant Context + Input Data + Constraints + Output Contract**

Examples may be added when they provide useful demonstrations.

This is a conceptual model rather than a literal requirement. A simple task may need only an instruction and input, while a complex application may assemble context dynamically and enforce output requirements outside the prompt.

## 4. Message Structure and Instruction Boundaries

Modern language-model applications often use structured conversations rather than a single text string.

A conversation may contain messages associated with roles such as system, developer, user, and assistant. Tool interactions may introduce additional messages.

These roles are not interchangeable.

- System and developer instructions can establish application behavior and constraints.
- User messages provide requests and task-specific input.
- Assistant messages contain model responses.
- Tool messages provide results from external operations.

The exact role semantics and precedence rules depend on the model and platform. Follow the relevant API documentation rather than assuming every model uses identical rules.

An instruction hierarchy is also not a complete security mechanism. Applications must still validate tool permissions, isolate untrusted content, and enforce access controls outside the model.

## 5. Prompt Design Example

Consider an application that classifies customer support messages.

### Input

"The subscription renewed twice, and I need the extra charge refunded."

### Prompt A: Underspecified

```text
Classify this message.
```

Potential problems:
- The label taxonomy is unspecified.
- The output format is unspecified.
- The meaning of classification is unclear.

### Prompt B: Structured

```text
Task:
Classify the customer message into exactly one category:
billing, technical_support, account_access, or other.

Instructions:
- Select the category that best represents the primary issue.
- Do not invent facts that are absent from the message.
- Return only the specified JSON object.

Output contract:
{
  "category": "<allowed category>",
  "reason": "<brief explanation based on the message>"
}

Customer message:
"The subscription renewed twice, and I need the extra charge refunded."
```

The intended category is `billing`.

Prompt B makes the taxonomy, decision objective, and output structure explicit. Whether it produces better results must still be tested against representative inputs.

## 6. Design Trade-Offs

### Specificity versus flexibility

More specific instructions can improve consistency on well-defined tasks, but excessive constraints can make prompts brittle or unsuitable for legitimate edge cases.

### Context completeness versus context overload

Additional context may resolve ambiguity, but irrelevant or conflicting information can impair performance and increase token consumption.

### Examples versus generalization

Examples can clarify conventions, but their selection and ordering may affect the model's behavior. Evaluation should include cases that differ from the examples.

### Prompt compliance versus task correctness

A response may satisfy every formatting requirement while being factually incorrect. Structural validity and semantic correctness must be evaluated separately.

## 7. Common Failure Modes

| Failure mode | Cause | Mitigation |
|---|---|---|
| Ambiguous task | Multiple plausible interpretations | Specify the intended operation |
| Missing context | Essential facts are unavailable | Supply relevant context or define a fallback |
| Conflicting instructions | Requirements cannot all be satisfied | Resolve conflicts explicitly |
| Invalid output | Requested structure is not enforced | Validate or constrain the output |
| Unsupported claims | The model fills gaps with plausible content | Require evidence, allow abstention, and verify claims |
| Context interference | Irrelevant or contradictory material | Improve context selection and organization |
| Prompt injection | Untrusted content attempts to influence behavior | Enforce trust boundaries and tool permissions outside the prompt |

## 8. Evaluation Principles

Prompt quality should be measured against task-specific criteria rather than subjective impressions alone.

A prompt evaluation should consider:

1. **Task correctness:** Does the response solve the intended problem?
2. **Instruction compliance:** Does it satisfy the requested requirements?
3. **Structural validity:** Does it conform to the output contract?
4. **Robustness:** Does performance hold across representative and adversarial inputs?
5. **Efficiency:** What are the latency, token usage, and cost implications?
6. **Safety:** Does the system respect privacy, authorization, and security requirements?

Use a fixed evaluation dataset when comparing prompt variants. Change one major variable at a time where practical, record the model and inference settings, and preserve the raw outputs.

## 9. Practical Design Checklist

Before deploying a prompt, verify that:

- The task is clearly defined.
- Necessary context is available.
- Input data is distinguishable from instructions.
- Important constraints are explicit.
- The output contract is testable.
- Missing or ambiguous information has a defined handling strategy.
- Untrusted input cannot independently authorize privileged actions.
- Evaluation includes representative edge cases.
- Model behavior and operational cost are measured.

## 10. Key Takeaways

Prompt anatomy provides a framework for reasoning about the inputs that condition model behavior.

The main engineering objective is not to maximize prompt length or complexity. It is to provide the information and constraints needed for a specific task while preserving flexibility where appropriate.

Prompt design is only one component of reliable LLM engineering. Retrieval, structured interfaces, validation, evaluation, and application-level security remain essential.

## References

- [OpenAI API Documentation](https://developers.openai.com/api/docs/)
- [OpenAI Prompt Engineering Guide](https://developers.openai.com/api/docs/guides/prompt-engineering/)
- [Anthropic: Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
