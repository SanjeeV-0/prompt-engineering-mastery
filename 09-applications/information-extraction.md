# Information Extraction with LLMs

## 1. Overview

Information extraction is the process of converting unstructured or semi-structured content into a defined representation of facts, entities, attributes, relationships, or events.

Examples include:

- Extracting names, dates, and organizations from documents
- Identifying product attributes from descriptions
- Extracting requirements from technical specifications
- Converting support tickets into structured records
- Identifying contract clauses and their associated conditions
- Extracting events, participants, and dates from meeting notes

Large language models (LLMs) can perform these tasks using natural-language instructions and examples. However, reliable extraction requires more than asking a model to return JSON.

The prompt must define what to extract, how to interpret ambiguous content, what evidence is acceptable, how to handle missing values, and what output format is required.

A robust extraction workflow separates three concerns:

1. **Interpretation:** Determine what the source actually states.
2. **Representation:** Express the extracted information in a consistent schema.
3. **Validation:** Check whether the output is structurally valid and supported by the source.

The objective is not to produce a complete-looking record at any cost. It is to produce a record that accurately reflects the available evidence.

## 2. Define the Extraction Task

A weak extraction prompt might say:

```text id="1p8qwx"
Extract the important information from this text.
```

The phrase “important information” is subjective. Different runs may return different fields, levels of detail, or interpretations.

A stronger prompt specifies the target fields and their meanings.

```text id="7yrzmt"
Extract the following information from the supplied product description:

- product_name: the explicitly stated product name
- price: the listed price, including currency
- availability: the explicitly stated availability status
- features: the product features directly mentioned in the text

Rules:
- Do not infer values that are not supported by the source.
- Use null when a scalar field cannot be determined.
- Use an empty list when no features are explicitly identified.
- Preserve the original meaning and units.
- Return only the specified JSON object.
```

This defines the scope, extraction criteria, missing-value behavior, and output format.

### Define field semantics precisely

A field name alone may be insufficient.

For example, `date` could mean:

- The date a document was created
- The date an event occurred
- The date a deadline falls on
- The date mentioned most recently

A good schema and prompt explain which meaning is intended.

If a document contains several dates, the model should distinguish them according to the task's definitions rather than selecting one arbitrarily.

## 3. Design an Extraction Schema

A schema describes the expected structure of the extracted record.

For example:

```json id="n7k1tv"
{
  "person_name": "string or null",
  "organization": "string or null",
  "event_date": "string or null",
  "location": "string or null",
  "confidence_note": "string"
}
```

This is a conceptual example of a schema. A production implementation should use actual JSON Schema or equivalent typed definitions.

A useful extraction schema defines:

- Field names
- Data types
- Required fields
- Optional fields
- Permitted values
- Missing-value conventions
- Date and number formats
- Whether additional fields are allowed
- Relationships between fields

### Choose the right level of detail

An overly broad schema may produce inconsistent results. An excessively detailed schema may force the model to make distinctions the source does not support.

For example, if the source says “the meeting is next Friday,” do not require an exact calendar date unless the reference date and timezone are known.

Schema design should match the information actually available and the needs of downstream consumers.

## 4. Distinguish Missing, Unknown, and Not Applicable

Missing-value handling is one of the most important parts of extraction design.

These situations are different:

- **Present:** The source explicitly provides the value.
- **Unknown:** The available evidence does not establish the value.
- **Not applicable:** The field does not apply to the record.
- **Conflicting:** Different source passages provide incompatible values.
- **Ambiguous:** The text supports multiple interpretations.

A simple schema may represent several of these cases using `null`, but doing so loses information.

For tasks that require auditability, use an explicit status.

Example:

```json id="pvx4z9"
{
  "delivery_date": {
    "value": null,
    "status": "unknown",
    "evidence": []
  }
}
```

For a conflicting value:

```json id="h1wk72"
{
  "delivery_date": {
    "value": null,
    "status": "conflicting",
    "evidence": [
      "Paragraph 2 states 12 May.",
      "Paragraph 5 states 14 May."
    ]
  }
}
```

The exact structure should match the application's requirements. Avoid introducing complex status fields when a simple nullable value is sufficient.

### Explicit prompting rule

```text id="p2h73n"
Do not infer a missing value from general knowledge or typical patterns.

If the source does not establish the requested value, mark it unknown.
If the source contains conflicting values, preserve the conflict rather
than silently choosing one.
```

This reduces unsupported completion, a common extraction failure.

## 5. Extract Evidence Alongside Values

For high-accuracy tasks, extracting a value without its supporting evidence can make errors difficult to diagnose.

