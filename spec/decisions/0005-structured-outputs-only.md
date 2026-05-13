# [D-5] Structured outputs only

**Status.** Accepted.

**Decision.** Every LLM extraction uses provider structured-output / tool-calling against a JSON schema. No JSON-in-markdown.

**Rationale.** Eliminates a whole class of parsing failures. Schema doubles as documentation.

**Alternatives considered.**
- Freeform with regex parsing.

**Trade-offs accepted.** Provider lock-in to structured-output APIs. Acceptable for a one-shot assessment.

**Related.** Principle 6 in [principles.md](../principles.md).
