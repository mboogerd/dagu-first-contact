# [D-19] Taxonomy discovery blocks Extract

**Status.** Accepted.

**Decision.** [Taxonomy discovery](../specs/taxonomy/spec.md) runs once per assessment and produces `config/taxonomy.locked.yaml`. [Extract](../specs/extract/spec.md) refuses to run without it. Re-running discovery produces a new locked version, which invalidates extraction caches via the extractor cache key.

**Rationale.** "Pay the cost up front." Locking before bulk extraction prevents the worse failure mode of finding taxonomy gaps after thousands of extracted records exist with stale enum values. Cache-key versioning means a re-lock cleanly invalidates affected work.

**Alternatives considered.**
- Discovery as a side-script, optional — easy to skip; reproducibility suffers.
- Discovery as a sub-step inside Extract — couples concerns.

**Trade-offs accepted.** Adds one stage and one blocking review step. Acceptable cost for the reliability gain. A consultant who wants to iterate fast can keep using the starting taxonomy by running `taxonomy:lock --from-starting`; this is recorded explicitly in the lock metadata as a known shortcut.

**Related.** [taxonomy spec](../specs/taxonomy/spec.md); [D-21](0021-taxonomy-debt-post-lock.md).
