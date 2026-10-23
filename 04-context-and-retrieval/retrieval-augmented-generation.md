# Retrieval-Augmented Generation (RAG)

## 1. Overview

Retrieval-Augmented Generation (RAG) is an architecture that combines information retrieval with language-model generation. Before generating an answer, the system retrieves potentially relevant information from an external knowledge source and supplies selected results to the model as context.

RAG is useful when an application needs to answer questions using private documents, domain-specific knowledge, frequently updated information, or a corpus that cannot be fully included in every prompt.

A language model's internal parameters are not a reliable substitute for retrieving current, source-specific evidence. RAG gives the application a way to provide relevant material at inference time.

However, RAG does not guarantee factual accuracy. The system can retrieve the wrong evidence, miss the correct document, misunderstand the retrieved content, or generate claims that the evidence does not support.

## 2. Core Architecture

A typical RAG system has two major workflows: indexing and query-time retrieval.

### Indexing workflow

1. Collect source documents.
2. Parse text, tables, metadata, and other supported content.
3. Normalize and clean the extracted material.
4. Split documents into retrievable units.
5. Generate embeddings or build another searchable representation.
6. Store the content, metadata, and search indexes.

### Query-time workflow

1. Receive the user's question.
2. Interpret the information need.
3. Retrieve candidate passages.
4. Filter, rank, or rerank the candidates.
5. Assemble a context that fits the model's input budget.
6. Generate an answer using the selected evidence.
7. Validate the answer and citations where required.

The basic data flow is:

`Documents → Parsing → Chunking → Indexing`

`Question → Retrieval → Ranking → Context assembly → Generation → Validation`

Some systems add query rewriting, multiple retrieval passes, hybrid search, access-control filters, or specialized handling for tables and images.

## 3. Why Use RAG?

RAG is useful when an application needs to:

- Answer questions from a defined document collection.
- Incorporate information that changes over time.
- Ground answers in identifiable sources.
- Search internal knowledge bases or technical documentation.
- Keep source material separate from model parameters.
- Restrict answers to information available in authorized records.

RAG can also make knowledge updates easier: a document can be reindexed without retraining the language model.

This does not mean that every document change becomes instantly available. Freshness depends on ingestion, indexing, caching, and update policies.

RAG is less useful when the task requires no external information, the source corpus is too unreliable to support the answer, or retrieval overhead is greater than its benefit.

## 4. Document Ingestion and Parsing

Retrieval quality starts before the search index is built.

Documents may contain:

- Headings and paragraphs.
- Tables and lists.
- Code blocks.
- Footnotes and citations.
- Page numbers and section identifiers.
- Scanned pages requiring OCR.
- Repeated headers and navigation text.

Poor parsing can destroy relationships between information. For example, extracting a table as disconnected text may separate a value from the column heading that defines its meaning.

A robust ingestion pipeline should preserve useful structure and attach metadata such as:

- Document ID.
- Source URI or repository path.
- Title and section.
- Page or character range.
- Version or revision.
- Publication or update timestamp.
- Access-control attributes.

Metadata supports filtering, traceability, freshness management, and citation generation.

Treat parsing quality as an independently testable component. If the original information is extracted incorrectly, a better retrieval algorithm cannot recover the lost information.

## 5. Chunking Strategies

Chunking divides source material into units that can be retrieved and supplied to the model.

The best chunking strategy depends on document structure, retrieval behavior, and the information needs of the application.

### Fixed-size chunking

Split text into chunks based on a target token or character length, sometimes with overlap.

**Advantages:**
- Simple to implement.
- Predictable chunk sizes.
- Useful as a baseline.

**Limitations:**
- May split a concept across boundaries.
- Can separate headings from the text they describe.
- May create redundant overlapping passages.

### Structure-aware chunking

Split documents at meaningful boundaries such as headings, paragraphs, sections, or code blocks.

**Advantages:**
- Better preservation of semantic relationships.
- More natural citation boundaries.
- Useful for technical documentation and structured reports.

**Limitations:**
- Sections may vary greatly in size.
- Long sections may still require further splitting.

### Semantic chunking

Use content similarity or semantic boundaries to determine where one chunk ends and another begins.

**Advantages:**
- Can preserve coherent ideas.
- May help with documents that lack reliable structural markers.

