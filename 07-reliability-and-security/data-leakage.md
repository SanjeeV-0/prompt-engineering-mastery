# Data Leakage in LLM Systems

## 1. Introduction

Data leakage occurs when information reaches a model, evaluator, user, or downstream component that should not have access to it for the task being performed.

In LLM applications, leakage is broader than accidentally exposing a password. It can involve private user data, confidential business records, hidden instructions, evaluation answers, information from another tenant, restricted retrieval results, or future information that would not have been available at prediction time.

Data leakage can compromise both **security** and **evaluation validity**.

- Security leakage exposes information to an unauthorized party or component.
- Evaluation leakage allows information about expected outcomes to influence a test in a way that produces misleading performance estimates.
- Training or development leakage allows information that should have remained independent to influence model or prompt development.

A system can achieve excellent benchmark scores while performing poorly in real use if evaluation answers, duplicate examples, or future information have leaked into its development process.

Reliable LLM engineering therefore requires explicit information boundaries, controlled data flows, least-privilege access, and tests that verify those boundaries.

## 2. Threat Model and Information Boundaries

Before designing controls, identify what information exists, who may access it, and which components process it.

Typical assets include:

- Personal information
- Credentials, API keys, and authentication tokens
- Customer conversations and uploaded documents
- Internal business records
- System prompts and private application instructions
- Retrieved documents with access restrictions
- Tool outputs
- Evaluation labels and hidden test cases
- Training and fine-tuning datasets
- Logs, traces, caches, and generated artifacts

Potential threat actors include malicious users, compromised accounts, malicious document authors, unauthorized internal users, and accidental recipients.

Not every piece of internal information is necessarily secret. The important question is whether access is authorized for a particular user, task, component, and purpose.

### Define trust boundaries

An LLM application commonly includes several trust zones:

1. **User boundary:** Data supplied by the requester.
2. **Application boundary:** Trusted orchestration logic, permissions, and configuration.
3. **Model boundary:** Information sent to the model provider or inference service.
4. **Retrieval boundary:** Documents and records the user is permitted to access.
5. **Tool boundary:** External services and APIs with their own permissions.
6. **Storage boundary:** Logs, databases, caches, and evaluation artifacts.
7. **Evaluation boundary:** Development examples, calibration data, and held-out tests.

Every boundary creates a question: what information may cross it, under what conditions, and with what safeguards?

## 3. Common Types of Data Leakage

### 3.1 Direct disclosure

The model returns confidential information in its response.

Examples include revealing another user's email address, including a secret from application context, or exposing restricted document contents.

### 3.2 Cross-user or cross-tenant leakage

A system retrieves or reuses information belonging to a different user, organization, or session.

Possible causes include:

- Missing tenant filters in retrieval queries
- Incorrect authorization checks
- Shared caches with incomplete cache keys
- Conversation state reused across users
- Background jobs using the wrong identity
- Incorrectly scoped database queries

This category is particularly important for applications serving multiple customers.

### 3.3 Context leakage

Sensitive information is included in the model context even though it is unnecessary for the task.

The model might not reveal the information in its final response, but unnecessary inclusion increases exposure to logging, provider processing, debugging tools, or downstream components.

The safest default is to send only the information needed for the requested task.

### 3.4 Tool and integration leakage

A tool call may send private data to an external service without appropriate authorization or minimization.

For example, a summarization workflow might submit an entire customer record to a third-party API when only a few fields are required.

### 3.5 Logging and observability leakage

Prompts, completions, tool arguments, and error traces may contain sensitive information.

Logging can create an additional copy of data that outlives the original request or is accessible to a broader group of people.

### 3.6 Cache leakage

A response generated for one user may be served to another user because the cache key fails to include relevant authorization or context boundaries.

This can occur even if the original retrieval and generation steps were properly authorized.

### 3.7 Evaluation leakage

A prompt or model is evaluated using information that improperly influenced its development.

Examples include:

