# [D-27] HDBSCAN runs over unassigned docs only

**Status.** Accepted.

**Decision.** HDBSCAN is not a primary domain assignment algorithm. It runs only over docs that were unassigned (below `assignment_threshold` against all seed domains), to surface orphan domains that don't correspond to any existing git repo.

**Rationale.** Repos are the strong prior ([D-8]); HDBSCAN is the fallback for genuine outliers. Running HDBSCAN over all docs would dilute the repo prior and produce unstable domain identities across runs.

**Alternatives considered.**
- HDBSCAN over everything — loses the repo prior.
- No HDBSCAN; unassigned docs stay unassigned — legitimate orphan domains would be lost.

**Trade-offs accepted.** Two assignment mechanisms (nearest-seed + HDBSCAN). Acceptable: each is simple in isolation.

**Related.** [domain-structural spec](../specs/domain-structural/spec.md).
