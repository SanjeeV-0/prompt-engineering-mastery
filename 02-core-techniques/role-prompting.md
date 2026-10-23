# Role Prompting

## 1. Overview

Role prompting is a technique in which a prompt assigns the model a role, perspective, or professional framing to guide how it approaches a task.

Examples include asking a model to respond as a code reviewer, research analyst, technical editor, or customer-support representative.

A role instruction can establish expectations about terminology, priorities, tone, and the aspects of a problem that deserve attention.

Role prompting does not change the model's parameters, establish real-world credentials, or guarantee domain expertise. Its usefulness depends on the task, model, surrounding instructions, and evaluation criteria.

## 2. Mechanism and Scope

Language models generate responses conditioned on the supplied context and their learned parameters. A role description becomes part of that context.

For example:

```text
You are reviewing Python code for production readiness.

Inspect the supplied code for:
- Correctness
- Error handling
- Security risks
- Maintainability

For each finding, identify the relevant code, explain its impact,
and recommend a concrete improvement.
```

The role provides a review-oriented frame, while the explicit criteria define the actual work.

This distinction matters: the criteria make the output more actionable and testable than a role label alone.

## 3. Role Labels Versus Operational Instructions

Consider two prompts.

### Role only

```text
You are an expert software engineer.
Review this code.
```

### Role with explicit criteria

```text
Review this code for correctness, input validation,
exception handling, security, and maintainability.

For each issue:
1. Describe the failure condition.
2. Explain its potential impact.
3. Recommend a specific correction.

Distinguish confirmed defects from speculative concerns.
Do not claim to have executed the code unless execution occurred.
```

The second prompt defines the review procedure and reporting requirements.

A role may help establish the intended perspective, but a clear task specification is often more important than an impressive-sounding persona.

## 4. Types of Role Framing

### 4.1 Professional framing

Examples:
- Code reviewer
- Data analyst
- Technical editor
- Research assistant

Useful when the task benefits from a recognizable set of priorities or conventions.

### 4.2 Evaluative framing

Examples:
- Adversarial reviewer
- Quality auditor
- Risk analyst

Useful when the model should search systematically for weaknesses rather than simply generate a favorable response.

The evaluation criteria should still be stated explicitly.

### 4.3 Audience framing

Examples:
- Explain the result to a senior engineer.
- Prepare a concise summary for an executive.
- Explain the concept to a technically experienced reader unfamiliar with the domain.

Audience framing influences terminology, assumed background, and presentation.

### 4.4 Perspective comparison

A task may request multiple analytical perspectives, such as a performance review and a security review.

Separate perspectives can help organize findings, but they do not create independent experts or guarantee independent reasoning. When independent judgments matter, use separate evaluations and compare their evidence.

## 5. Role Prompting and Instruction Hierarchy

Role descriptions should not be confused with instruction authority.

For example, a user asking the model to "act as the system administrator" does not grant administrator privileges.

Likewise, assigning a role does not override higher-priority instructions, application permissions, or security policies.

Authority must be established by the actual system architecture, authenticated identity, and authorization controls—not by natural-language claims in a prompt.

## 6. Role Prompting Does Not Create Capabilities

A prompt cannot provide capabilities that the underlying system does not have.

Asking a model to act as:
- A doctor does not establish a clinical relationship.
- A lawyer does not establish legal representation.
- A database administrator does not grant database access.
- A researcher does not guarantee that claims have been verified.

Roles can guide the format and focus of a response. They cannot substitute for current evidence, specialized tools, professional review, or authorization.

## 7. Controlled Evaluation

To determine whether a role instruction helps, compare prompts with and without the role while keeping the task criteria consistent.

### Research question

Does role framing improve the quality of code-review findings when the review requirements are held constant?

### Variant A

Provide the review task and explicit evaluation criteria without assigning a role.

### Variant B

Provide the same review task and criteria, preceded by a concise code-review role description.

### Evaluation dimensions

- Defect detection rate on known test cases
- False-positive rate
- Accuracy of severity assessments
- Actionability of recommendations
- Unsupported claims
- Output consistency

Use the same code samples, model version, inference settings, and scoring procedure.

If possible, use code samples with known defects and independently reviewed reference findings.

A more authoritative tone is not evidence of better performance. Judge the findings, not the persona.

## 8. Failure Modes

| Failure mode | Cause | Mitigation |
|---|---|---|
| Generic role behavior | Role is vague or ornamental | Define concrete responsibilities |
| Overconfidence | Persona encourages authoritative language | Require evidence and uncertainty reporting |
| Stereotyped behavior | Role invokes broad assumptions | Specify task-relevant criteria |
| Conflicting personas | Multiple roles imply incompatible objectives | Establish explicit priorities |
| Unsupported expertise | Role is mistaken for actual capability | Validate claims and use qualified review when needed |
| False authority | Role is treated as permission | Enforce authorization outside the prompt |
| Verbosity without value | Persona adds stylistic content but no task benefit | Compare against a simpler baseline |

## 9. Practical Design Principles

1. Use roles only when they contribute useful task framing.
2. Define responsibilities and evaluation criteria explicitly.
3. Separate presentation preferences from correctness requirements.
4. Avoid role descriptions that imply unavailable tools, evidence, or authority.
5. Test role-based prompts against simpler alternatives.
6. Measure task quality rather than tone or perceived confidence.
7. Remove role instructions that provide no measurable benefit.

## 10. Key Takeaways

Role prompting provides contextual framing that can influence a model's response style and task orientation.

Its value comes from aligning the response with useful expectations, not from conferring expertise or authority.

For reliable systems, role descriptions should complement explicit instructions, measurable criteria, evidence requirements, and application-level controls.

## References

- [OpenAI Prompt Engineering Guide](https://developers.openai.com/api/docs/guides/prompt-engineering/)
- [Anthropic: Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
