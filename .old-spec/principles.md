# Principles

These are the immutable constraints of the pipeline. They are the "constitution" — every design decision must respect them; deviations require explicit justification in a decision document under [decisions/](decisions/).

Every generation prompt that produces new spec content or implementation code should be primed with this file.

---

## 1. Filesystem is the database

Every artifact is a file. Git tracks everything. No external state stores.

*See [D-1](decisions/0001-filesystem-as-db.md).*

## 2. Immutable layers

Each pipeline stage reads from upstream and writes to its own directory. Never mutate upstream.

## 3. Content-addressed caching

Every LLM call is keyed on `hash(prompt + input + model + schema)`. Re-runs are nearly free.

## 4. Uniform document shape after ingestion

All evidence becomes `{markdown + YAML frontmatter}`. Everything downstream is source-agnostic.

*See [D-2](decisions/0002-uniform-normalized-doc-shape.md).*

## 5. Deterministic orchestration, LLM-powered steps

Plain code orchestrates the pipeline graph. LLMs do work *inside* steps, not *between* them.

*See [D-14](decisions/0014-deterministic-orchestration.md).*

## 6. Structured outputs only

No freeform JSON-in-markdown. Use provider structured-output / tool-calling. Every extractor has a schema.

*See [D-5](decisions/0005-structured-outputs-only.md).*

## 7. Provenance is preserved end-to-end

Every derived artifact records its inputs (content hashes), the model, and the prompt version that produced it.

## 8. Cheap-first

Embeddings before LLMs. Cheap models for high-volume mechanical work. Expensive reasoning models reserved for consolidation.

*See [D-13](decisions/0013-expensive-model-at-consolidation-only.md).*

---

## How principles relate to the rest of the spec

- **Component specs under `specs/<component>/spec.md`** describe externally-observable behavior. They must comply with these principles; if they appear to violate one, that's a bug in the spec, not an exception.
- **Decision documents under `decisions/`** are where deviations or non-obvious applications of principles get recorded with rationale.
- **Change folders under `changes/<NNN>-slug/`** propose new work. Their `design.md` must show how the proposal complies with these principles (or explicitly mark a deviation for review).

## Adding or changing principles

A principle is changed only via an explicit change folder whose scope is "amend principles." Such changes require human review (no automation). Existing decisions that depend on the changed principle must be re-examined as part of the same change.
