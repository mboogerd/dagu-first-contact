# Taxonomy Discovery (Stage 1.5)

Validate and refine the starting taxonomy against real evidence before bulk extraction locks in expensive token spend. Produce a locked taxonomy that downstream extractors consume.

**Phase.** Stage 1.5.

**Input → Output.** `projections/` + `config/taxonomy.starting.yaml` → `taxonomy/` + `config/taxonomy.locked.yaml`.

**When it runs.** Once per assessment, blocking. [Extract](../extract/spec.md) refuses to run without `config/taxonomy.locked.yaml`. Re-running this stage produces a new `taxonomy.locked.yaml` version; downstream stages with cached outputs based on the prior version are invalidated through normal cache-key versioning.

---

## Approach

A bounded discovery loop per source type, followed by global consolidation and human-reviewed locking.

### 1.5a · Stratified sampling, per source type

- For each source type in scope, repeatedly sample one **projection output** until learning stalls.
- Sampling prioritizes **diversity axes**: size (small/medium/large), age (recent/median/old), structure (e.g., for Jira: bug/story/epic; for git: code/config/docs/specs), topic (by embedding to spread coverage), and **projection** (when a source type has more than one projection enabled, ensuring discovery sees outputs from each projection rather than over-sampling whichever produced more docs).
- Each iteration's pick maximizes a diversity score against previously-sampled docs in this source type. Ties broken by earliest age.
- Sampled docs are recorded; the same doc is not re-sampled within a source type.

### 1.5b · Per-document finding extraction (LLM, cached)

- For each sampled doc, run a single LLM call with the `discover_taxonomy` prompt and the **current starting taxonomy** as context.
- Output is a `TaxonomyFinding` (below): which existing enum values applied, which were ambiguous (and against what alternative), which were missing (with proposed new value, rationale, supporting excerpt).
- Structured output via tool-calling; cached on `hash(prompt + doc_content_hash + current_taxonomy_hash + model)`.

### 1.5c · Per-iteration learning evaluation

- An iteration **advances learning** if it introduces at least one of:
  - a new proposed enum value not seen in previous iterations of this source type;
  - a new ambiguity pair not seen previously;
  - a new gap report against an enum that previously showed no gaps.
- Repeated observation of an existing finding does **not** count as advancing learning, but increases its support count (used during consolidation).

### 1.5d · Termination per source type

- The loop for a source type terminates when **two consecutive iterations do not advance learning**, OR when the **per-source iteration cap** is reached (default: 15 iterations; configurable).
- The cap is a belt-and-suspenders safety against pathological non-convergence on noisy sources.

### 1.5e · Cross-source consolidation

- After all source types finish, all `TaxonomyFinding` records are aggregated into `taxonomy/findings.json`.
- Findings are merged per schema target (e.g., `requirement.type`, `interaction.kind`).
- For each target, the script proposes: **additions** (new values with cross-source support), **refinements** (description tightening based on observed usage), **removals** (starting values never used — flagged as `requires_human_approval: true` per [D-18]), and **ambiguities** (pairs flagged repeatedly, with proposed prompt-level guidance).

### 1.5f · Proposal generation

- A human-readable `taxonomy/proposal.md` is written, showing a diff vs. the starting taxonomy: what's added, refined, proposed-for-removal, and flagged-ambiguous, each with rationale and supporting excerpts (linked to the original sampled docs).
- The proposal is the review artifact. The consultant edits it (accepting, rejecting, or modifying proposals) and then runs the lock command.

### 1.5g · Lock

- The lock command reads the (possibly edited) proposal and writes `config/taxonomy.locked.yaml`.
- Lock records: `version` (hash of content), `locked_at` (timestamp), `sources_used` (which source types contributed to discovery).
- After lock, downstream stages may proceed. Discovery iterations remain in `taxonomy/` as the audit trail of why the taxonomy looks the way it does.

## Data shapes

### Starting and Locked Taxonomy (`config/taxonomy.{starting,locked}.yaml`)

The starting taxonomy mirrors the enum values defined in the [extract spec](../extract/spec.md) (requirement `type` / `status`, interaction `kind` / `evidence_strength`, concept `kind`). It is the **floor**: this stage may add, refine, or split values, but removals require human approval in the proposal review.

```yaml
version: "<semver or hash>"
locked_at: <ISO timestamp; null in starting>
sources_used: [git, jira, rfp, spreadsheet, transcript]  # in locked only

requirement:
  type:
    - value: functional
      description: A behavior the system must perform.
    - value: quality_attribute
      description: A measurable property (performance, security, availability, ...).
    # ...
  status:
    - value: implemented
      description: Evidence shows it is in production.
    # ...

interaction:
  kind:
    - value: http_call
      description: Synchronous HTTP/REST request, including GraphQL over HTTP.
    # ...
  evidence_strength:
    - value: observed
      description: Extracted from code, config, or specs that implement the interaction.
    # ...

concept:
  kind:
    - value: business_concept
      description: A business capability or problem area.
    - value: technical_concept
      description: An implementation-side area or concern.
```

