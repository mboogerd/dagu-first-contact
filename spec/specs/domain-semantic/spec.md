# Domain — Semantic (Stage 3b)

Generate human-readable summaries for each domain. LLM-driven but cached.

**Phase.** Stage 3b.

**Input → Output.** `domains/<domain>/members.yaml` + member docs and their extractions → `domains/<domain>/<domain-name>__summary.md` (+ orphan domain name updates in `domains/_index.yaml`).

---

## Behavior

- For each domain, generate `<domain-name>__summary.md` covering responsibilities and interactions, from member docs and their extractions.
- Orphan domains additionally get a meaningful name (replacing `orphan-<index>`) generated from their summary; the rename is recorded in `_index.yaml`.
- Cache key: `hash(sorted(member_content_hashes) + prompt_version + model)`.
- Summary only regenerates when membership or member content changes.

## Domain summary shape

Free-form markdown. The summary feeds:

- [domain-hierarchy](../domain-hierarchy/spec.md) (super-domain identification).
- [consolidate](../consolidate/spec.md) (as context for criticality assessment and cross-domain findings).
- [report](../report/spec.md) (landscape section).

Each summary should cover, at minimum:

- **Purpose.** What this domain represents.
- **Responsibilities.** What its members do collectively.
- **Interactions.** Who it talks to (other domains, external systems).
- **Notable concerns.** Anything that doesn't fit but the consultant should know.

The exact section structure is not contracted (the domain's content drives it), but downstream consumers expect the four bullet topics above to be addressable.

## Related decisions

- [D-9](../../decisions/0009-hash-keyed-summary-cache.md) summary cache key.

## Failure modes

- **Generic summaries on heterogeneous domains.** A domain with mixed contents produces a vague summary. Acceptable: vagueness is signal that the domain may need splitting (a concern for [domain-hierarchy](../domain-hierarchy/spec.md) or manual review).
- **Stale summary after member-content edits.** Cache key is on member content hashes; edits invalidate correctly.
