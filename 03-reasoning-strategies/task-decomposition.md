# Task Decomposition for LLM Systems

## 1. Overview

Task decomposition is the process of breaking a complex objective into smaller, more manageable subtasks with explicit inputs, outputs, and dependencies.

Instead of asking a model to solve an entire problem in one prompt, a system can organize the work into stages, validate intermediate results, and combine them into a final response.

A decomposed workflow can improve reliability when the original task requires multiple distinct operations. However, decomposition also introduces orchestration overhead, additional model calls, intermediate-state errors, and opportunities for information loss.

The goal is not to maximize the number of steps. It is to identify the smallest useful structure that makes the task easier to execute, validate, and maintain.

## 2. When to Decompose a Task

Decomposition is useful when a task has one or more of the following properties:

- It contains distinct subproblems with different success criteria.
- Some operations depend on the results of earlier operations.
- Intermediate results can be validated independently.
- Different subtasks benefit from different prompts, tools, models, or context.
- The task exceeds the practical context or reliability limits of a single interaction.
- Failures need to be isolated, retried, or audited.

For example, producing a technical report from several documents may require:

1. Identifying the relevant documents.
2. Extracting claims and supporting evidence.
3. Resolving conflicts between sources.
4. Organizing the findings.
5. Drafting the report.
6. Checking factual support and output requirements.

Each stage has a distinct purpose and can be evaluated separately.

Decomposition is less useful when the task is simple, the subtasks are tightly coupled, or intermediate results cannot be meaningfully checked. A direct prompt may be cheaper and more reliable in those cases.

## 3. Common Decomposition Strategies

### 3.1 Sequential decomposition

Subtasks execute in a defined order. Each stage consumes the output of a previous stage.

Example:

`Extract data → Normalize fields → Validate records → Generate summary`

Use sequential decomposition when later stages require earlier results.

**Risk:** An early error can propagate through every downstream stage. Validate critical intermediate outputs before continuing.

### 3.2 Parallel decomposition

Independent subtasks execute separately, and their outputs are combined later.

Example:

`Analyze document A ─┐`

`Analyze document B ─┼→ Synthesize findings`

`Analyze document C ─┘`

Use parallel decomposition when tasks do not depend on one another and can be evaluated independently.

**Risk:** Parallel outputs may use inconsistent assumptions, overlap, or contradict one another. Define shared output contracts and include a reconciliation stage.

### 3.3 Hierarchical decomposition

A large objective is divided into major subtasks, which may themselves be divided into smaller tasks.

For example:

- Research a technical topic.
  - Identify major concepts.
  - Compare approaches.
    - Compare performance.
    - Compare implementation complexity.
  - Summarize trade-offs.
  - Produce recommendations.

Use hierarchical decomposition when a task has multiple levels of structure or scope.

**Risk:** Excessive hierarchy creates orchestration complexity and makes it difficult to trace how local decisions affect the final objective.

### 3.4 Adaptive decomposition

The system decides which subtask to execute next based on intermediate results.

For example, an information-extraction workflow may inspect a document first, then choose a specialized extraction path depending on whether the document contains tables, narrative text, or both.

Use adaptive decomposition when the required steps depend on information that is not known in advance.

**Risk:** Dynamic routing can make behavior less predictable. Bound the available actions, define stopping conditions, and log routing decisions.

## 4. Design the Decomposition Before Writing Prompts

A reliable workflow starts with the task structure, not with a collection of independently written prompts.

For each proposed subtask, specify:

| Property | Design question |
|---|---|
| Objective | What must this stage accomplish? |
| Inputs | What information does it need? |
| Output contract | What exact structure must it return? |
| Dependencies | Which stages must finish first? |
| Validation | How will success or failure be detected? |
| Recovery | Can the stage be retried or handled another way? |
| Completion condition | What determines that the stage is finished? |

These specifications reduce ambiguity between stages and make the workflow easier to test.

### Dependency graph

Represent the workflow as a directed graph:

- Nodes represent subtasks.
- Edges represent data dependencies.
- A node can execute when its required inputs are available.
- Independent nodes may execute concurrently.

A directed acyclic graph (DAG) is useful for workflows with fixed dependencies. Workflows with conditional branches or repeated actions may require a state machine or another explicit control-flow model.

Avoid adding dependencies that are not required. Unnecessary dependencies increase latency and reduce opportunities for parallel execution.

## 5. Choose the Right Granularity

