"""Prompt-optimization benchmark package for invoice-field extraction.

Modules:
    config     - environment-driven configuration and validation
    prompts    - versioned prompt templates with stable content hashes
    dataset    - dataset loading and structural validation
    evaluation - deterministic, provider-independent scoring
    client     - OpenRouter transport with bounded retries
    schema     - per-request record and run-manifest schemas
    runner     - executes a benchmark plan through the client and evaluator
    analysis   - aggregation, model-distribution and paired comparisons
    reporting  - atomic artifact writes and the markdown report

See experiments/README.md for usage and methodology.
"""

PACKAGE_VERSION = "1.0"