- Test answers included in prompt demonstrations
- Duplicate examples appearing in development and test sets
- Human reviewers repeatedly tuning against the final test set
- Evaluation labels accidentally included in model inputs
- Historical predictions using future data

This leakage makes evaluation results less trustworthy.

### 3.8 Training-data memorization and extraction

A model may reproduce sensitive information present in training or fine-tuning data under some conditions.

The risk depends on the data, training procedure, model, and access pattern. Do not assume that a model will always forget sensitive information simply because it has been fine-tuned or prompted to avoid disclosure.

Preventing unnecessary sensitive data from entering training pipelines is preferable to relying on behavioral instructions to suppress it later.

## 4. Data Leakage in the LLM Request Lifecycle

A typical request may pass through the following stages:

```text
User request
    |
    v
Authentication and authorization
    |
    v
Input processing and context assembly
    |
    v
Retrieval and tool selection
    |
    v
Model inference
    |
    v
Output validation and filtering
    |
    v
Response delivery
    |
    v
Logging, caching, analytics, and evaluation
```

Each stage can introduce a different leakage risk.

- Authentication may identify the wrong user.
- Retrieval may return unauthorized records.
- Context assembly may include unnecessary secrets.
- Tool orchestration may send data to an unintended service.
- Generation may reproduce sensitive context.
- Output handling may fail to redact restricted fields.
- Logging may persist data beyond its intended lifetime.
- Evaluation may copy private production examples into less-protected datasets.

Security review should cover the complete lifecycle rather than focusing only on the final model response.

## 5. Data Minimization

Data minimization means collecting, retaining, and transmitting only the information necessary for a defined purpose.

For LLM systems, minimization should be applied to:

- User input
- Retrieved documents
- Prompt context
- Tool arguments
- Model outputs
- Logs and traces
- Evaluation datasets
- Cached results

### Example

Suppose a workflow classifies a customer request into a category.

The model may need the request text and a small set of category definitions. It probably does not need the customer's full address, account credentials, or complete transaction history.

Before adding a field to the context, ask:

1. Is the field required for the task?
2. Can the task be completed using a less sensitive representation?
3. Can the field be transformed, masked, or omitted?
4. Does the receiving component have permission to process it?
5. Does the field need to be retained after the request completes?

Minimization reduces exposure even when other controls fail.

## 6. Authorization Must Precede Retrieval

A model should not be responsible for deciding whether a user is allowed to see a record.

Authorization should be enforced in application logic and data-access layers before restricted content is placed into model context.

A secure retrieval flow should:

1. Authenticate the requester.
2. Establish the requester's identity and permissions.
3. Apply access-control filters to retrieval queries.
4. Verify document-level or record-level permissions where required.
5. Retrieve only authorized content.
6. Recheck authorization when necessary for sensitive or changing permissions.
7. Log security-relevant decisions without unnecessarily recording the protected content.

### Example

Consider a system that retrieves customer-support records. The retrieval query should include the authenticated tenant or customer scope, rather than searching globally and asking the model to ignore unrelated records.

A prompt instruction such as “only reveal records belonging to the current user” is not a substitute for database authorization.

## 7. Prevent Cross-Tenant Leakage

Multi-tenant applications need explicit isolation across every layer that stores or retrieves user-specific state.

Review at least:

- Database queries
- Vector database filters
- Document identifiers
- Conversation history
- Session storage
- Tool credentials
- Background jobs
- Caches
- Logs and analytics
- Evaluation data exports

### Cache-key design

A cache key should incorporate every dimension that materially affects whether a response can be reused safely.

Depending on the application, this may include:

- Tenant or authorization scope
- User or session identity
- Normalized request
- Relevant conversation state
- Retrieved-document version
- Prompt version
- Model configuration
- Tool and policy configuration

Including the prompt and model versions improves correctness when the system changes. Including authorization scope helps prevent cross-user reuse.

Even a carefully designed key is not sufficient on its own. Cached content should still be subject to the application's authorization policy.

