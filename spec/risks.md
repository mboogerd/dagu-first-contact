# Known risks

Risks we've accepted, with mitigations. Risks that depended on dropped features (eval framework, calibration, archival) have been removed; those concerns moved to [open-questions.md](open-questions.md) where applicable.

---

## [R-1] Agent-based orchestration appeals; deterministic orchestration was chosen

Agent orchestration stacks non-determinism, makes debugging hard, burns tokens reasoning about work rather than doing it, and undermines reproducibility — exactly where we need it. Decision is [D-14](decisions/0014-deterministic-orchestration.md). If a user-facing chat interface over the assessment results is desired later, it's a separate layer that reads the artifacts the deterministic pipeline produces.

## [R-2] Cross-cluster reconciliation is targeted, not exhaustive

The [cross-cluster](specs/cross-cluster/spec.md) stage addresses the most valuable form of cross-cluster conflict (sibling-subtree contradictions and scope mismatches between similar-statement requirements) but does not exhaustively compare every pair of requirements across the entire tree. By design ([D-41](decisions/0041-cross-cluster-conservative-scope.md), [D-44](decisions/0044-hard-candidate-cap-halt-warn.md)), it skips three conflict kinds and bounds the candidate pool by embedding similarity. Conflicts that don't surface via embedding similarity (e.g., very different vocabulary describing the same conflict) will not be detected.

## [R-3] Embedding-based cluster assignment will misfile some docs

A Jira ticket can semantically match repo A but actually be about repo B. Mitigations:

- Use explicit hints in normalized frontmatter where available (e.g., Jira `component` → repo mapping).
- Surface low-confidence assignments in a review queue, not silently.
- Accept that 5–10% misfiling is fine at the assessment stage.

The consultant has noted that pure embedding-based clustering may not be trustworthy enough on its own; an open issue tracks a future revision (see [open-questions.md](open-questions.md)).

## [R-4] Prompt drift invalidates cache

Tuning prompts during the assessment invalidates cached outputs for that extractor. Cache key includes prompt version (so this is *correct*, not buggy), but it means budget for regeneration on prompt changes. Mitigation: stabilize prompts on a small sample before running across all evidence.

## [R-5] Confidence and criticality scoring is uncalibrated

First runs will produce a noisy review queue. Calibration is **deferred in v1** — the consultant accepts default weights and treats the review queue ordering as a starting point rather than a ranked answer. See [open-questions.md](open-questions.md) for the deferred calibration design.

## [R-6] Source-authority weights are configured guesses

`config/consolidation.yaml: source_authority` ships with default weights (RFP 1.0, code 0.8, Jira 0.6, etc.) that are reasonable but not validated for any specific client. The defaults affect reconciliation outcomes and the authority-weighted-agreement signal in confidence. Mitigation: authority weights are config, not code; the consultant can tune them mid-assessment with selective cache invalidation per [D-38](decisions/0038-layered-consolidation-caching.md).

## [R-7] Lossy normalization for complex sources

Spreadsheets with rich formatting, RFPs with embedded tables/images, and transcripts with speaker overlap may lose information at normalization. Mitigation: preserve original in `evidence/`; surface "normalization warnings" alongside the normalized doc.

## [R-8] Filesystem scaling

At medium scale (dozens of repos, thousands of tickets — the current target), the filesystem is fine. If scope grows to large (hundreds of repos, 10k+ tickets), expect: slow `git status`, slow recursive listings, and pressure to introduce an index. Mitigation: revisit at that point, not pre-emptively.

## [R-9] Taxonomy discovery suffers from sample-driven blindness

Discovery samples ~15 docs per source type. A source type with subtle distinctions that only appear in unsampled docs will leave gaps in the locked taxonomy. Mitigations: the starting taxonomy is a floor ([D-18](decisions/0018-starting-taxonomy-as-floor.md)) so legitimate values aren't silently pruned; the discovery proposal flags low-confidence single-finding additions for explicit consultant review; [D-21](decisions/0021-taxonomy-debt-post-lock.md) explicitly allows documenting post-lock gaps without restarting.

## [R-10] Discovery and extraction cost coupling

Re-running discovery produces a new `taxonomy.locked.yaml` version, which invalidates the entire extraction cache. This is correct behavior but it means a small late-stage taxonomy edit costs a full re-extraction. Mitigation: lock once, lock well, and use [D-21](decisions/0021-taxonomy-debt-post-lock.md) to defer non-critical taxonomy revisions to a future run.