Decomposition granularity determines how much work each subtask performs.

**Tasks that are too broad** can reproduce the original problem at a smaller scale. They may still be difficult to validate and may mix operations with different requirements.

**Tasks that are too narrow** create too many calls, increase orchestration overhead, and can lose important context across boundaries.

A useful subtask generally has:

- One primary objective.
- A bounded input scope.
- A verifiable output.
- A clear relationship to the overall objective.

A practical rule is to split a stage when its operations have meaningfully different validation requirements, context needs, failure modes, or retry behavior.

Do not split a task merely because it contains several sentences or can be expressed as a numbered list.

## 6. Intermediate Outputs and Contracts

Intermediate outputs are the interface between stages. Their quality affects the entire workflow.

Prefer explicit, machine-readable contracts when downstream processing depends on predictable fields.

For example, a document-analysis stage might return:

```json
{
  "document_id": "doc-17",
  "claims": [
    {
      "claim": "The service supports batch processing",
      "evidence": "Relevant source excerpt",
      "source_location": "section 2",
      "confidence": "medium"
    }
  ],
  "unresolved_questions": []
}
```

The contract should define required fields, permitted types, missing-value behavior, and how uncertainty is represented.

A downstream stage should not have to infer whether a missing field means “not found,” “not checked,” or “failed to process.”

### Separate extraction from interpretation

When factual traceability matters, separate the collection of evidence from the interpretation of that evidence.

For example:

1. Extract a claim and its source location.
2. Validate that the source location exists.
3. Ask a synthesis stage to compare supported claims.
4. Require the final report to preserve the connection between conclusions and evidence.

This structure makes it easier to detect unsupported conclusions than a workflow that immediately turns raw material into polished prose.

## 7. Context Management Across Stages

Passing the entire conversation or every previous output to every stage is often inefficient.

Instead, pass the minimum context required for the next operation, while preserving information that affects correctness.

Useful context may include:

- The overall objective.
- Relevant source material.
- The current subtask's instructions.
- Required terminology and assumptions.
- Validated intermediate results.
- Output and safety constraints.

Do not discard context merely to reduce token usage. Removing a qualification, exception, or source citation can make a later result incorrect.

For long workflows, retain a compact state representation that distinguishes confirmed facts, unresolved questions, decisions, and assumptions. When necessary, keep links or identifiers that allow the system to retrieve the original evidence.

## 8. Error Propagation and Recovery

A decomposed workflow can fail at multiple levels:

- **Subtask failure:** A stage produces an invalid or incomplete output.
- **Interface failure:** A stage returns data that violates the next stage's contract.
- **Dependency failure:** A required input is unavailable.
- **Synthesis failure:** Individually valid outputs are combined incorrectly.
- **Control-flow failure:** The workflow repeats unnecessarily or stops too early.
- **Objective drift:** The sequence of local tasks no longer satisfies the original goal.

Use validation gates at important boundaries.

A robust workflow should distinguish between:

1. A valid result.
2. A valid result with uncertainty.
3. A recoverable failure.
4. An unrecoverable failure.

Retries should be bounded. Repeating the same prompt without changing the input, instructions, or execution strategy may simply reproduce the same error.

When possible, retry only the failed stage rather than rerunning the entire workflow. This requires intermediate results to be stored and stages to have well-defined inputs and outputs.

## 9. Example: Research-to-Report Pipeline

Suppose the objective is to produce a technical comparison of three approaches using supplied documents.

### Stage 1: Plan

Identify the approaches, evaluation criteria, required sources, and final report format.

**Validation:** Every approach has a defined comparison scope.

### Stage 2: Extract evidence

Process each document independently and return relevant claims, evidence excerpts, and source locations.

**Validation:** Required fields exist and source references are traceable.

### Stage 3: Normalize

Map equivalent concepts to common comparison criteria without discarding meaningful differences.

**Validation:** Each normalized entry can be traced to its original evidence.

### Stage 4: Compare

Identify similarities, differences, trade-offs, and missing evidence across approaches.

**Validation:** Each major comparison is supported by the extracted material.

### Stage 5: Draft

Generate the report using the validated comparison and required structure.

**Validation:** All requested sections are present and conclusions reflect the evidence.

### Stage 6: Audit

Check factual support, consistency, completeness, and formatting.

**Validation:** Unsupported claims are removed, qualified, or flagged for further investigation.