**Limitations:**
- Requires additional processing.
- Results depend on the segmentation method.
- Added complexity may not improve performance on every corpus.

### Parent-child retrieval

Index smaller child passages for precise retrieval while retaining links to larger parent sections or documents.

The system can retrieve a focused passage and then supply additional surrounding context when necessary.

This approach can balance retrieval precision with contextual completeness, but it increases storage and orchestration complexity.

### Chunk size and overlap

Small chunks can improve retrieval precision but may omit qualifications or dependencies. Large chunks preserve more context but may introduce irrelevant text and consume more of the context window.

Overlap can preserve information near chunk boundaries, but excessive overlap increases duplication and index size.

Choose chunk size and overlap empirically. Evaluate the resulting retrieval system rather than assuming a universal optimal setting.

## 6. Embeddings and Vector Search

An embedding model maps text into a numerical vector intended to represent useful semantic properties.

For a document chunk \(d\), an embedding model produces a vector:

\[
\mathbf{v}_d = E(d)
\]

A query \(q\) can be embedded similarly:

\[
\mathbf{v}_q = E(q)
\]

A vector search system compares the query vector with stored document vectors using a similarity or distance measure.

Common approaches include cosine similarity, dot product, and Euclidean distance. The appropriate measure depends on the embedding model and how its vectors are trained or normalized.

### Semantic retrieval

Vector search can retrieve passages that express similar concepts even when they do not share the same keywords.

For example, a query about “reducing API response time” may retrieve documentation discussing “latency optimization.”

### Limitations

Embeddings do not encode perfect semantic understanding. Vector search can struggle with:

- Exact identifiers and uncommon names.
- Numeric constraints.
- Negation and subtle distinctions.
- Very long or mixed-topic chunks.
- Domain terminology poorly represented in the embedding model.

Embedding quality, chunking, metadata, and query formulation all influence retrieval performance.

Use compatible embedding models for indexed documents and queries. Changing the embedding model may require re-embedding the corpus or maintaining separate indexes.

## 7. Keyword Search and Hybrid Retrieval

Keyword search matches explicit terms or lexical features. Vector search retrieves by semantic similarity.

These methods have complementary strengths.

| Approach | Typical strength | Typical weakness |
|---|---|---|
| Keyword search | Exact terms, IDs, names, and rare tokens | May miss semantically related wording |
| Vector search | Semantic similarity and paraphrases | May miss exact constraints or identifiers |
| Hybrid retrieval | Combines lexical and semantic evidence | Requires tuning and result fusion |

Hybrid retrieval can combine keyword and vector results using a rank-fusion method or another calibrated scoring strategy.

One common method is Reciprocal Rank Fusion (RRF):

\[
\operatorname{RRF}(d) =
\sum_{r \in R}
\frac{1}{k + \operatorname{rank}_r(d)}
\]

Here, \(R\) is the set of ranked result lists, \(d\) is a document, \(k\) is a smoothing constant, and \(\operatorname{rank}_r(d)\) is the rank of the document in list \(r\).

RRF combines rankings without requiring the raw scores from different retrieval systems to be directly comparable.

Hybrid retrieval is not automatically superior for every corpus. Compare it against simpler baselines using representative queries.

## 8. Query Processing and Retrieval

The user's original question may not be the best search query.

A retrieval pipeline can use query processing to:

- Expand abbreviations.
- Resolve references using conversation history.
- Rewrite ambiguous questions.
- Generate multiple focused subqueries.
- Extract entities, dates, versions, or constraints.
- Decompose compound questions into separate information needs.

For example, “What changed in the new release?” may require the product name, previous version, target version, and relevant release notes.

Query rewriting should preserve the user's intent. An incorrect rewrite can remove an important constraint or introduce an unsupported assumption.

For compound questions, multi-query retrieval can improve coverage. The system must then merge results, remove duplicates, and retain enough provenance to explain which evidence supports each part of the answer.

## 9. Ranking and Reranking

Initial retrieval often prioritizes recall: it aims to find a broad enough set of potentially relevant passages.

A reranker then evaluates the query and candidate passages more directly to improve ordering.

A common pipeline is:

