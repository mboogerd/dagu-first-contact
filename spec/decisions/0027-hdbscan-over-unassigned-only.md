# [D-27] HDBSCAN runs over unassigned docs only

**Status.** Accepted.

**Decision.** HDBSCAN is not a primary clustering algorithm. It runs only over docs that were unassigned (below `assignment_threshold` against all seed clusters), to surface orphan clusters that don't correspond to any existing git repo.

**Rationale.** Repos are the strong prior ([D-8]); HDBSCAN is the fallback for genuine outliers. Running HDBSCAN over all docs would dilute the repo prior and produce unstable cluster identities across runs.

**Alternatives considered.**
- HDBSCAN over everything — loses the repo prior.
- No HDBSCAN; unassigned docs stay unassigned — legitimate orphan clusters would be lost.

**Trade-offs accepted.** Two clustering mechanisms (nearest-seed + HDBSCAN). Acceptable: each is simple in isolation.

**Related.** [cluster-structural spec](../specs/cluster-structural/spec.md).