### Negative testing

Create two users or tenants with deliberately different access rights.

Verify that:

- Each user can retrieve their authorized records.
- Neither user can retrieve the other's restricted records.
- Cached results are not shared across incompatible authorization scopes.
- Conversation state cannot be reused across sessions accidentally.
- Permission changes take effect according to the application's documented policy.

Security tests should verify actual data access, not merely whether the model claims that access was denied.

## 8. Sensitive Information in Prompts

Prompts may contain data such as names, addresses, financial details, confidential code, medical information, or internal business records.

Before sending data to a model service, establish:

- Which provider or deployment receives it
- Whether the data is retained and for how long
- Whether it may be used for training under the applicable service terms
- Who can access request logs
- Which regions and subprocessors may process it
- Whether the application has the required contractual and legal permissions

These properties depend on the deployment and service configuration. They should be verified against current documentation and organizational requirements rather than assumed from the fact that an API is being used.

### Minimize prompt exposure

Use the following practices:

- Remove unrelated personal information.
- Replace identifiers with task-scoped aliases when possible.
- Redact secrets before model invocation.
- Restrict tool and model access to the minimum necessary context.
- Avoid placing credentials in system prompts.
- Use secret-management systems for API keys and tokens.
- Avoid returning private context in error messages.

Redaction must preserve the information needed for the task. If a value is material to the computation, replace it with a controlled representation rather than deleting it blindly.

## 9. Output Leakage and Data-Loss Prevention

Output controls can detect and block certain classes of accidental disclosure.

Possible controls include:

- Secret-pattern detection
- Personally identifiable information (PII) detection
- Field-level response filtering
- Allowlisted output schemas
- Data classification rules
- User-specific access checks
- Redaction of unauthorized fields
- Policy-based refusal or escalation

### Limitations of pattern matching

Regular expressions can detect many recognizable formats, such as some API-key patterns or structured identifiers. They cannot identify every secret or determine whether a value is authorized for a particular recipient.

Semantic detection can help identify less obvious cases but can also produce false positives and false negatives.

Use layered controls: prevent unnecessary data from entering the context, restrict data access, validate the output, and apply recipient-aware authorization.

### Example output filtering

```python
from typing import Any


ALLOWED_FIELDS = {"ticket_id", "category", "summary"}


def filter_response(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Response must be a JSON object.")

    unexpected = set(payload) - ALLOWED_FIELDS
    if unexpected:
        raise ValueError(
            f"Unexpected output fields: {sorted(unexpected)}"
        )

    return payload
```

This example enforces an output field allowlist. It does not prove that the values are correct or safe. A field such as `summary` can still contain sensitive data, so additional content and authorization checks may be required.

## 10. Logging, Tracing, and Observability

Observability is essential for diagnosing failures, but logs can become a major source of leakage.

Potentially sensitive log fields include:

- Full prompts
- Full completions
- Retrieved document text
- Tool arguments and results
- Authentication headers
- Exception messages
- Request identifiers linked to personal data
- Evaluation examples and annotations

### Logging strategy

Prefer structured, minimized telemetry such as:

- Request identifier
- Model and prompt version
- Token counts
- Latency
- Validation outcome
- Tool status
- Error category
- Evaluation score
- Redacted security event metadata

Store raw prompts and outputs only when necessary, with explicit controls over access, retention, and purpose.

### Recommended controls

- Redact secrets before logging.
- Restrict log access using least privilege.
- Set retention limits.
- Encrypt data in transit and at rest as appropriate.
- Separate operational metadata from raw content.
- Audit access to sensitive logs.
- Ensure debugging exports follow the same data-handling policy.
- Avoid including credentials in exceptions or stack traces.

Redaction should happen before the sensitive content is written to the log sink. Removing it later does not eliminate the initial exposure.

## 11. Data Leakage in Evaluation Pipelines

Evaluation leakage deserves special attention because it can make an unreliable system appear successful.