A more useful record may contain:

- The normalized value
- A supporting quotation or source span
- The source identifier
- The extraction status

Example:

```json id="s8q3vp"
{
  "invoice_number": {
    "value": "INV-2048",
    "status": "present",
    "evidence": [
      {
        "source_id": "invoice-01",
        "text": "Invoice Number: INV-2048"
      }
    ]
  }
}
```

The quotation illustrates the representation, not a real invoice.

### Why evidence matters

Evidence supports:

- Manual verification
- Debugging incorrect extractions
- Source-level auditing
- Conflict resolution
- Citation generation
- More reliable downstream processing

Prompt the model to return only evidence that actually appears in the supplied source.

A quotation can still be incorrectly associated with a value, so applications should verify source spans where possible.

### Preserve provenance

For document collections, evidence should ideally include stable source identifiers and locations such as page numbers, section identifiers, or character offsets.

Do not rely exclusively on a model-generated source label when the application can assign and validate source identifiers itself.

## 6. Choose Between Direct Extraction and Normalization

Extraction and normalization are related but distinct operations.

**Extraction** identifies what the source states.

**Normalization** converts the extracted value into a consistent representation.

For example, the source might say:

> The meeting is scheduled for the 3rd of March, 2027.

The extracted value preserves the original date expression. A normalization stage may convert it to `2027-03-03`, provided the interpretation is unambiguous.

A robust workflow separates the two when normalization could introduce errors.

### Example prompt

```text id="6a0j2d"
For each requested field:
1. Identify the value stated in the source.
2. Preserve the original wording in source_value.
3. Produce normalized_value only when the transformation is
   unambiguous and follows the specified normalization rules.
4. Otherwise, set normalized_value to null and explain the ambiguity.
```

Example output:

```json id="d02mwb"
{
  "source_value": "3rd of March, 2027",
  "normalized_value": "2027-03-03"
}
```

### Common normalization operations

- Date formatting
- Currency representation
- Unit conversion
- Whitespace normalization
- Entity-name standardization
- Phone-number formatting
- Enumeration mapping

Normalization rules should be explicit. Do not silently change units, currencies, timezones, or meanings.

## 7. Use Few-Shot Examples for Ambiguous Fields

Few-shot prompting can improve consistency when field definitions are difficult to communicate through instructions alone.

Suppose a support-ticket extraction task must distinguish an explicit customer complaint from a proposed solution.

An example can demonstrate the intended interpretation:

```text id="j0ud61"
Example input:
"The application crashes whenever I upload a large file.
It would help if the upload limit were increased."

Expected output:
{
  "issue": "The application crashes when uploading a large file.",
  "suggestion": "Increase the upload limit."
}

Now process the supplied ticket using the same definitions.
```

Examples should demonstrate:

- Typical cases
- Missing information
- Ambiguous cases
- Negative examples
- Relevant edge cases

### Avoid overfitting to examples

A model may imitate an example too literally or assume that every input contains the same fields.

Use examples that illustrate the rules without implying that all records have identical content.

Test the prompt on examples that differ in wording, length, structure, and complexity from the demonstrations.

## 8. Handle Long and Complex Documents

Long documents can contain information relevant to a field in several locations.

For example, a contract may mention a party's name in the introduction, an effective date in one section, and termination conditions near the end.

Passing a large document into one extraction prompt may be adequate for some models and tasks, but can become expensive or unreliable when the document is very long.

Possible strategies include:

- Extracting fields from relevant sections
- Processing the document in chunks
- Retrieving passages based on requested fields
- Using a first pass to locate candidate evidence
- Combining validated field-level results
- Performing a final consistency check

### Preserve document boundaries

When chunking a document, retain useful metadata:

- Document identifier
- Page or section
- Chunk position
- Overlap with adjacent chunks, where applicable
- Relevant headings

Without this information, the model may lose the context needed to interpret a statement correctly.

### Avoid premature summarization

A summary can omit exact values, exceptions, qualifiers, or negations that matter for extraction.

For example, “payment is due within 30 days unless the invoice is disputed” cannot safely be reduced to “payment is due within 30 days” if the exception matters.

For exact extraction tasks, retrieve or inspect the original evidence before producing the final value.

## 9. Handle Negation, Qualifiers, and Relationships

Extraction errors often arise not because the model misses a keyword, but because it loses the relationship between pieces of text.

Consider:

> The product does not support offline access.

A keyword-based interpretation might incorrectly record `offline_access = true`.

A good prompt instructs the model to preserve negation and qualifiers.