This pipeline illustrates how decomposition creates separate quality checkpoints. It does not guarantee correctness: the extraction stage can miss evidence, normalization can distort meaning, and the final audit can overlook errors. Evaluation must test the complete pipeline as well as its individual stages.

## 10. Evaluation

Evaluate decomposition at both the stage level and the end-to-end level.

| Metric | What it measures |
|---|---|
| End-to-end task success | Whether the final result meets the original requirements |
| Stage success rate | How often each subtask meets its contract |
| Interface validity | Whether intermediate outputs satisfy their schemas |
| Error propagation rate | How often an upstream failure causes downstream errors |
| Recovery success rate | How often retries or fallback paths resolve failures |
| Latency | Time required to complete the workflow |
| Token and tool cost | Resources consumed across all stages |
| Traceability | Whether final claims can be connected to supporting inputs |

Compare the decomposed workflow with a direct-prompt baseline using the same test cases and evaluation criteria.

A decomposition is worthwhile when its improvement in reliability, quality, controllability, or maintainability justifies its additional cost and latency.

Use representative test cases, including ambiguous inputs, missing information, contradictory sources, malformed intermediate outputs, and unusually large tasks.

## 11. Common Failure Modes

### Over-decomposition

**Problem:** Too many stages create latency, cost, and maintenance overhead.

**Improvement:** Merge stages that share the same inputs, validation criteria, and recovery strategy.

### Under-decomposition

**Problem:** One stage performs several unrelated operations, making failures hard to diagnose.

**Improvement:** Split stages at meaningful changes in objective, context, or validation.

### Lossy intermediate summaries

**Problem:** A summary omits exceptions, qualifications, or evidence needed later.

**Improvement:** Preserve critical facts, uncertainty, and source references; retain access to original inputs.

### Incompatible output formats

**Problem:** Downstream prompts interpret fields inconsistently or depend on unstructured prose.

**Improvement:** Define explicit contracts and validate them before passing results forward.

### Blind synthesis

**Problem:** The final stage combines contradictory outputs without resolving them.

**Improvement:** Add a reconciliation step that identifies conflicts and requires evidence or explicit uncertainty.

### Local optimization

**Problem:** Every stage performs well on its own metric, but the final result misses the original objective.

**Improvement:** Maintain end-to-end acceptance criteria and test the full workflow.

### Unbounded orchestration

**Problem:** Conditional paths, retries, or agent actions continue without a clear stopping condition.

**Improvement:** Define step limits, retry limits, exit conditions, and failure escalation.

## 12. Relationship to Other Techniques

Task decomposition is a general workflow design strategy. It can be combined with other prompting techniques:

- **Chain-of-thought prompting:** Encourages reasoning-oriented responses within a task. Decomposition instead changes how work is partitioned and executed.
- **Least-to-most prompting:** Solves simpler subproblems before tackling more complex ones in a structured progression.
- **Prompt chaining:** Connects prompts so that one stage's output becomes another stage's input.
- **Tool calling:** Delegates suitable subtasks to external functions or systems.
- **Retrieval-augmented generation:** Supplies relevant external information to selected stages.
- **Self-consistency:** Compares multiple candidate outputs or reasoning paths for selected subtasks.
- **Structured output:** Makes intermediate interfaces more predictable and easier to validate.

These techniques solve different problems and can be combined when the added complexity is justified.

## 13. Implementation Checklist

Before deploying a decomposed workflow, verify that:

- [ ] The overall objective and end-to-end acceptance criteria are explicit.
- [ ] Every subtask has a clear purpose and bounded scope.
- [ ] Dependencies and execution order are documented.
- [ ] Intermediate output contracts are defined.
- [ ] Important outputs are validated before downstream use.
- [ ] Uncertainty, missing data, and failure states are distinguishable.
- [ ] Context is preserved across stage boundaries.
- [ ] Retries and fallback paths are bounded.
- [ ] Intermediate results can be inspected and failures traced.
- [ ] End-to-end quality is measured against a direct-prompt baseline.
- [ ] Latency and cost are justified by measurable benefits.

## 14. Key Takeaways

Task decomposition makes complex LLM workflows easier to manage by separating objectives, defining interfaces, and introducing validation points.

Its effectiveness depends on choosing appropriate boundaries, preserving critical context, controlling error propagation, and evaluating the complete workflow.

The central principle is to decompose around meaningful dependencies and quality checks—not simply to create more prompts.