1. Retrieve a larger candidate set using keyword and/or vector search.
2. Apply metadata and permission filters.
3. Score candidates with a reranking model or another relevance function.
4. Select the best passages within a context budget.
5. Preserve source identifiers and relevant metadata.

Reranking can improve relevance, but it adds computational cost and latency. It cannot recover a document that was never retrieved into the candidate set.

The number of retrieved candidates, reranker choice, and final context size should be tuned together. Selecting only a few highly ranked passages may improve precision while missing evidence required for a complete answer.

## 10. Context Assembly for Generation

Retrieval produces candidate evidence, not a finished answer. The selected passages must be organized into a useful context.

A context assembly stage should consider:

- Relevance to the current question.
- Source reliability and freshness.
- Coverage of all required subquestions.
- Duplicate and overlapping content.
- Conflicting claims.
- Context-window limits.
- Access-control requirements.
- Citation metadata.

A useful context should distinguish the task instructions from retrieved source content.

Example:

```text
TASK
Explain the documented retry behavior for the client library.

EVIDENCE
[Source: client-guide, section: Retries]
The client retries transient connection failures up to three times.

[Source: release-notes, version: 2.1]
Version 2.1 changed the default retry policy for rate-limit responses.

REQUIREMENTS
- Distinguish connection failures from rate-limit responses.
- Cite the supporting source for each claim.
- If a detail is not supported, state that it is unknown.
```

The evidence above is illustrative. A real application must insert actual retrieved passages and verify their accuracy.

Avoid placing unrelated passages in the context merely because they scored reasonably well in retrieval. Also avoid compressing the evidence so aggressively that the model loses distinctions needed to answer the question.

## 11. Grounding and Citation Validation

Grounded generation requires answers to be supported by the available evidence.

A system can instruct the model to cite source identifiers, but prompt instructions alone do not guarantee correct citations.

A robust design separates several checks:

1. **Retrieval validity:** Were relevant and authorized sources retrieved?
2. **Evidence coverage:** Does the evidence address every requested part?
3. **Claim support:** Is each material factual claim supported by its cited passage?
4. **Citation validity:** Does each citation refer to an existing source and location?
5. **Conflict handling:** Are contradictions identified rather than silently ignored?
6. **Abstention behavior:** Does the system acknowledge when evidence is insufficient?

For high-reliability applications, validate citations and important claims programmatically or with an independently evaluated verification stage.

A citation that points to a real document is not necessarily a citation that supports the accompanying claim.

## 12. RAG Failure Modes

### Retrieval misses

**Problem:** The relevant passage is absent from the candidate set.

**Potential causes:** Poor chunking, unsuitable embeddings, query mismatch, incomplete ingestion, or restrictive filters.

**Mitigation:** Inspect retrieval failures, expand query coverage, test hybrid search, and evaluate candidate recall.

### Irrelevant retrieval

**Problem:** Retrieved passages are topically related but do not answer the question.

**Potential causes:** Ambiguous queries, poor ranking, broad chunks, or weak relevance signals.

**Mitigation:** Improve query formulation, use reranking, and evaluate relevance separately from generation.

### Missing context

**Problem:** A retrieved passage contains the main fact but omits the qualification required for a correct answer.

**Mitigation:** Use structure-aware chunking, parent-child retrieval, or contextual expansion.

### Stale or conflicting sources

**Problem:** The system uses an obsolete version or merges contradictory information.

**Mitigation:** Track source versions and timestamps, apply freshness policies, and define precedence rules where justified.

### Unsupported generation

**Problem:** The model produces claims that do not follow from the retrieved evidence.

**Mitigation:** Require evidence-linked claims, validate citations, test abstention, and measure grounded accuracy.

### Lost metadata

**Problem:** A passage is retrieved but its source location or version is missing.

**Mitigation:** Preserve provenance through parsing, indexing, retrieval, and generation.

### Permission leakage

**Problem:** A user receives information from a document they are not authorized to access.

**Mitigation:** Enforce access control in retrieval and tool infrastructure. Do not rely on the model to suppress unauthorized content after it has been placed in context.

### Over-retrieval

**Problem:** Too many passages consume the context budget and introduce distracting evidence.

**Mitigation:** Tune candidate selection, deduplicate overlapping passages, and measure context sufficiency.

## 13. RAG Evaluation

RAG evaluation should separate retrieval quality from generation quality and end-to-end task success.

