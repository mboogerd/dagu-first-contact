# WP-07: Jira importer (`ops/import_jira.py`)

## Context
Implements spec §7.4.4. Fetches raw issue payloads per Jira project and writes them under `import/jira/[project-key]/issue-payloads/*.json`, plus a project manifest.

Prerequisite WPs: WP-01, WP-03.

## Scope
### In scope
- CLI: `python -m ops.import_jira [--only PROJECT ...] [--references PATH] [--since ISO8601]`.
- Read `jira.instance` and `jira.projects` from `references.yaml`.
- Authenticate via Basic auth (`JIRA_EMAIL` + `JIRA_API_TOKEN`) against `<instance>/rest/api/3/search` (or `/search/jql` if the legacy endpoint is gone — investigate at pickup time).
- For each project key:
  - Page through `project = <KEY>` (optionally `AND updated >= <since>` if `--since` is given), `maxResults=100`, expanding fields needed for normalization (description, comments, status, assignee, labels, issuetype, updated, created).
  - Write each issue verbatim as `import/jira/[PROJECT]/issue-payloads/<ISSUE-KEY>.json`.
  - Preserve any `nextPageToken` / pagination metadata in `import/jira/[PROJECT]/.pagination.json` for debugging.
  - Write `import/jira/[PROJECT]/.import-manifest.yaml`:
    ```yaml
    project: BILLING
    instance: https://company.atlassian.net
    issue_count: 487
    imported_at: 2026-05-14T12:00:00Z
    since: null
    ```
- Be polite: respect rate limits (sleep on HTTP 429 with `Retry-After`).
- `--dry-run` makes one call and reports the expected count without writing.

### Out of scope
- Markdown conversion (WP-08).
- Attachments / changelog history (note as open question).

## Inputs
- `references.yaml` (jira section).
- Env: `JIRA_EMAIL`, `JIRA_API_TOKEN`.

## Outputs / Deliverables
- `ops/import_jira.py`
- Schema/validator entry for the Jira manifest.
- `tests/test_import_jira.py` using `responses` (or `pytest-httpx`/`requests-mock`) to fake the Jira API.

## Implementation notes
- Language: **Python**, `requests` or `httpx`. Pick `httpx` if we want async later, otherwise `requests` is simpler.
- Do not embed credentials in the manifest.
- Use exponential backoff on 5xx; honour `Retry-After` on 429.
- File names must be safe (`ISSUE-KEY` is already safe; sanity-check anyway).

## Acceptance criteria
- [ ] Mocked Jira returns 3 paginated pages → importer writes the correct number of `*.json` files and a manifest with matching `issue_count`.
- [ ] Re-running without `--since` overwrites payloads idempotently; `--since` only fetches updated issues but does not delete previously-imported ones.
- [ ] Missing credentials → clear error and non-zero exit, no partial state.
- [ ] 429 with `Retry-After: 1` is handled (test by faking the response).
- [ ] `python -m ops.validate_artifacts validate all` accepts the project manifest.

## Verification commands
```bash
python -m pytest -q tests/test_import_jira.py
# Smoke (requires real creds):
# JIRA_EMAIL=... JIRA_API_TOKEN=... python -m ops.import_jira --only PLATFORM --dry-run
```

## Open questions
- Should we capture attachments? Default: no for MVP; record open questions in issue markdown later.
- New `/search/jql` endpoint vs legacy `/search`: confirm at pickup.
