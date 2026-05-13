# Ingest (Stage 1)

Pull raw evidence from sources; produce uniform normalized docs.

**Phase.** Stage 1.

**Input → Output.** `config/sources.yaml` → `evidence/` + `normalized/`.

---

## Behavior

Per-source-type adapters. Each adapter has two responsibilities:

1. Fetch raw evidence into `evidence/<source_type>/...` (idempotent — skip if unchanged).
2. Produce a `NormalizedDoc` (markdown + frontmatter) in `normalized/<source_type>/<source_id>.md`.

For most source types the normalized doc is a direct rendering of evidence (`normalization_kind: raw_text`). The **git adapter is special**: a repo is not a document, so the normalized doc is an **LLM-generated curated summary** following the `RepoSummary` template (below), with `normalization_kind: curated_summary`. The raw repo content stays in `evidence/git/<repo>/` for later use by extractors that need code-level detail. See [D-22], [D-23].

Adapters in scope for v1: `git`, `jira`, `spreadsheet`, `rfp`, `transcript`. Adding a new source type means writing one adapter; nothing downstream changes.

## Data shapes

### NormalizedDoc

Markdown file with YAML frontmatter:

```yaml
---
source_type: jira | git | rfp | spreadsheet | transcript
source_id: <stable id, e.g. PROJ-123, repo-name, doc-filename>
source_date: <ISO date if known>
ingested_at: <ISO timestamp>
content_hash: <sha256 of normalized markdown body>
original_path: evidence/jira/proj/PROJ-123.md
# Optional: present only for source_type=git
normalization_kind: curated_summary   # vs raw_text (the default for other sources)
extra:
  # source-specific metadata
  jira_status: done
  jira_reporter: alice@example.com
---

<markdown body>
```

`normalization_kind` distinguishes documents that are direct renderings of their evidence (`raw_text`, the default — Jira tickets, RFPs, transcripts, spreadsheets) from documents that are **curated summaries** of larger evidence (`curated_summary` — currently only git repos; see [D-22]). Downstream stages MAY use this flag when they need to know whether to consult the underlying `evidence/` for additional detail.

### RepoSummary (the body of normalized git docs)

When `source_type: git`, the normalized markdown body follows a fixed-section template. The template is the contract; the LLM that produces it has freedom within each section but MUST emit all sections.

```markdown
# <repo-name>

## Purpose
<1–3 sentences: what business or technical capability does this repo provide?>

## Public API Surface
<HTTP endpoints, event topics published/subscribed, CLI commands, library exports.
 List form. Empty section header allowed if genuinely none, with explicit "(none observed)".>

## Runtime Dependencies
<External services this repo depends on at runtime: databases, queues, third-party APIs,
 other repos in this assessment. List form with one line per dependency.>

## Primary Domain Concepts
<5–15 named concepts the repo organizes itself around. Mix of business and technical
 concepts is fine; this feeds domain extraction and cluster labeling.>

## Notes
<Anything notable that doesn't fit above: deprecation status, ongoing migrations,
 known architectural patterns (microservice, monolith, batch job, etc.).>
```

### Git adapter behavior

1. Clones the repo into `evidence/git/<repo>/`.
2. Constructs an LLM prompt from: README files, top-level directory listing, recently modified files, package/build manifests, and any `*.md` docs at the repo root or in `docs/`.
3. Calls the `summarize_repo` prompt (cached on `hash(prompt + repo_content_hash + model)`, where `repo_content_hash` is over the prompt-input set, not the entire repo).
4. Writes the result to `normalized/git/<repo>.md` with `normalization_kind: curated_summary`.

The raw repo content stays in `evidence/git/<repo>/` and is available to extractors that need code-level detail (see [D-23]).

## Directory layout (relative to the assessment root)

```
evidence/
└── <source_type>/<source_id>/...

normalized/
└── <source_type>/
    └── <source_id>.md                # the normalized document
```

(Embedding sidecars live alongside the normalized doc; see [embedding](../embedding/spec.md).)

## Related decisions

- [D-1](../../decisions/0001-filesystem-as-db.md) filesystem-as-DB.
- [D-2](../../decisions/0002-uniform-normalized-doc-shape.md) uniform doc shape.
- [D-3](../../decisions/0003-adapter-pattern-for-ingestion.md) adapter pattern.
- [D-22](../../decisions/0022-git-repo-curated-summary.md) git-repo curated summary.
- [D-23](../../decisions/0023-raw-evidence-accessible-to-extractors.md) raw evidence accessible to extractors.

## Failure modes

- Lossy normalization (e.g., spreadsheets with rich formatting flattened too aggressively).
- Stale `evidence/` if upstream changed but our cache says "fetched recently."
- Spreadsheets and RFPs that defy markdown conversion (large tables, embedded images).
- Jira tickets with thousands of comments blowing past context windows in later stages.
- **Repo-summary blind spots.** The git adapter's prompt input (README, top-level structure, manifests, `docs/`) may miss what makes a repo distinctive (e.g., logic buried in a non-obvious module). Mitigation: the `Notes` section of the template explicitly invites the LLM to flag uncertainty.
- **Empty-section drift.** LLM omits sections it deems empty. Mitigation: schema validation requires all template sections present; "(none observed)" is the explicit empty value.