### Retrieval metrics

- **Recall@k:** Fraction of known relevant items retrieved within the top \(k\) results.
- **Precision@k:** Fraction of the top \(k\) results that are relevant.
- **MRR (Mean Reciprocal Rank):** Measures how highly the first relevant result is ranked.
- **nDCG@k:** Measures ranking quality while accounting for graded relevance.

These metrics require an appropriate relevance-labeled dataset. The exact metric definitions and relevance judgments should be documented.

### Generation metrics

- Answer correctness against known references.
- Groundedness or faithfulness to the supplied evidence.
- Completeness across required subquestions.
- Citation precision and coverage.
- Appropriate abstention when evidence is insufficient.
- Output-format validity.

Automated judges can help scale evaluation, but they can also miss unsupported claims or reward plausible-sounding answers. Use human review or deterministic checks where appropriate, particularly when the cost of an error is high.

### End-to-end metrics

- Task success rate.
- Latency.
- Token usage and inference cost.
- Retrieval and reranking cost.
- Failure rate by query category.
- Performance on outdated, ambiguous, or adversarial inputs.

Evaluate representative query types, including exact lookups, paraphrases, multi-hop questions, version-specific questions, and questions that cannot be answered from the corpus.

## 14. Practical Experiment Design

A useful RAG experiment changes one major design decision at a time.

For example:

| Experiment | Baseline | Variant |
|---|---|---|
| Chunking | Fixed-size chunks | Structure-aware chunks |
| Retrieval | Vector search | Hybrid retrieval |
| Ranking | Initial retrieval ranking | Reranked candidates |
| Context | Top-ranked passages | Top-ranked passages with parent context |
| Generation | General answer prompt | Evidence-constrained answer prompt |

For each variant:

1. Use the same evaluation queries.
2. Keep the source corpus and answer criteria consistent.
3. Measure retrieval and generation separately.
4. Track cost and latency.
5. Inspect failure cases, not only aggregate scores.
6. Retain the simplest configuration that meets the quality requirements.

Avoid choosing a configuration based solely on a few successful demonstrations. A system may perform well on common queries while failing on rare identifiers, conflicting sources, or missing-evidence cases.

## 15. When to Use RAG vs. Fine-Tuning

RAG and fine-tuning address different needs.

| Requirement | RAG | Fine-tuning |
|---|---|---|
| Access to external documents at inference time | Directly suited | Does not itself provide live retrieval |
| Frequent knowledge updates | Often easier through reindexing | May require additional training or adaptation |
| Grounding answers in specific source passages | Supports retrieval-based citations | Does not inherently provide source provenance |
| Adapting response style or task behavior | Can help through instructions and context | Can be useful when consistent behavior adaptation is needed |
| Private knowledge base access | Can retrieve authorized records | Training data handling introduces different considerations |

The approaches can be combined. Fine-tuning may adapt behavior, while RAG supplies current evidence.

Neither technique guarantees correctness or eliminates the need for evaluation, security controls, and validation.

## 16. Production Readiness Checklist

Before deploying a RAG system, verify that:

- [ ] Source documents are parsed accurately.
- [ ] Chunking preserves important semantic relationships.
- [ ] Metadata and provenance survive every pipeline stage.
- [ ] Retrieval is evaluated against labeled queries.
- [ ] Exact-match and semantic retrieval needs are both considered.
- [ ] Ranking and context selection are measured independently.
- [ ] The context contains sufficient evidence for the full question.
- [ ] Answers distinguish supported claims from unknown information.
- [ ] Citations are checked for both validity and claim support.
- [ ] Source freshness and version conflicts are handled explicitly.
- [ ] Access controls are enforced before unauthorized content reaches the model.
- [ ] Latency, cost, failures, and data-quality issues are observable.
- [ ] The system is tested with realistic and adversarial cases.

## 17. Key Takeaways

RAG connects a language model to an external knowledge source by retrieving relevant evidence and including it in the generation context.

Its reliability depends on the entire pipeline: ingestion, parsing, chunking, indexing, query processing, retrieval, ranking, context assembly, generation, and validation.

The key engineering principle is to evaluate retrieval and generation separately, preserve evidence provenance, and never assume that retrieved context automatically makes the final answer correct.