# Output Validation for LLM Systems

## 1. Introduction

Output validation is the process of checking whether an LLM-generated response satisfies the structural, semantic, operational, and security requirements of the application before the response is accepted or used.

LLM outputs are not inherently trustworthy just because they appear well-formed. A model can return valid JSON containing incorrect values, produce a plausible answer that violates business rules, omit a required field, invent a citation, or generate tool arguments that exceed the user's permissions.

A reliable application therefore treats model output as **untrusted input to the next stage of the system**.

Output validation creates a boundary between probabilistic generation and deterministic application behavior. It can detect invalid outputs, prevent unsafe actions, trigger bounded recovery procedures, and produce measurable quality signals.

A robust validation pipeline typically checks:

1. Syntax and parseability
2. Structural and schema compliance
3. Type and field constraints
4. Semantic correctness
5. Business rules
6. Evidence and provenance
7. Security and authorization
8. Downstream action safety

Not every application needs every layer, but the required checks should be explicit rather than left to the model's discretion.

## 2. Why Prompt Instructions Are Not Enough

A prompt may instruct a model to return valid JSON, use only permitted labels, include every required field, or avoid unsupported claims. These instructions can improve behavior, but they do not guarantee compliance.

Potential failures include:

- Explanatory text surrounding a JSON object
- Missing required properties
- Incorrect field types
- Unexpected enum values
- Truncated output
- Unsupported factual claims
- Invalid citations
- Incorrect numerical calculations
- Unauthorized tool arguments
- Values that violate business rules

For example, this response is valid JSON:

```json
{
  "account_status": "approved",
  "approval_reason": "verified"
}
```

However, it may still be invalid if the application has not authorized the account, the verification never occurred, or the model invented the status.

The distinction is fundamental:

- **Generation** proposes an output.
- **Validation** checks whether the output is acceptable.
- **Authorization** determines whether an action is permitted.
- **Execution** performs the action.
- **Verification** checks what actually happened.

These responsibilities should not be collapsed into a single prompt.

## 3. A Layered Validation Architecture

A practical output-validation pipeline separates checks by purpose.

<box gap={2}>
  <box border radius="lg" padding={3} gap={1}>
    <title size="md">Layer 1 — Parsing</title>
    Determine whether the output can be decoded into the expected representation, such as JSON.
  </box>
  <box align="center">
    <icon name="arrow-down" size="lg" color="secondary" />
  </box>
  <box border radius="lg" padding={3} gap={1}>
    <title size="md">Layer 2 — Schema validation</title>
    Check required fields, types, allowed values, and structural constraints.
  </box>
  <box align="center">
    <icon name="arrow-down" size="lg" color="secondary" />
  </box>
  <box border radius="lg" padding={3} gap={1}>
    <title size="md">Layer 3 — Semantic and business validation</title>
    Verify domain rules, relationships between fields, numerical constraints, and task-specific meaning.
  </box>
  <box align="center">
    <icon name="arrow-down" size="lg" color="secondary" />
  </box>
  <box border radius="lg" padding={3} gap={1}>
    <title size="md">Layer 4 — Security and authorization</title>
    Check permissions, policy restrictions, resource ownership, and action scope.
  </box>
  <box align="center">
    <icon name="arrow-down" size="lg" color="secondary" />
  </box>
  <box border radius="lg" padding={3} gap={1}>
    <title size="md">Layer 5 — Controlled execution</title>
    Execute only validated and authorized operations, then verify the resulting state.
  </box>
</box>

A failure at any layer should prevent the output from silently progressing as though it were valid.

The order can vary depending on the application. For example, a system may need to validate response size before parsing, or apply security filtering before storing an intermediate result. The important requirement is that every necessary control runs before the relevant data is trusted or acted upon.

## 4. Syntax Validation

Syntax validation checks whether the output can be parsed according to its declared format.

For JSON, use a JSON parser rather than asking another model whether the text “looks like JSON.”

### Common JSON failures

