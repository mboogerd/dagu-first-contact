# Delta — ingest

## MODIFIED

### Behavior

The ingest stage no longer produces a single normalized doc per evidence record. Instead, for each evidence record, it runs **every projection registered for that record's source type** (as declared in `config/sources.yaml`), producing one or more files in `projections/<source>/<id>/<projection>/`.

The git adapter is no longer special. Its `summarize_repo` LLM call is now the implementation of the `git:repo_summary` projection. The adapter itself does only fetching of `evidence/git/<repo>/`; projection execution is shared infrastructure invoked the same way for every source.

### Adapter responsibilities

Adapters now have **one** responsibility: fetch raw evidence into `evidence/<source_type>/...` (idempotent — skip if unchanged).

Projection execution is no longer the adapter's job; it is driven by the ingest CLI iterating over `config/sources.yaml`'s declared projections.

### NormalizedDoc → projection output

The `NormalizedDoc` shape is unchanged in spirit but with frontmatter updates. See [design.md §Frontmatter schema](../../changes/001-projection-primitive/design.md#frontmatter-schema).

The frontmatter fields `normalization_kind` is **removed**. The fields `projection`, `projection_version`, `projection_params`, `parent_evidence`, `intent`, `default_status` are **added**.

### RepoSummary template

The RepoSummary template stays exactly as it is, but it is now described in the `git:repo_summary` projection contract at `spec/projections/git__repo_summary.md`, not in this ingest spec. The five fixed sections (Purpose, Public API Surface, Runtime Dependencies, Primary Domain Concepts, Notes) remain the contract.

### Directory layout

Replaces the entire `Directory layout` section.

```
evidence/
└── <source_type>/<source_id>/...    ← unchanged

projections/
└── <source_type>/<source_id>/
    └── <projection>/
        ├── <output>.md              ← projection output(s)
        ├── <output>.embedding*.json ← embedding sidecars (see embedding spec)
        └── <intermediates>          ← optional, projection-specific
```

## REMOVED

- The `Git adapter behavior` subsection enumerating the four steps (clone, build prompt, summarize_repo call, write to normalized/). Replaced by the `git:repo_summary` projection contract.
- All references to `normalization_kind: raw_text | curated_summary`. Distinction is now carried by which projection produced the file.
- The git-specific failure mode entries (`Repo-summary blind spots`, `Empty-section drift`) move to the `git:repo_summary` projection contract file.

## ADDED

### Source configuration (`config/sources.yaml`)

Each entry now lists which projections to run for that evidence. Example:

```yaml
sources:
  git:
    - id: payments-service
      url: git@github.com:client/payments-service.git
      projections:
        - name: git:repo_summary
          parameters: {}
  jira:
    - id: PROJ-123
      api_endpoint: ...
      projections:
        - name: jira:ticket_render
          parameters: {}
  rfp:
    - id: doc-12
      source_path: evidence_inputs/doc-12.pdf
      projections:
        - name: rfp:whole_document
          parameters: {}
        - name: rfp:section_split        # multi-projection example
          parameters:
            min_section_length: 200
```

Sources MAY declare multiple projections. The pipeline produces one output per projection.

### Failure modes (new)

- **Projection registry mismatch.** A `config/sources.yaml` declares a projection name not in the registry. Ingest fails fast with a clear error.
- **Per-projection failures stay isolated.** If `rfp:section_split` fails for one document, `rfp:whole_document` for the same document still completes. Failures are recorded per (evidence, projection) pair.

## Related

- [Change folder 001](../../changes/001-projection-primitive/proposal.md) — full design and rationale.
- [Projection contracts](../../projections/) — per-projection specifications.