### 11.1 Duplicate and near-duplicate examples

If the same underlying question appears in both development and test datasets, prompt optimization may indirectly memorize the test example.

Deduplicate exact copies and, where appropriate, identify near-duplicates using semantic similarity or shared source identifiers.

Automated similarity checks are useful screening tools, but they do not replace reviewing related examples that could share the same answer or source.

### 11.2 Prompt demonstrations

Few-shot examples should not accidentally expose hidden test answers or contain information unavailable to the system at inference time.

Track the provenance of demonstrations and keep them separate from the final held-out evaluation data.

### 11.3 Repeated test-set tuning

If developers inspect every failed test example and update the prompt accordingly, the test set gradually becomes development data.

Use a separate development set for iteration and preserve an independent final test set. If the final test set has been repeatedly used to guide changes, create a new held-out set where feasible.

### 11.4 Temporal leakage

For tasks that predict future outcomes, ensure that inputs contain only information available at prediction time.

For example, a forecasting evaluation is invalid if the prompt includes a report published after the date being predicted.

Temporal leakage can occur in retrieved documents, feature pipelines, cached summaries, and manually prepared context—not only in training data.

### 11.5 Evaluator leakage

An LLM judge can receive reference labels or candidate metadata that inadvertently reveal the expected answer.

Provide only the information required for the judging task. When blinding is appropriate, remove candidate identifiers, model names, and other unnecessary signals that could influence the evaluation.

## 12. Training and Fine-Tuning Data

Fine-tuning and other training pipelines introduce additional data-handling concerns.

Review:

- Whether the data was collected for a compatible purpose
- Whether the organization has the necessary rights and permissions
- Whether sensitive fields can be excluded or transformed
- Whether examples contain credentials or confidential records
- Whether training and evaluation splits overlap improperly
- Whether access to datasets and training artifacts is restricted
- Whether retention and deletion requirements are documented

Training-data filtering should happen before data enters the training process whenever feasible.

If sensitive data must be removed from an existing trained system, deleting a source file may not remove information already incorporated into model parameters or derived artifacts. The appropriate remediation depends on the training method, provider capabilities, applicable requirements, and system architecture.

Do not promise that a model has forgotten data without evidence that the relevant remediation was completed and verified.

## 13. Caches, Embeddings, and Derived Data

Derived artifacts can still contain sensitive information.

Examples include:

- Vector embeddings
- Summaries of private documents
- Conversation memory
- Search indexes
- Cached model outputs
- Generated reports
- Evaluation annotations
- Intermediate agent state

Transforming a document into an embedding does not automatically make it anonymous or safe to disclose.

Treat derived artifacts according to their content, re-identification risk, access requirements, and intended use.

When source access is revoked or a document is deleted, identify all dependent artifacts that may need invalidation, re-indexing, or deletion according to the application's data lifecycle policy.

## 14. Privacy-Preserving Test Data

Testing often requires realistic examples, but copying production data into development environments can create unnecessary risk.

Potential approaches include:

- Synthetic examples
- De-identified data
- Redacted production examples
- Controlled access to a protected evaluation environment
- Representative templates with substituted values
- Aggregate statistics instead of raw records

Each method has trade-offs.

Synthetic data can fail to represent real-world complexity. Redaction can remove context necessary for the task. De-identification may not eliminate re-identification risk, especially when multiple fields can be combined.

Validate that the transformed dataset still measures the intended behavior while minimizing exposure.

## 15. A Data-Flow Review Procedure

For each application feature, document the information flow.

### Step 1: Inventory

List the input sources, context fields, retrieved documents, tool arguments, outputs, caches, logs, and evaluation artifacts.

### Step 2: Classify

Identify the sensitivity and access requirements of each data category.

### Step 3: Map recipients

Determine which users, services, model deployments, databases, and internal roles can access each category.

### Step 4: Justify each transfer

For every boundary crossing, record why the data is required and what controls apply.

### Step 5: Verify authorization

