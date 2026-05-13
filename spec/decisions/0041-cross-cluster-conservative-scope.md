# [D-41] Cross-cluster scope: contradiction and scope_mismatch only

**Status.** Accepted, **flagged for re-examination**.

**Flag.** The conservative scope was challenged in the reviewer pass: "what part of the change plan crosses subsystem boundaries?" is a question the assessment is trying to answer, and the exclusions might hide signal there. Re-examine after the first real run on the corpus produces actual cross-cluster findings.

**Decision.** Cross-cluster reconciliation detects only two of the five conflict kinds defined in [D-35]: `contradiction` and `scope_mismatch`. `status_disagreement`, `type_disagreement`, and `version_skew` are explicitly excluded.

**Rationale.** Same-named concepts in different clusters legitimately differ on status and type. A "user" requirement in the auth cluster and a "user" requirement in the analytics cluster aren't necessarily about the same user; their independent statuses are meaningful, not contradictory. Cross-cluster `version_skew` is unusual and would mostly produce noise. The kinds that DO matter cross-cluster are real disagreements about what the system should do (contradiction) or for whom (scope_mismatch).

**Alternatives considered.**
- All five kinds — noisy; floods review queue with structural artifacts of clustering.
- Only contradiction — `scope_mismatch` is exactly the kind of subtle cross-subsystem conflict the consultant most wants to know about.

**Trade-offs accepted.** May miss legitimate cross-cluster status/type/version conflicts. Acceptable for v1: these are rare enough that the consultant can surface them through ad-hoc review.

**Related.** [cross-cluster spec](../specs/cross-cluster/spec.md); [open-questions.md](../open-questions.md) (re-examination after first real run).
