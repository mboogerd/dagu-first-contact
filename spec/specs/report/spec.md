# Report (Stage 5.5)

Produce a consultant-facing "first read" markdown document that surfaces the highest-priority review items, the system landscape, the pipeline's health and freshness signals, the provenance of the run, and the **handover state**. The report is the artifact the consultant opens to decide where to focus next; the handover section is what the next consultant reads first.

**Phase.** Stage 5.5.

**Input → Output.** All pipeline outputs + `config/report.yaml` → `reports/<ISO_timestamp>.md`.

**When it runs.** On demand. Each invocation writes a new timestamped file; existing reports are never overwritten. Recommended cadence: after every `consolidate` run, plus an additional snapshot before major prompt or model changes.

---

## Approach

No LLM calls. The report is purely a rendering of existing artifacts; reproducibility comes from the frontmatter capturing every input version that contributed to the rendered content.

### Sections in v1

1. **Frontmatter** — input versions, counts, freshness warnings (see below).
2. **Handover** — state of play for the next consultant.
3. **Top-N** — the headline: highest-priority review queue items.
4. **Landscape** — the domain tree as a first-orientation view.
5. **Health** — freshness signals.
6. **Provenance** — counts and ingestion timestamps.

### Frontmatter assembly

```yaml
---
report_id: 2026-05-14T14-30-00Z
report_config_version: <config/report.yaml version>

inputs:
  taxonomy:
    version: <config/taxonomy.locked.yaml version>
    locked_at: <ISO>
    locked_from_starting: false
  clustering:
    version: <config/clustering.yaml version>
    embedding_model: nomic-embed-text-v1.5@<revision>
  consolidation:
    version: <config/consolidation.yaml version>
  cross_domain:
    findings_count: 12

freshness_warnings:
  - id: taxonomy_from_starting
    severity: warn
    message: |
      Locked taxonomy was created via the --from-starting shortcut.
      No discovery-based refinement has been applied.

counts:
  evidence:
    git_repos: 23
    jira_tickets: 1842
    rfp_docs: 7
    spreadsheets: 4
    transcripts: 11
  projections: 1887
  extracted:
    requirements: 4321
    interactions: 1209
    concepts: 412
  domains:
    total: 35
  consolidated_requirements: 2876
  review_queue_total: 2876
  review_queue_rendered: 50
---
```

### Handover section (new in v1)

A state-of-play summary aimed at the next consultant picking up the engagement. Deterministically rendered from existing artifacts. Contents:

- **Current state.** Date, what stages have run, what hasn't.
- **What the client has answered.** [Placeholder in v1; will be populated when the client-feedback loop lands.]
- **Open conflicts requiring attention.** Top-N items from the review queue, with a one-line "what the consultant should ask next" prompt (this is just the conflict's existing description; no synthesis).
- **Where attention should go first.** A short ordered list keyed off the freshness warnings + the top review queue items.
- **Practical resume commands.** The CLI sequence the next consultant should run to re-execute the pipeline incrementally from current state.
- **Known limitations and shortcuts taken.** A bullet list pulled from the frontmatter's freshness warnings, expanded to be self-contained without referring back to the spec.

The section is intended to be readable in isolation — a consultant who has not read the spec should be able to act on it.

### Top-N section

- Read `domains/root__review-queue.md` (the top-level review queue, sorted by `review_priority` descending).
- Take the top `top_queue.size` items (default 50 per `config/report.yaml`).
- For each item, render a structured markdown block containing:
  - Domain path and rank in queue.
  - Resolved statement, `type`, `status`, `change_plan_flag`.
  - All conflicts with kind, description, evidence excerpts.
  - Confidence breakdown: score + the five signals + which weights version produced it.
  - Criticality level + rationale (the LLM's one-sentence explanation).
  - Review priority components (base + boosts + total) so the consultant sees exactly why this item ranked here.
  - Source provenance: one line per contributing source with type, id, date, and excerpt.
  - Cross-domain references: wikilinks to cross-domain findings when applicable.
  - Tags as a compact filter line.

The block is self-contained — the consultant can act on a single item without opening other files.

### Landscape section

- Read `domains/_index.yaml` and per-domain summary files.
- Render a tree view of the domain hierarchy (depth-limited).
- For each domain, render: purpose (one line from summary), member count, top 3 concepts (from extracted concepts, deduplicated by alias), top 5 interactions (from extracted interactions, grouped by kind).
- This section is read-only orientation; no decisions hang on it.

### Health section

Compute freshness signals against `config/report.yaml: freshness`:

- **Taxonomy freshness.** If `taxonomy.locked.yaml` was locked via `--from-starting`, emit `taxonomy_from_starting` warning.
- **Model pin drift.** Detect when any model id in `models.yaml` has a newer pinnable version available (best-effort; provider-dependent; non-blocking).

Health stays as a separate section even though it only has two signals in v1. It is the natural home for future freshness signals (eval freshness, calibration staleness) when those features return, and keeping it separate avoids restructuring later.

Warnings are written to frontmatter (`freshness_warnings`) AND surfaced in this section in human-readable form.

### Provenance section

- Render counts from frontmatter as a clean table (per-source breakdown enabled by default per `config/report.yaml: provenance.per_source_breakdown`).
- Show ingestion timestamps for the most recently ingested artifact per source type.

## Configuration (`config/report.yaml`)

```yaml
version: "<semver or hash>"

top_queue:
  size: 50                            # number of review queue items rendered in full

freshness:
  taxonomy:
    warn_if_locked_with_from_starting: true

sections:
  - frontmatter
  - handover
  - top_queue
  - landscape
  - health
  - provenance

provenance:
  per_source_breakdown: true            # show counts by adapter as well as totals
```

## Write

- Filename: `reports/<ISO_timestamp>.md` where `<ISO_timestamp>` is the report's `report_id` (UTC, filename-safe form, e.g. `2026-05-14T14-30-00Z`).
- Reports are never overwritten.

## Related decisions

- [D-45](../../decisions/0045-deterministic-report-rendering.md) deterministic rendering; no LLM calls.
- [D-46](../../decisions/0046-reports-always-timestamped.md) always timestamped; never overwritten.
- [D-47](../../decisions/0047-freshness-signals-first-class.md) freshness signals are first-class.
- [D-48](../../decisions/0048-report-sections-independent-and-toggleable.md) independent toggleable sections.

## Related risks

- [R-24](../../risks.md) reports/ accumulates without bound.
- [R-25](../../risks.md) no narrative synthesis.

## Failure modes

- **Missing inputs.** If `domains/root__review-queue.md` doesn't exist (consolidate never ran), this stage fails fast with a clear error rather than producing a half-empty report.
- **Stale references in rendered items.** A report rendered now references content_hashes that may change later. Acceptable: the frontmatter pins every input version, so the consultant can reason about what was true at report time even if subsequent edits change things.
- **Disk accumulation from never-overwritten reports.** Over many iterations, `reports/` grows unboundedly. Mitigation: consultants are encouraged to gitignore `reports/` for routine runs, committing only snapshots that matter.