```text id="m3z7aw"
Extract product capabilities according to the source's actual meaning.

- Preserve negation.
- Distinguish supported from unsupported features.
- Preserve exceptions and conditional statements.
- Do not treat a mentioned feature as a supported capability unless
  the source explicitly establishes that relationship.
```

### Relationships matter

Suppose a document says:

> Alice approved the request that Bob submitted.

The extracted relationships are:

- Bob submitted the request.
- Alice approved the request.

A weak extraction prompt might identify both people and the action words without assigning the correct roles.

For relationship extraction, define the expected entities and relations explicitly.

For example:

```json id="s3r2j8"
{
  "entities": [
    {"id": "e1", "type": "person", "name": "Alice"},
    {"id": "e2", "type": "person", "name": "Bob"},
    {"id": "e3", "type": "request", "name": null}
  ],
  "relations": [
    {"subject": "e2", "relation": "submitted", "object": "e3"},
    {"subject": "e1", "relation": "approved", "object": "e3"}
  ]
}
```

The schema is illustrative. Entity identifiers and relationship types should be defined for the target application.

## 10. Prevent Unsupported Inference

LLMs may fill missing fields with plausible values based on patterns in the text or general knowledge.

This can make a record appear complete while introducing incorrect information.

Example source:

> Jordan joined the company in 2022 and leads the analytics team.

Unsupported extractions might include a specific job title, a degree, or an exact joining date.

A prompt should distinguish direct evidence from inference.

```text id="v4x0pk"
Use only the supplied source to establish extracted facts.

Do not:
- Add facts from general knowledge.
- Infer exact dates from approximate time expressions.
- Assume a person's title from their responsibilities.
- Convert an implication into an explicit fact.
- Fill missing fields with typical or likely values.

If the evidence is insufficient, mark the field unknown.
```

For some applications, inference is part of the task. If so, label inferred values separately and specify the permitted inference rules.

## 11. Structured Output and Validation

A model can return syntactically valid JSON that contains incorrect or unsupported values.

Validation should therefore occur in layers.

### Layer 1: Syntax

Can the output be parsed?

### Layer 2: Schema

Are the expected fields present with the correct types?

### Layer 3: Semantics

Do values satisfy the field definitions and domain constraints?

### Layer 4: Evidence

Are the extracted values supported by the original source?

### Layer 5: Application rules

Are the results permitted and suitable for downstream use?

Example:

```python id="i3z0rk"
import json
from datetime import date

def validate_record(raw_output: str) -> dict:
    result = json.loads(raw_output)

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")

    required = {"name", "event_date", "status"}

    if set(result) != required:
        raise ValueError("Unexpected or missing fields")

    if result["name"] is not None and not isinstance(
        result["name"], str
    ):
        raise ValueError("name must be a string or null")

    if result["event_date"] is not None:
        if not isinstance(result["event_date"], str):
            raise ValueError("event_date must be a string or null")

        try:
            date.fromisoformat(result["event_date"])
        except ValueError as exc:
            raise ValueError("event_date must use YYYY-MM-DD") from exc

    allowed_statuses = {"scheduled", "cancelled", "unknown"}

    if result["status"] not in allowed_statuses:
        raise ValueError("Invalid status")

    return result
```

This example checks basic structure and date syntax. It does not prove that the event date or status is supported by the source.

For production use, define the expected schema carefully and add evidence checks appropriate to the task.

## 12. Measure Extraction Quality

A prompt that works well on a few examples may fail on different document formats, longer inputs, or ambiguous wording.

Create a labeled evaluation dataset containing representative examples and expected outputs.

Include:

- Straightforward records
- Missing fields
- Conflicting values
- Negation
- Ambiguous dates and units
- Repeated entities
- Long documents
- Unusual formats
- Irrelevant text
- Adversarial instructions embedded in source content

### Field-level metrics

For fields that require exact matches:

\[
\text{Exact Match Rate}
=
\frac{\text{Correct field values}}
{\text{Total evaluated field values}}
\]

For entity or span extraction, precision and recall are useful:

\[
\text{Precision}
=
\frac{TP}{TP+FP}
\]

\[
\text{Recall}
=
\frac{TP}{TP+FN}
\]

\[
F_1
=
2\cdot\frac{\text{Precision}\cdot\text{Recall}}
{\text{Precision}+\text{Recall}}
\]

Here, \(TP\), \(FP\), and \(FN\) represent true positives, false positives, and false negatives according to the task's labeling rules.

For normalized dates, entity names, or semantically equivalent values, exact string comparison may be too strict. Use task-appropriate normalization and evaluation rules.

### Evaluate more than accuracy

Useful measurements include:

