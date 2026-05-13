# [D-17] Bounded taxonomy-discovery termination

**Status.** Accepted.

**Decision.** Per-source-type discovery loop terminates on whichever comes first: (a) two consecutive iterations that do not "advance learning" (introduce a new proposed enum value, a new ambiguity pair, or a new gap report), or (b) a hard per-source iteration cap (default 15).

**Rationale.** "Iterate until stable" without a computable definition of stability doesn't terminate. Defining advancement as *new* findings, not repeated ones, gives a concrete rule. The cap is safety against pathological non-convergence on noisy sources.

**Alternatives considered.**
- Fixed iteration count per source — wastes calls on quickly-stable sources; under-samples noisy ones.
- Stop after N iterations with no advancement (N>2) — marginal benefit.
- Vibes-based "looks stable to me" — not reproducible.

**Trade-offs accepted.** A source type with subtle late-emerging variants may be cut off by the cap. The cap is configurable; raising it costs more discovery calls but doesn't affect extraction.

**Related.** [taxonomy spec](../specs/taxonomy/spec.md).