## [R-11] Repo summary is a single LLM call that drives cluster seeding

Cluster seeds come from git-repo curated summaries ([D-22](decisions/0022-git-repo-curated-summary.md)). A weak or misleading summary contaminates every downstream assignment to that cluster. Mitigations: the consultant can manually edit `normalized/git/<repo>.md` after Ingest (the next `embed` run refreshes the sidecar and the next `cluster` run reflects the edit); the `Notes` section of the template explicitly invites uncertainty flagging.

## [R-12] Local embedding model quality is below frontier

`nomic-embed-text-v1.5` is good enough for cosine-similarity clustering of moderately-sized docs but is not state-of-the-art. Edge cases (technical jargon-heavy transcripts, multilingual content, deeply contextual short documents) may cluster poorly. Mitigations: low-confidence band surfaces borderline assignments for review; `assignment_hint` frontmatter overrides; the fallback path to a stronger model is documented if a specific corpus genuinely defeats the local model.

## [R-13] Repo summary LLM may miss non-obvious code patterns

The summarize_repo prompt sees README, top-level structure, manifests, and `docs/`. Code in less-discoverable locations (deep packages, dynamically loaded modules) won't appear in the summary unless the README or docs mention it. Acceptable for clustering, but it means the repo summary should never be treated as a substitute for the actual code during extraction ([D-23](decisions/0023-raw-evidence-accessible-to-extractors.md) addresses this).

## [R-18] Grouping is the longest-lever single failure in consolidation

A bad grouping decision (over-merge or under-merge) propagates through everything downstream: conflict detection sees the wrong members, reconciliation produces a wrong resolved statement, scoring is computed against the wrong set. Mitigation: groups are persisted as their own artifact (`groups.json`) for inspection; LLM verification verdicts are recorded with rationale; manual override of grouping is supported by editing `groups.json` and re-running consolidation.

## [R-20] Manual reconciliation overrides go stale silently

A `config/consolidation_overrides/<group_id>.yaml` authored when a group had three members becomes orphaned when extraction changes the group's membership and thus its `group_id`. Mitigation: stale overrides emit warnings at consolidation time (their `group_id` is no longer present in `groups.json`); the consultant decides whether to update or delete.

## [R-21] Cross-cluster candidate explosion on clustered corpora

Some corpora (e.g., microservice ecosystems with shared patterns repeated per service) produce many cross-cluster candidate pairs because the same statements legitimately recur. The hard cap ([D-44](decisions/0044-hard-candidate-cap-halt-warn.md)) prevents runaway cost but doesn't solve the underlying signal-to-noise problem. Mitigation: raise the embedding threshold; the consultant accepts that very-similar-but-legitimately-distinct requirements aren't real conflicts.

## [R-22] Cross-cluster LLM verification false negatives are invisible

When the verifier rejects a candidate as `not_a_conflict`, that decision is cached and not revisited unless cache keys change. A genuine but subtle conflict that the LLM missed on first pass will stay missed. Mitigation: the `needs_review` verdict catches the uncertainty cases; the consultant can review `cross_cluster/conflicts.json` for `not_a_conflict` entries when investigating specific concerns; future verifier prompt improvements invalidate the cache and re-verify.

## [R-23] Cross-cluster boost may distort priority for low-criticality items

A `minor`-criticality cross-cluster conflict gets `0.15 * 0 + 0.20 = 0.20` priority, which could float above a `moderate`-criticality non-conflict item at `0.40 * 0.5 = 0.20`. Whether this is correct is calibration territory. In v1, the boost magnitude is a guess; the consultant interprets cross-cluster-conflict surfacing as informational.

## [R-24] reports/ accumulates without bound

Every `report` invocation writes a new timestamped file ([D-46](decisions/0046-reports-always-timestamped.md)). Over many iterations of an assessment, `reports/` can accumulate dozens to hundreds of files. Mitigation: the recommended discipline is to gitignore `reports/*.md` except for snapshots the consultant explicitly wants to commit. The spec does not enforce a retention policy.

## [R-25] No narrative synthesis in the report

The report is deterministic and rendering-only — no LLM-generated executive summary or theme synthesis. The consultant has to do the synthesis when they write the client deliverable. Acceptable: synthesis is the consultant's value-add; automating it would either be low-quality or non-reproducible. A future optional narrative section could be added without changing the core architecture.