- Single quotes used for strings
- Trailing commas
- Comments inside objects
- Unescaped control characters
- Truncated objects or arrays
- Multiple objects when exactly one is expected
- Markdown fences surrounding the JSON when the contract prohibits them
- Non-JSON values such as `NaN` or `Infinity` in implementations that reject them

### Python example

```python
import json


def parse_json_output(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("Model output must be a string.")

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON.") from exc

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object at the top level.")

    return result
```

This function establishes syntax and top-level type requirements. It does not validate field names, values, business rules, or factual correctness.

### Reject ambiguous encodings

Do not silently extract the first JSON-looking substring from an arbitrary response unless that behavior is explicitly part of the interface.

A response containing two objects or prose around an object may indicate that the model violated the output contract. Automatically accepting a fragment can conceal defects and create ambiguity about which content is authoritative.

If the application permits fenced JSON or another wrapper, implement that format deliberately and test it.

## 5. Schema Validation

Schema validation checks whether a parsed value conforms to a defined structure.

A JSON Schema can specify:

- Required properties
- Property types
- Enumerated values
- Minimum and maximum values
- String length limits
- Array item types
- Nested object structure
- Additional-property restrictions

### Example schema

```python
from jsonschema import Draft202012Validator

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "ticket_id": {
            "type": "string",
            "minLength": 1,
        },
        "category": {
            "type": "string",
            "enum": [
                "billing",
                "technical",
                "account",
                "other",
            ],
        },
        "priority": {
            "type": "integer",
            "minimum": 1,
            "maximum": 4,
        },
        "summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500,
        },
    },
    "required": [
        "ticket_id",
        "category",
        "priority",
        "summary",
    ],
    "additionalProperties": False,
}

validator = Draft202012Validator(RESPONSE_SCHEMA)


def validate_schema(payload: object) -> list[str]:
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]
```

Example use:

```python
payload = {
    "ticket_id": "T-1024",
    "category": "technical",
    "priority": 2,
    "summary": "The user cannot connect to the service.",
}

errors = validate_schema(payload)

if errors:
    raise ValueError(f"Schema validation failed: {errors}")
```

The schema is an executable contract. Changes to it should be versioned and tested because they can affect compatibility with existing prompts, clients, and stored records.

### Strictness and compatibility

`additionalProperties: False` rejects unexpected fields. This is useful when the interface must be exact, but it can make forward compatibility harder if the model begins returning new properties.

Choose strictness intentionally. Do not remove useful validation merely to make unexpected outputs pass.

## 6. Type Validation and Coercion

Models may return values in the wrong type.

Examples:

```json
{
  "quantity": "12",
  "is_active": "true",
  "score": 4.0
}
```

Whether these values are acceptable depends on the contract.

A string containing `"12"` is not automatically an integer. A string containing `"true"` is not a Boolean. A floating-point value such as `4.0` may or may not be acceptable where an integer is required.

### Coercion policy

If coercion is permitted:

1. Define the accepted source types.
2. Define the conversion rules.
3. Reject ambiguous values.
4. Check bounds after conversion.
5. Record whether coercion occurred.

Do not rely on permissive conversions that silently change meaning.

For example, converting `"12.5"` to an integer by truncation may corrupt a financial quantity. Converting `"unknown"` to zero may convert missing information into a false fact.

### Missing, null, and empty values

These states are not interchangeable:

- Property omitted: no value was supplied.
- `null`: the value is explicitly unavailable or unknown under the schema.
- Empty string: a string exists but contains no characters.
- Empty array: a collection exists but contains no elements.
- Zero: a numeric value equal to zero.
- `false`: a Boolean value representing false.

Define the intended meaning of each state for every important field.

## 7. Semantic Validation

Semantic validation determines whether the output makes sense in the context of the task.

An output can pass parsing and schema checks while containing contradictions or impossible values.

Examples include:

- An end date preceding a start date
- A subtotal inconsistent with line-item values
- A percentage outside the allowed range
- An invoice total inconsistent with verified records
- A summary that contradicts the source document
- A selected category inconsistent with required classification rules
- A citation that exists but does not support the associated claim

Semantic checks should be as deterministic as the task permits.

### Example: date relationship

```python
from datetime import date


def validate_date_range(
    start_date: date,
    end_date: date,
) -> list[str]:
    errors = []

    if end_date < start_date:
        errors.append("End date must not precede start date.")

    return errors
```

This check does not require an LLM. It uses a deterministic rule with a clearly defined interpretation.

### Evidence-based semantic checks

For evidence-grounded generation, validate whether the response's material claims are supported by the supplied sources.

Depending on the task, this can involve:

- Checking that citations refer to real source identifiers
- Verifying that quoted passages appear in the source
- Checking whether required facts are included
- Detecting contradictions between output and source
- Sending uncertain cases for independent review

An existing citation is not proof of support. A citation can point to the correct document while being irrelevant to the specific claim.

LLM-based verification may assist with difficult semantic cases, but it should itself be evaluated and should not replace deterministic checks where those are available.

## 8. Business-Rule Validation

Business rules encode application-specific constraints that may not fit naturally into a general schema.

Examples include:

- An order quantity must not exceed the available inventory.
- A requested account operation must be permitted for the authenticated user.
- A discount must not exceed the authorized maximum.
- A transaction amount must be within an allowed range.
- A report must include all required sections.
- A tool action must reference a resource that exists and belongs to the authorized tenant.

Implement these rules in trusted application code or an appropriate policy service.

Do not treat a model-generated statement such as `"authorized": true` as evidence of authorization. The application must independently verify permissions using trusted identity and policy data.

### Separate proposed actions from permitted actions

An LLM may propose an action, but that proposal should not automatically execute.

A safer sequence is:

1. Parse the proposed action.
2. Validate its schema.
3. Resolve resource identifiers using trusted data.
4. Check authorization.
5. Validate business rules.
6. Require approval if the action's risk level demands it.
7. Execute the operation.
8. Verify the actual result.

This separation is especially important for systems that send messages, modify records, create orders, or perform other operations with side effects.

## 9. Tool-Call Validation

Tool calls are structured requests from the model to external functions or services. They should be treated as untrusted proposals.

A valid tool-call payload does not establish that the tool should be invoked.

Validate:

- Tool name against an allowlist
- Argument structure and types
- Resource identifiers
- User authorization
- Permitted operation scope
- Rate and resource limits
- Whether the action is reversible
- Whether explicit user confirmation is required

### Example policy check

```python
ALLOWED_ACTIONS = {"lookup_ticket", "get_order_status"}


def validate_tool_request(request: object) -> list[str]:
    if not isinstance(request, dict):
        return ["Tool request must be an object."]

    errors = []

    action = request.get("action")
    arguments = request.get("arguments")

    if action not in ALLOWED_ACTIONS:
        errors.append("Action is not permitted.")

    if not isinstance(arguments, dict):
        errors.append("Arguments must be an object.")

    return errors
```

This example checks only a basic allowlist and argument container. Each tool needs its own schema, permission checks, and business rules.

For actions with external side effects, additional protections may include idempotency keys, explicit approval, transaction limits, and post-execution verification.

## 10. Output Validation for RAG Systems

Retrieval-augmented generation (RAG) systems introduce specific validation requirements because answers may depend on retrieved evidence.

A useful validation process separates:

1. Retrieval correctness
2. Evidence identity and provenance
3. Citation integrity
4. Claim support
5. Answer completeness
6. Abstention when evidence is insufficient

### Citation validation

For each citation:

- Confirm that the referenced source exists.
- Confirm that the source was available to the request.
- Verify that the citation points to the claimed passage or section.
- Check whether the passage supports the associated statement.
- Ensure that the user is authorized to access the cited source.

A citation that references an inaccessible document can itself leak sensitive information through identifiers, titles, or metadata.