- Field-level precision and recall
- Exact match rate
- Schema-valid output rate
- Unsupported inference rate
- Correct handling of unknown values
- Evidence attribution accuracy
- Performance across document types
- Latency and cost per record

For high-stakes extraction, measure the error rate for critical fields separately rather than hiding it inside an overall average.

## 13. Improve Prompts Using Error Analysis

Prompt optimization should begin with a clear understanding of failure patterns.

Suppose an extraction prompt has these observed problems:

- Incorrect interpretation of negative statements
- Invented values for missing dates
- Inconsistent currency normalization
- Missing evidence references

Do not immediately rewrite the entire prompt. Classify each failure and introduce targeted changes.

| Failure | Possible improvement |
|---|---|
| Negation errors | Add explicit negation rules and counterexamples |
| Invented values | Define unknown-value behavior and prohibit unsupported inference |
| Inconsistent normalization | Specify canonical formats and conversion rules |
| Missing evidence | Require source references for each critical field |
| Invalid JSON | Tighten the output contract and validate structurally |
| Incorrect field assignment | Clarify field definitions and add contrastive examples |

Run the revised prompt against the same evaluation set.

Check for regressions: a prompt that becomes more conservative may reduce unsupported values but also omit valid information.

The goal is to improve the balance of correctness, completeness, and uncertainty handling.

## 14. A Practical Extraction Workflow

A reliable information-extraction workflow can follow these steps:

1. Define the business objective and required fields.
2. Specify the schema and each field's meaning.
3. Establish rules for missing, conflicting, and ambiguous information.
4. Supply the relevant source text with clear boundaries.
5. Prompt the model to extract only supported facts.
6. Request evidence or provenance for critical fields.
7. Parse and validate the structured output.
8. Verify important values against the source.
9. Route unresolved conflicts or critical failures for review.
10. Measure performance on a representative test dataset.
11. Improve the prompt using categorized errors.
12. Monitor quality as source formats and input distributions change.

Not every task requires a separate model call for each step. The workflow can combine compatible stages, provided the necessary validation and evidence requirements are preserved.

## 15. Common Anti-Patterns

### Extracting “everything important”

**Problem:** The model chooses fields inconsistently.

**Improvement:** Define explicit fields and extraction criteria.

### Forcing every field to have a value

**Problem:** The model invents plausible values to satisfy the schema.

**Improvement:** Define null, unknown, conflicting, and not-applicable behavior.

### Mixing extraction and interpretation

**Problem:** Source facts become blended with assumptions or recommendations.

**Improvement:** Separate direct extraction from inference and label each appropriately.

### Using JSON as the only quality check

**Problem:** Structurally valid output contains unsupported facts.

**Improvement:** Add semantic and evidence validation.

### Removing source evidence too early

**Problem:** Downstream stages cannot verify extracted values.

**Improvement:** Preserve source identifiers and relevant spans for critical fields.

### Testing only clean examples

**Problem:** The prompt fails on missing data, negation, conflicting statements, or unusual formats.

**Improvement:** Build a test set that represents real-world variability.

## 16. Practical Checklist

- [ ] Every field has a clear definition.
- [ ] The output schema matches downstream requirements.
- [ ] Missing and conflicting information have explicit handling rules.
- [ ] Extraction is distinguished from normalization and inference.
- [ ] Negation, qualifiers, and relationships are preserved.
- [ ] Critical values retain source provenance.
- [ ] Untrusted instructions in source content are not treated as task instructions.
- [ ] Structured output is parsed and validated.
- [ ] Important facts are checked against the source.
- [ ] Evaluation includes edge cases and realistic documents.
- [ ] Prompt changes are measured against a baseline.
- [ ] Critical-field errors are measured separately.

## 17. Key Takeaways

- Reliable information extraction starts with precise field definitions and output contracts.
- Missing information should remain missing rather than being replaced with plausible guesses.
- Extraction, normalization, and inference are different operations and should be distinguished.
- Evidence and provenance make results easier to verify and debug.
- Negation, qualifiers, and relationships are essential to preserving meaning.
- Valid JSON does not guarantee correct or supported facts.
- Representative evaluation datasets reveal failures that clean examples hide.
- Prompt optimization should be driven by measured error patterns.

The strongest extraction prompt is not the one that fills the most fields. It is the one that consistently returns the information the source supports, represents uncertainty honestly, and produces output that downstream systems can validate.

## Further Reading

- OpenAI, *Prompt engineering*: https://platform.openai.com/docs/guides/prompt-engineering
- OpenAI, *Structured Outputs*: https://platform.openai.com/docs/guides/structured-outputs
- Anthropic, *Prompt engineering overview*: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview