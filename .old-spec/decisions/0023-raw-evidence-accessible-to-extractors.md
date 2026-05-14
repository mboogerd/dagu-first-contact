# [D-23] Raw evidence remains accessible to extractors

**Status.** Accepted.

**Decision.** Extractors are not restricted to projection outputs. When a projection's contract declares that evidence access is expected, extractors MAY read the underlying `evidence/<source_type>/<source_id>/` for additional detail (e.g., requirement extraction from git reads the `repo_summary` projection output AND may consult specific code files referenced therein).

**Rationale.** Domain assignment needs a uniform, low-fidelity representation (the summary). Extraction needs high-fidelity, source-native evidence (the code). Forcing one shape on both wastes signal. Honest about the asymmetry.

**Alternatives considered.**
- Only projection outputs are visible downstream — requirements extraction from a 500-word repo summary loses too much.
- Mandate raw access for all extractors — over-engineering for sources that are already curated.

**Trade-offs accepted.** Extractors that consult `evidence/` are no longer purely source-agnostic. Mitigation: the asymmetry is bounded to git in v1.

**Related.** [extract spec](../specs/extract/spec.md); [D-49](0049-projection-primitive.md).
