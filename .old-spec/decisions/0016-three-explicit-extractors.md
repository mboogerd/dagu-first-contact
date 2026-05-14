# [D-16] Three explicit extractors with distinct schemas

**Status.** Accepted.

**Decision.** Three extractors — `extract_requirements`, `extract_interactions`, `extract_concepts` — each with its own prompt and schema. Interactions are scoped to **runtime topology** only; concepts are split into `business_concept` and `technical_concept`; requirements carry both `type` and `status`.

**Rationale.** Each extractor answers a distinct question: "what must the system do?" (requirements), "who talks to whom?" (interactions), "what concepts is the system organized around?" (concepts). Mixing them in one extractor produces vague output. Keeping them separate makes prompts focused and downstream consumers explicit about what they need.

**Alternatives considered.**
- One mega-extractor producing all three — kitchen-sink prompt.
- Two extractors (requirements + topology) — concepts are useful for domain naming and for linking business capabilities to technical domains.
- Per-source-type extractor variants — rejected by [D-4].

**Trade-offs accepted.**
- Three LLM calls per document instead of one (cost increase). Mitigated by [D-13] (cheap model for extraction) and cache reuse on re-runs.
- Some information is awkward to attribute — e.g., a sentence may imply a requirement, an interaction, AND a concept. Each extractor independently emits its view; that's correct, not duplication.

**Related.** [extract spec](../specs/extract/spec.md); [D-4](0004-source-agnostic-extractors.md).