The **locked** taxonomy is the artifact downstream stages consume. The starting taxonomy stays in git as the prior; the locked taxonomy is the prior plus discovery findings, reviewed and accepted.

### TaxonomyFinding (`taxonomy/iterations/.../iter-NN.json`)

One record per sampled document per iteration. Captures what the discovery LLM saw and proposed for that document.

```json
{
  "iteration": 3,
  "source_type": "rfp",
  "source_id": "doc-12",
  "projection": "rfp:section_split",
  "projection_output": "03-payments-integration.md",
  "sampled_for": "diversity_axes_satisfied",
  "diversity_axes": {"size": "large", "age": "old", "structure": "many_sections", "projection": "section_split"},
  "observations": {
    "requirement_type": {
      "values_used": ["functional", "constraint"],
      "ambiguous": [
        {"existing": "constraint", "alternative": "assumption",
         "rationale": "Statement reads more like a stated belief than a hard constraint."}
      ],
      "missing": [
        {"proposed_value": "regulatory_constraint",
         "rationale": "Several statements distinguish regulatory requirements from technical constraints.",
         "example_excerpt": "..."}
      ]
    },
    "interaction_kind": { "values_used": [], "ambiguous": [], "missing": [] },
    "concept_kind": { "values_used": [], "ambiguous": [], "missing": [] }
  },
  "advances_learning": true,
  "advance_reason": "Proposed new value 'regulatory_constraint' for requirement.type"
}
```

`advances_learning` is set per iteration based on the rule in [D-17]. The discovery loop terminates when this is `false` for two consecutive iterations per source type, or the per-source iteration cap is hit (whichever comes first).

### Consolidated findings (`taxonomy/findings.json`)

Aggregates all per-document findings into a single proposal-ready structure.

```json
{
  "schema_target": "requirement.type",
  "starting_values": ["functional", "quality_attribute", "constraint", "assumption", "change_plan"],
  "proposed_additions": [
    {
      "value": "regulatory_constraint",
      "rationale": "<merged across sources>",
      "supporting_findings": ["rfp:doc-12:section_split:iter-3", "jira:PROJ-1287:bulk_download:iter-1"],
      "confidence": "high"
    }
  ],
  "proposed_refinements": [
    {
      "value": "quality_attribute",
      "current_description": "A measurable property...",
      "proposed_description": "...",
      "rationale": "Sources consistently describe quality attributes with explicit thresholds; description should reflect that."
    }
  ],
  "proposed_removals": [
    {
      "value": "assumption",
      "rationale": "Not used in any sampled document.",
      "supporting_findings": [],
      "requires_human_approval": true
    }
  ],
  "ambiguities": [
    {
      "between": ["constraint", "assumption"],
      "occurrences": 7,
      "guidance_proposal": "Add to prompt: constraints are external/binding; assumptions are stated beliefs."
    }
  ]
}
```

## Directory layout

```
taxonomy/
├── iterations/
│   └── <source_type>/
│       └── iter-<NN>.json    # one record per sampled doc per iteration
├── findings.json             # consolidated findings across all source types
└── proposal.md               # human-reviewable proposal (diff vs starting taxonomy)
```

## Related decisions

- [D-17](../../decisions/0017-bounded-discovery-termination.md) termination rule.
- [D-18](../../decisions/0018-starting-taxonomy-as-floor.md) floor-not-reset.
- [D-19](../../decisions/0019-discovery-blocks-extract.md) blocks Extract.
- [D-20](../../decisions/0020-human-reviewed-lock.md) human-reviewed lock.
- [D-21](../../decisions/0021-taxonomy-debt-post-lock.md) post-lock debt handling.

## Failure modes

- **Sample-driven blindness.** A source type with few or quiet documents under-explores its taxonomy. Mitigation: starting taxonomy is a floor; removals require approval; consultant can see in the proposal which values had zero support and decide.
- **Discovery loop never terminates.** "Advances learning" is too lenient and every iteration finds *something*. Mitigation: hard iteration cap; "advance" requires *new* findings, not repeated ones.
- **Discovery overfits to LLM verbosity.** The discovery LLM is enthusiastic and proposes spurious new values. Mitigation: cross-source consolidation requires support from **at least two findings** for a proposed addition to reach "high confidence"; single-finding proposals are flagged "low confidence" in the proposal.
- **Taxonomy drift mid-assessment.** After lock, real extraction reveals genuine gaps. Mitigation: per [D-21], document as known limitation; finish the run; revisit only if severity warrants a re-lock. The cost of restarting is mostly cache-recoverable but prompt changes still invalidate extractor cache for affected sources.
- **Iteration cost.** Each iteration is a full-document LLM call. At ~15 iterations x 5 source types = ~75 calls on cheap model. Negligible. The expense is consultant review time, not tokens.
