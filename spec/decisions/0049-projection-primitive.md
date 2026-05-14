# [D-49] Projection primitive

**Status.** Accepted. Supersedes [D-22](0022-git-repo-curated-summary.md).

**Decision.** Introduce a **projection** as a named, resolvable, parameterized operation that takes an evidence record and produces one or more downstream-ready normalized documents. Replace the `normalization_kind: raw_text | curated_summary` enum with explicit projections per source. Move all "make evidence downstream-ready" logic into projection implementations.

A projection name is `<adapter>:<projection>` (e.g., `git:repo_summary`, `jira:bulk_download`, `rfp:section_split`). Each projection has a contract file at `spec/projections/<adapter>__<projection>.md` and an implementation directory at `assessment/projections/<adapter>__<projection>/`.

The `projections/` tree IS the normalized layer. There is no separate `normalized/` tree. Every downstream stage reads from `projections/<source>/<id>/<projection>/<file>.md`.

**Rationale.** The git adapter was special-cased as the only source producing an LLM-curated summary. This doesn't generalize. Cross-functional documents (RFPs, spreadsheets) need splitting into per-subsystem partials for proper domain assignment. Large evidence benefits from multiple projections consumed by different stages. The projection primitive addresses all three uniformly and replaces the git special case with one instance of a general mechanism.

**Alternatives considered.**
- Keep `normalization_kind` and add more values — doesn't handle multi-output cases.
- Per-adapter special-casing for each new need — accumulates technical debt.
- Generic "transformer" abstraction — over-general; projection is scoped to evidence→normalized-doc.

**Trade-offs accepted.** One more concept in the spec. Mitigated by the concept being intuitive (evidence goes in, downstream-ready docs come out) and by the existing git special case already being the pattern, just unnamed.

**Related.** [ingest spec](../specs/ingest/spec.md); [D-22](0022-git-repo-curated-summary.md) (superseded); [D-50](0050-source-declared-intent.md); change folder [001-projection-primitive](../changes/001-projection-primitive/proposal.md) (origin).
