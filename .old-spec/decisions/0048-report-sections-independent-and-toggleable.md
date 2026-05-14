# [D-48] Sections are independently authored and toggleable via config

**Status.** Accepted.

**Decision.** Each report section is an independent renderer. Each reads its own inputs and produces its own markdown block. The `sections` list in `config/report.yaml` controls which sections run and in what order.

**Rationale.** Independence makes the rendering logic small and testable per section, lets the consultant disable sections they don't want, and makes future section additions straightforward.

**Alternatives considered.**
- Monolithic renderer with the whole report in one function — harder to maintain.
- Fixed section order and presence — less flexible.

**Trade-offs accepted.** Per-section state (like the report frontmatter's `counts`) must be assembled before sections run. Acceptable: frontmatter assembly is its own phase.

**Related.** [report spec](../specs/report/spec.md).