### Evidence insufficiency

If the retrieved sources do not establish the answer, the application should follow its defined fallback behavior.

Depending on the task, that may mean asking a question, returning an explicit unknown value, searching again within a bounded policy, or escalating.

Do not treat the model's confidence or fluent explanation as evidence that the answer is grounded.

## 11. Validation Failure Handling

When validation fails, the system needs a controlled recovery strategy.

Common options include:

- Reject the output
- Retry generation
- Request a constrained correction
- Apply a deterministic repair
- Return a structured error
- Ask the user for missing information
- Escalate to a human reviewer

Choose the response according to the failure type.

| Failure | Suitable response |
|---|---|
| Invalid JSON | Bounded regeneration or format-specific repair |
| Missing required field | Regenerate or request missing information |
| Invalid enum value | Reject or regenerate with allowed values |
| Business-rule violation | Reject and investigate; do not blindly coerce |
| Unauthorized action | Block execution and record a security event |
| Insufficient evidence | Abstain, retrieve more evidence, or escalate |
| Contradictory source data | Surface the conflict or follow a documented resolution rule |
| External tool failure | Apply bounded retry or controlled fallback |

### Never silently repair high-impact data

Automatically changing an incorrect monetary amount, resource identifier, or authorization field can turn a visible model error into a hidden application error.

For high-impact values, prefer rejection and explicit resolution over speculative correction.

## 12. Bounded Retry and Repair

A retry can help when the failure is caused by a recoverable generation issue. However, retries can also increase cost, latency, and the chance of inconsistent results.

Use a bounded policy:

1. Validate the initial output.
2. Classify the failure.
3. Retry only if the failure is plausibly recoverable.
4. Provide concise, specific validation feedback.
5. Revalidate the complete new output.
6. Stop after a configured attempt limit.
7. Return a controlled failure if validation still fails.

A repair prompt should describe the violated contract without allowing untrusted output to rewrite system requirements.

For example:

```text
The previous response failed validation because the "priority"
field was outside the allowed range.

Return a corrected object that follows the original schema.
Use only permitted values. Do not invent missing facts.
If a required value cannot be established, follow the schema's
documented unknown-value rule.
```

The exact prompt should depend on the schema and task. Revalidation remains mandatory after every repair attempt.

## 13. Observability and Validation Metrics

Validation failures should be measured so the system can improve over time.

Useful metrics include:

- Parse success rate
- Schema-validity rate
- Semantic-validation pass rate
- Business-rule rejection rate
- Unauthorized-action rejection rate
- Retry frequency
- Recovery success rate
- Unresolved failure rate
- Average retries per request
- Latency and cost per successful task

Define each metric precisely. For example, schema validity should not include semantic correctness unless that aggregation is intentional.

Track failure categories separately. A high schema-validity rate can coexist with poor factual correctness.

### Useful diagnostic fields

For each request, record only the data necessary for diagnosis, such as:

- Request identifier
- Prompt and schema versions
- Validation stage
- Failure category
- Retry count
- Final outcome
- Latency
- Token usage

Avoid logging sensitive raw inputs or outputs unnecessarily.

## 14. Testing a Validation Pipeline

The validator is itself software and requires tests.

### Unit tests

Test individual rules with:

- Valid values
- Invalid values
- Boundary values
- Missing fields
- Unexpected types
- Null values
- Contradictory fields

### Integration tests

Verify that invalid outputs do not reach downstream components.

For example, test that an unauthorized tool request is rejected before the external service is invoked.

### Property-based tests

Generate many structured inputs and verify general invariants, such as:

- Invalid enum values are always rejected.
- Unknown properties are rejected when the schema is strict.
- Invalid date ranges never pass.
- Missing required fields never produce a valid result.
- Authorization failures never execute protected operations.

### Regression tests

Every confirmed validation defect should produce a test case that prevents the same defect from reappearing.

Test both successful recovery and safe failure. A pipeline that never crashes but silently accepts incorrect data is not reliable.

## 15. End-to-End Example

Consider a model that extracts information from support tickets.

The expected output is:

```json
{
  "ticket_id": "T-1024",
  "category": "technical",
  "priority": 2,
  "summary": "The user cannot connect to the service."
}
```

The application should:

1. Parse the model response.
2. Validate the JSON schema.
3. Verify that the ticket identifier corresponds to the current authorized record.
4. Check that the category is permitted.
5. Validate that the priority is within range.
6. Confirm that the summary does not contain prohibited sensitive information.
7. Persist the result only after the necessary checks pass.
8. Record the validation outcome.

If the model returns a valid object with a ticket identifier belonging to another tenant, the object must be rejected even though every field is syntactically valid.

If the model returns an unknown category, the system should not silently map it to an arbitrary category unless an explicit fallback rule defines that behavior.

If the summary includes information that is absent from the source ticket, semantic verification or review may be necessary.

The example illustrates why output validation must combine format checks with trusted application state and task-specific rules.

## 16. Common Anti-Patterns

### Trusting the prompt to enforce the schema

**Problem:** A model may violate the requested format.

**Improvement:** Validate every output in application code.

### Treating parse success as task success

**Problem:** Valid JSON may contain incorrect or fabricated values.

**Improvement:** Add semantic and business-rule validation.

### Using another LLM as the only validator

**Problem:** The validator may share the generator's blind spots.

**Improvement:** Use deterministic checks first and validate any model-based judge independently.

### Silently coercing incorrect values

**Problem:** A repair can hide a defect or change meaning.

**Improvement:** Use explicit conversion rules and reject ambiguous values.

### Retrying indefinitely

**Problem:** Unbounded retries can create cost, latency, and inconsistent side effects.

**Improvement:** Use a fixed retry limit and controlled fallback.

### Executing tool calls before authorization

**Problem:** A well-formed request can still be unauthorized.

**Improvement:** Apply permission checks before execution.

### Trusting model-generated success claims

**Problem:** The model may claim an action succeeded when the external operation failed.

**Improvement:** Verify the result using trusted tool responses or application state.

### Logging every raw response

**Problem:** Debugging data can become an unnecessary sensitive-data repository.

**Improvement:** Log minimized, structured diagnostic information.

## 17. Practical Checklist

### Structure

- [ ] Output is parsed using a deterministic parser.
- [ ] Schema validation checks required fields and types.
- [ ] Unknown fields are handled according to a documented policy.
- [ ] Missing, null, empty, and zero values have distinct semantics where needed.

### Semantics

- [ ] Field relationships and business rules are checked.
- [ ] Numerical calculations use trusted computation where appropriate.
- [ ] Evidence and citations are validated when required.
- [ ] Unsupported or contradictory claims trigger the defined response.

### Security

- [ ] Tool requests are checked against an allowlist.
- [ ] Authorization is enforced outside the model.
- [ ] High-impact actions require appropriate approval.
- [ ] Sensitive output is checked before delivery or storage.
- [ ] Validation errors do not expose unnecessary private information.

### Recovery

- [ ] Retry conditions are explicit.
- [ ] Retry attempts are bounded.
- [ ] Every repaired output is validated again.
- [ ] Unrecoverable failures produce controlled errors.
- [ ] Side effects are protected against duplicate execution.

### Monitoring

- [ ] Validation failures are measured by category.
- [ ] Important failure cases become regression tests.
- [ ] Prompt, schema, and validator versions are recorded.
- [ ] Logs are minimized and access-controlled.

## Conclusion

Output validation is the enforcement layer between probabilistic LLM generation and dependable application behavior.

A robust system does not assume that a fluent response is correct, that valid JSON is semantically sound, or that a well-formed tool call is authorized. It validates structure, meaning, business rules, evidence, and permissions before trusting or executing the result.

The central principle is simple: **the model may propose an output, but the application must decide whether that output is valid, authorized, and safe to use.**