# Prompt Engineering Learning Roadmap

This roadmap provides a structured path for learning, practicing, and evaluating prompt engineering techniques, from foundational instruction design to advanced workflows and applied extraction tasks.

Progress through the phases in order, complete the practical exercises, and record measurable results in the `experiments/` and `evaluations/` directories.

## Phase 1: Foundations

- [ ] Understand prompt anatomy and the roles of instructions, context, inputs, and output requirements.
- [ ] Study instruction design, ambiguity reduction, and constraint specification.
- [ ] Learn how context and constraints influence model behavior.
- [ ] Establish a baseline using a small set of representative prompts.

**Milestone:** Design a clear prompt for a defined task and explain the purpose of each component.

## Phase 2: Core Prompting Techniques

- [ ] Practice zero-shot prompting.
- [ ] Practice few-shot prompting and example selection.
- [ ] Study role prompting and its limitations.
- [ ] Generate structured outputs using explicit schemas and output contracts.
- [ ] Compare prompting strategies on the same test cases.

**Milestone:** Demonstrate how different prompting techniques affect output quality and consistency.

## Phase 3: Reasoning and Task Decomposition

- [ ] Study reasoning-oriented prompting and its limitations.
- [ ] Apply task decomposition to complex requests.
- [ ] Explore least-to-most prompting.
- [ ] Experiment with self-consistency and multiple candidate solutions.
- [ ] Identify when decomposition improves performance and when it adds unnecessary complexity.

**Milestone:** Solve a multi-step task using a documented strategy and evaluate its results against a simpler baseline.

## Phase 4: Context Engineering and Retrieval

- [ ] Learn context selection, prioritization, and organization.
- [ ] Study long-context management and context compression.
- [ ] Understand retrieval-augmented generation (RAG).
- [ ] Evaluate how context relevance and quality affect responses.
- [ ] Test how missing, irrelevant, or conflicting evidence changes model behavior.

**Milestone:** Build a prompt-based task that uses supplied or retrieved evidence and handles missing information explicitly.

## Phase 5: Prompt Optimization and Efficiency

- [ ] Establish a repeatable manual prompt-optimization process.
- [ ] Explore automatic prompt-optimization methods.
- [ ] Measure token usage, latency, and cost.
- [ ] Compare prompt variants using a fixed evaluation dataset.
- [ ] Track improvements, regressions, and trade-offs.

**Milestone:** Improve a baseline prompt and document the changes with reproducible evaluation results.

## Phase 6: Evaluation and Robustness

- [ ] Understand evaluation fundamentals and baseline comparisons.
- [ ] Design representative test datasets.
- [ ] Implement task-specific metrics.
- [ ] Study LLM-as-a-judge evaluation and its limitations.
- [ ] Test robustness across paraphrases, edge cases, and ambiguous inputs.
- [ ] Analyze errors and variation across repeated runs.

**Milestone:** Create a repeatable evaluation process that measures quality, consistency, and failure modes.

## Phase 7: Reliability, Security, and Validation

- [ ] Study prompt injection and instruction/data boundaries.
- [ ] Learn output validation and schema enforcement.
- [ ] Understand data leakage and privacy risks.
- [ ] Test prompts against adversarial and malformed inputs.
- [ ] Distinguish prompt-level safeguards from application-level security controls.

**Milestone:** Demonstrate how a prompt-based workflow handles untrusted content and invalid outputs, with documented tests.

## Phase 8: Advanced Prompt Workflows

- [ ] Design prompt chains with explicit intermediate outputs.
- [ ] Study tool-calling prompts, tool descriptions, and argument schemas.
- [ ] Define tool-selection rules and missing-argument behavior.
- [ ] Evaluate intermediate results and error propagation.
- [ ] Compare multi-stage workflows with single-prompt baselines.

**Milestone:** Build a multi-step workflow that uses structured handoffs, validates intermediate results, and reports failures clearly.

## Phase 9: Applied Project

- [ ] Implement a structured information-extraction task.
- [ ] Define an output schema and missing-value policy.
- [ ] Validate extracted values against source evidence.
- [ ] Create a representative evaluation dataset.
- [ ] Measure field-level accuracy, output validity, and unsupported inference.
- [ ] Document the approach, results, limitations, and possible improvements.

**Milestone:** Deliver a reproducible information-extraction project with test cases and evaluation results.

## Final Completion Checklist

- [ ] Every core technique has been practiced, not merely read.
- [ ] At least one experiment compares alternative prompt designs.
- [ ] Evaluation results are reproducible and documented.
- [ ] Failure cases and limitations are explicitly recorded.
- [ ] At least one practical project demonstrates the techniques.
- [ ] The README links to the roadmap, experiments, evaluations, and project artifacts.

## Completion Criteria

The roadmap is complete when the techniques have been applied to practical tasks, evaluated against defined criteria, and documented with evidence of their strengths and limitations.

The objective is not simply to collect prompting techniques. It is to develop a repeatable process for designing, testing, evaluating, and improving prompts.