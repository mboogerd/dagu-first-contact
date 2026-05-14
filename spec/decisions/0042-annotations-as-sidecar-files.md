# [D-42] Cross-domain findings are standalone markdown files; per-domain outputs remain immutable

**Status.** Accepted (revised — findings are now markdown files, not JSON sidecars).

**Decision.** Cross-domain conflict detection (phase 4f of consolidate) does NOT modify per-domain consolidated group files. Instead, it writes `<domain-name>__cross-domain-findings.md` as a standalone markdown file in the domain's folder. Downstream consumers (review queue, report) reference findings via wikilinks.

**Rationale.** Principle 2 — immutability of upstream layer outputs — is a core invariant. Findings as standalone files preserve immutability and make them navigable in Obsidian via wikilinks.

**Alternatives considered.**
- Mutate per-domain group files directly — breaks immutability principle.
- JSON sidecar files (original design) — less navigable in Obsidian; markdown with wikilinks is preferred.

**Trade-offs accepted.** An extra file per non-leaf domain. Acceptable.

**Related.** [consolidate spec](../specs/consolidate/spec.md); Principle 2.
