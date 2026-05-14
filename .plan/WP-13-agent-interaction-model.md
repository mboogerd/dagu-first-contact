# WP-13: Interaction model (agent)

## Context
Implements spec §9.4.2. Synthesises a cross-system interaction model from system summaries and (optionally) code-level evidence. Produces both a human-readable markdown view and a PlantUML diagram.

Prerequisite WPs: WP-12.

## Scope
### In scope
- Driver `ops/agent_interaction_model.py`:
  - Inputs: all `domain/systems/*.md`; optional `import/git/*` for evidence pointers.
  - Optional deterministic pre-indexing: grep for cross-system references (other system names, well-known endpoint paths, queue/topic names extracted from per-system summaries) and emit `.state/interactions/index.json`.
  - Call the agent (`prompts/interaction-model.md`) to produce:
    - `domain/interactions.md` — narrative + edge list with the structure required by spec §9.4.2:
      ```yaml
      edges:
        - from: checkout-service
          to: billing-service
          type: synchronous-api
          evidence: [import/git/checkout-service/src/BillingClient.kt]
          confidence: high
      ```
      (The YAML edge list can live inside a fenced ```` ```yaml ```` block in the markdown for readability.)
    - `domain/interactions.puml` — a PlantUML component diagram derived from the same edges (the driver may post-process the agent's YAML deterministically into PUML, which is preferable to asking the agent for both).
  - Frontmatter on `interactions.md`:
    ```yaml
    artifact_type: interactions
    generated_by: 20-domain-analysis
    generated_at: ...
    inputs: [domain/systems/...]
    input_hashes: { ... }
    confidence: low|medium|high
    ```
  - Recommendation: the agent returns *only* the edge YAML + narrative; the driver renders both `.md` and `.puml` from it. This avoids inconsistency between the two outputs.

### Out of scope
- Boundary proposal (WP-14).
- Runtime call-graph capture or static analysis tools (note as open question).

## Inputs
- `domain/systems/*.md`.
- `prompts/interaction-model.md`.

## Outputs / Deliverables
- `ops/agent_interaction_model.py`
- `prompts/interaction-model.md`
- `domain/interactions.md`, `domain/interactions.puml`
- `.state/interactions/index.json` (optional pre-index).
- Tests with a stubbed agent + a snapshot test for the PUML rendering.

## Implementation notes
- Language: **Python**.
- The deterministic edges → PUML step keeps the diagram consistent with the YAML.
- Validate the edge list against a small JSON Schema (`schemas/interactions-edges.schema.json`).

## Acceptance criteria
- [ ] With a stubbed agent returning a known edge list, both `interactions.md` and `interactions.puml` are produced.
- [ ] The PUML file is syntactically valid (run `plantuml -checkonly` if available; otherwise check it starts with `@startuml` and ends with `@enduml`).
- [ ] Edges referring to systems not present in `domain/systems/` produce a validator warning (via WP-03 cross-refs check).
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_interaction_model.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Should we attempt lightweight static analysis (e.g. find HTTP client invocations) per language? Default: no for MVP; the system summary already lists external dependencies.
