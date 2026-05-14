# Projection: `jira:bulk_download`

**Kind.** Deterministic.
**Default intent.** `mixed`
**Default status.** `unknown`

## Purpose

Produce one markdown file per Jira ticket in a project. Each file is a self-contained rendering of the ticket suitable for extraction and domain assignment. Replaces the v0 per-ticket adapter pattern with a bulk projection.

## Inputs

- `evidence/jira/<project>/` — the fetched Jira ticket data.

## Parameters

None. `parameters_schema: null`.

## Output contract

**Multiple output files:** `projections/jira/<project>/bulk_download/<ticket-id>.md`

One file per ticket. The markdown body renders: summary, description, comments (chronological), status, resolution, labels, components, fix versions. The frontmatter includes `extra.jira_status` (the ticket's workflow status) so the extractor can infer per-requirement status.

Because `intent: mixed`, the extractor reads each ticket's `extra.jira_status` to set the requirement's `status` accordingly (e.g., `Done` → `implemented`, `To Do` → `planned`).

## Cache key

```
hash(projection_name, projection_version, evidence_content_hash)
```

Deterministic; no model or prompt version in the key.

## Failure modes

- **Large comment threads.** Tickets with hundreds of comments may produce files that exceed downstream context windows. Mitigation: truncate comments beyond a configurable limit with a note.
- **Missing fields.** Tickets with empty descriptions or no comments produce sparse but valid output.
