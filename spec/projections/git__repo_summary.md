# Projection: `git:repo_summary`

**Kind.** LLM skill.
**Default intent.** `implemented`
**Default status.** `implemented`
**Seed source.** Yes — outputs seed domains in [domain-structural](../specs/domain-structural/spec.md).

## Purpose

Produce a fixed-template curated summary of a git repo. The summary serves as the domain seed embedding and as the primary input for extraction. Raw repo content stays in `evidence/git/<repo>/` for extractors that need code-level detail.

## Inputs

- `evidence/git/<repo>/` — the cloned repository.
- Prompt input set: README files, top-level directory listing, recently modified files, package/build manifests, and any `*.md` docs at the repo root or in `docs/`.

## Parameters

None. `parameters_schema: null`.

## Output contract

**Single output file:** `projections/git/<repo>/repo_summary/<repo>.md`

The markdown body follows a fixed five-section template. The LLM has freedom within each section but MUST emit all sections:

```markdown
# <repo-name>

## Purpose
<1-3 sentences: what business or technical capability does this repo provide?>

## Public API Surface
<HTTP endpoints, event topics published/subscribed, CLI commands, library exports.
 List form. Empty section header allowed if genuinely none, with explicit "(none observed)".>

## Runtime Dependencies
<External services this repo depends on at runtime: databases, queues, third-party APIs,
 other repos in this assessment. List form with one line per dependency.>

## Primary Domain Concepts
<5-15 named concepts the repo organizes itself around. Mix of business and technical
 concepts is fine; this feeds concept extraction and domain labeling.>

## Notes
<Anything notable that doesn't fit above: deprecation status, ongoing migrations,
 known architectural patterns (microservice, monolith, batch job, etc.).>
```

## Cache key

```
hash(projection_name, projection_version, evidence_content_hash, model, prompt_version)
```

Where `evidence_content_hash` is over the prompt-input set (not the entire repo).

## Failure modes

- **Repo-summary blind spots.** The prompt input (README, top-level structure, manifests, `docs/`) may miss what makes a repo distinctive (e.g., logic buried in a non-obvious module). Mitigation: the `Notes` section explicitly invites the LLM to flag uncertainty.
- **Empty-section drift.** LLM omits sections it deems empty. Mitigation: schema validation requires all template sections present; "(none observed)" is the explicit empty value.