Test whether access is checked before restricted data reaches the model or downstream service.

### Step 6: Minimize and protect

Remove unnecessary fields, redact secrets where appropriate, apply access controls, and define retention limits.

### Step 7: Test leakage paths

Use synthetic canary values and controlled test accounts to detect unintended exposure across prompts, retrieval, caches, tools, logs, and outputs.

### Step 8: Review lifecycle behavior

Verify that revocation, deletion, cache invalidation, and dataset retirement are handled consistently across derived artifacts.

## 16. Incident Response for Suspected Leakage

When leakage is suspected, prioritize containment and evidence preservation.

A practical response sequence is:

1. Identify the exposed information and affected systems.
2. Restrict or disable the affected data path where necessary.
3. Revoke or rotate exposed credentials.
4. Preserve relevant security logs under controlled access.
5. Determine the scope of access and possible recipients.
6. Identify the underlying cause.
7. Correct the authorization, context, cache, logging, or output defect.
8. Add regression tests for the confirmed failure.
9. Follow applicable organizational, contractual, and legal notification procedures.
10. Verify remediation before restoring the affected workflow.

Avoid copying sensitive information into tickets, chat messages, or debugging reports unless necessary and appropriately protected.

Incident handling should be coordinated with the responsible security, privacy, and operational teams. Legal and notification obligations vary by jurisdiction and data type.

## 17. Testing for Leakage

A practical leakage test suite should include controlled cases for:

- Unauthorized cross-tenant retrieval
- Cross-session conversation contamination
- Cache-key collisions
- Sensitive fields accidentally included in prompts
- Secret patterns appearing in outputs
- Sensitive content in logs and traces
- Tool calls sending excessive context
- Revoked permissions
- Deleted or updated documents remaining in indexes
- Evaluation answers appearing in development context

Use synthetic canary values—unique, non-sensitive test strings—to verify whether information crosses boundaries unexpectedly.

For each test, define the expected behavior and inspect the actual data path. A refusal message is not sufficient proof that unauthorized data was never retrieved or logged.

## 18. Practical Checklist

### Data access

- [ ] Authentication and authorization are enforced in application code.
- [ ] Retrieval applies user and tenant permissions before returning content.
- [ ] Tool permissions follow least privilege.
- [ ] Shared caches respect authorization boundaries.
- [ ] Session state cannot leak across users.

### Prompt and output handling

- [ ] Only task-relevant information enters model context.
- [ ] Secrets are not stored in prompts as a substitute for secret management.
- [ ] Output fields are validated and authorized for the recipient.
- [ ] Sensitive-data detection has documented limitations.
- [ ] Untrusted content cannot grant itself additional access.

### Storage and observability

- [ ] Logs minimize or redact sensitive content before storage.
- [ ] Log access and retention are controlled.
- [ ] Embeddings, summaries, and cached responses are treated as potentially sensitive.
- [ ] Data deletion and permission revocation cover dependent artifacts.

### Evaluation and training

- [ ] Development and test datasets are appropriately separated.
- [ ] Duplicate and temporal leakage are checked.
- [ ] Evaluation labels are not accidentally exposed to the system under test.
- [ ] Training data has documented provenance and access controls.
- [ ] Privacy-preserving test data is validated for usefulness.

### Operations

- [ ] Leakage scenarios are tested with synthetic data.
- [ ] Incident-response responsibilities are defined.
- [ ] Credential rotation and access revocation procedures are documented.
- [ ] Confirmed failures become regression tests.

## Conclusion

Data leakage in LLM systems can originate anywhere information is collected, retrieved, transformed, transmitted, generated, cached, logged, or evaluated.

Reliable prevention requires more than asking the model to keep information confidential. It requires explicit authorization, data minimization, tenant isolation, controlled information flows, safe logging, and tests that verify the actual boundaries.

The central principle is to prevent unauthorized information from reaching a component in the first place, limit what each component can access, and verify that sensitive information does not escape through secondary paths.