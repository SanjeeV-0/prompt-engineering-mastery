# Structured Output

## 1. Overview

Structured output is the generation of responses that conform to a predefined representation, such as JSON, a set of fields, an enumeration, or a typed data structure.

It enables language models to participate in software pipelines where responses must be parsed, validated, stored, or passed to other components.

A structured-output design typically defines:
- The required fields
- The data type of each field
- Permitted values
- Required and optional properties
- Rules for missing or uncertain information
- Validation and error-handling behavior

A response that looks structured is not necessarily valid, complete, or factually correct.

## 2. Why Structure Matters

Consider an application that extracts information from customer messages.

Unstructured response:

"The customer is asking about a billing problem and considers it urgent."

This may be understandable to a person but requires additional interpretation before a program can use it.

Structured response:

```json
{
  "category": "billing",
  "priority": "high",
  "reason": "The customer reports an incorrect charge."
}
```

A program can access the fields directly, provided the response conforms to the expected contract.

Structured output improves interface consistency, but it does not guarantee that the values are correct or supported by the input.

## 3. Specify an Output Contract

An output contract describes the response expected by the consuming application.

For example:

```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "enum": [
        "billing",
        "technical_support",
        "account_access",
        "other"
      ]
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high"]
    },
    "reason": {
      "type": "string"
    }
  },
  "required": ["category", "priority", "reason"],
  "additionalProperties": false
}
```

This illustrative JSON Schema specifies the permitted fields and values. Actual schema support varies by API and constrained-generation implementation.

A complete contract should also establish:
- How missing evidence is represented
- Whether null values are permitted
- Whether empty strings are valid
- How ambiguous cases are handled
- Which fields require supporting evidence

## 4. Prompt Instructions Versus Enforcement

### 4.1 Prompt-only formatting

```text
Return a JSON object with the keys "category" and "priority".
Do not include any text outside the JSON.
```

This instruction communicates the desired format. However, the model may still return malformed JSON, omit a field, or produce an invalid value.

### 4.2 Constrained structured generation

Where supported, an API may accept a schema or constrained output definition that restricts the response format during generation.

This is stronger than prompt-only instructions for enforcing structural requirements.

However, constrained generation does not establish semantic correctness. A perfectly valid object may still contain an incorrect classification.

### 4.3 Application-level validation

The consuming application should validate the result before relying on it.

Validation may include:
- Syntax parsing
- Schema compliance
- Enum membership
- Cross-field consistency
- Domain-specific business rules
- Evidence and authorization checks

Critical constraints should not depend exclusively on the model.

## 5. A Layered Validation Model

Structured-output reliability can be understood as a sequence of distinct checks.

1. **Generation:** the model produces a response.
2. **Parsing:** the response can be interpreted in the required representation.
3. **Schema validation:** the fields and types satisfy the contract.
4. **Semantic validation:** the values make sense for the task.
5. **Evidence validation:** claims are supported by the available source.
6. **Action authorization:** any consequential operation is permitted.

Passing an earlier stage does not guarantee success at later stages.

For example, a response can pass JSON Schema validation while containing a fabricated invoice number. Schema validation alone cannot establish that the invoice exists.

## 6. Handling Missing and Uncertain Information

Extraction systems should distinguish between a field that is absent from the source and a field whose value is known.

For example:

```json
{
  "invoice_number": null,
  "evidence": "The document does not contain an identifiable invoice number."
}
```

This representation is appropriate only if the schema permits null values and the evidence field is part of the defined contract.

Alternative policies include:
- Rejecting incomplete records
- Returning an explicit status field
- Requesting clarification
- Routing the record for human review

Choose a policy that reflects the application requirements rather than treating every missing value as an empty string.

## 7. Python Validation Example

The following example validates a classification response without calling an LLM.

It demonstrates why application code must check the returned structure.

```python
import json


ALLOWED_CATEGORIES = {
    "billing",
    "technical_support",
    "account_access",
    "other",
}

ALLOWED_PRIORITIES = {"low", "medium", "high"}


def validate_classification(raw_output: str) -> dict:
    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("Output is not valid JSON") from exc

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")

    expected_keys = {"category", "priority", "reason"}

    if set(result.keys()) != expected_keys:
        raise ValueError("Unexpected or missing fields")

    if result["category"] not in ALLOWED_CATEGORIES:
        raise ValueError("Invalid category")

    if result["priority"] not in ALLOWED_PRIORITIES:
        raise ValueError("Invalid priority")

    if not isinstance(result["reason"], str):
        raise ValueError("Reason must be a string")

    return result


if __name__ == "__main__":
    valid_output = """
    {
      "category": "billing",
      "priority": "high",
      "reason": "The customer reports an incorrect charge."
    }
    """

    print(validate_classification(valid_output))
```

This validates the basic structure and allowed values. A production implementation should also check types before set membership, handle unexpected input types, define field-length limits where appropriate, and enforce domain-specific rules.

Most importantly, this function does not verify whether the model's classification is factually correct.

## 8. Failure Handling

Structured-output systems must define what happens when generation or validation fails.

Possible strategies include:
- Rejecting the invalid response
- Retrying with bounded attempts
- Returning a structured error
- Sending the item to a review queue
- Falling back to a deterministic implementation

Retries should be limited and observable. Repeatedly asking the model to repair a response does not guarantee correctness and may increase cost or latency.

Do not execute consequential actions based on an unvalidated response.

## 9. Evaluation Metrics

Evaluate structured-output systems at multiple levels.

### Structural metrics
- Parse success rate
- Schema compliance rate
- Required-field completeness
- Invalid-enum rate

### Semantic metrics
- Field-level accuracy
- Exact-match accuracy where appropriate
- Extraction precision and recall
- Evidence support rate

### Operational metrics
- Retry rate
- Latency
- Token consumption
- Cost per valid result
- Human-review rate

Report structural and semantic results separately. Combining them into one score can hide important failure modes.

## 10. When to Use Structured Output

Structured output is especially useful for:
- Information extraction
- Classification pipelines
- Data transformation
- API integrations
- Tool argument generation
- Automated report generation
- Multi-stage LLM workflows

It is less important when a free-form conversational response is sufficient and no downstream component needs a rigid representation.

## 11. Common Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Invalid JSON | Format requested only through prose | Use supported constrained generation and parse validation |
| Missing fields | Contract is incomplete or not enforced | Define required fields and validate |
| Invalid enum | Model returns an unpermitted value | Enforce allowed values |
| Semantically incorrect fields | Valid structure mistaken for correctness | Evaluate against labeled or verified references |
| Unsupported extraction | Model invents a value | Define abstention and evidence policies |
| Unsafe tool execution | Model output is treated as authorization | Enforce permissions and validate arguments |
| Unbounded retries | Failure recovery lacks limits | Use bounded retries and explicit fallbacks |

## 12. Key Takeaways

Structured output turns model responses into defined interfaces for software systems.

Reliable implementations distinguish formatting instructions, generation constraints, structural validation, semantic correctness, and action authorization.

The correct engineering approach is to define an explicit output contract, use constrained generation when available, validate the response in application code, and measure both structural compliance and task accuracy.

## References

- [OpenAI Structured Outputs Guide](https://developers.openai.com/api/docs/guides/structured-outputs/)
- [OpenAI API Documentation](https://developers.openai.com/api/docs/)
- [JSON Schema Documentation](https://json-schema.org/learn)
