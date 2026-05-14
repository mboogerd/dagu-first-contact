# WP-04: Git importer (`ops/import_git.py`)

## Context
Implements spec §7.4.1. Clones/updates every git source from `references.yaml` into `import/git/[repo-name]/` and writes an import manifest per repo.

Prerequisite WPs: WP-01, WP-03 (the validator must accept `references.yaml`).

## Scope
### In scope
- CLI: `python -m ops.import_git [--only NAME ...] [--references PATH]`.
- For each entry in `references.yaml` under `git:`:
  - If `import/git/[name]/` is absent: clone the configured `url`.
  - Else: fetch, then checkout the configured `branch` (or `ref` if added later), then fast-forward.
  - On any failure for an individual repo: log, continue with the rest, return non-zero overall.
  - After success, capture `git rev-parse HEAD` and write `import/git/[name]/.import-manifest.yaml` matching spec §7.4.1:
    ```yaml
    repo: billing-service
    url: git@github.com:org/billing-service.git
    branch: main
    commit: abc123
    imported_at: 2026-05-14T12:00:00Z
    ```
    The manifest is *not* an artifact with markdown frontmatter — it is a small YAML file. Still record its schema in `schemas/import-manifest.schema.json` and register a validator (WP-03 plug-in).
- Respect a `--dry-run` flag.
- Honour `GIT_SSH_COMMAND` from the environment; never embed credentials in code.

### Out of scope
- LFS, submodules (note as open question if any source repo needs them).
- Shallow vs full clones — default to full; allow `--depth N` for experimentation.
- Anything beyond the manifest in `import/git/[name]/` (no extra processing).

## Inputs
- `references.yaml` (git section).
- SSH/HTTPS credentials from the environment.

## Outputs / Deliverables
- `ops/import_git.py`
- `schemas/import-manifest.schema.json`
- `ops/validators/import_manifest.py` (plug-in to WP-03 validator)
- `tests/test_import_git.py` using a local bare repo as a fixture (so tests don't need the internet).
- README usage snippet.

## Implementation notes
- Language: **Python**, using either the `git` CLI via `subprocess` or `pygit2`/`GitPython`. Recommendation: `subprocess` against the system `git` to minimise deps and behave exactly like a developer would.
- Use a worktree-friendly approach: a fresh clone uses `git clone --branch <branch>`; updates use `git fetch && git checkout <branch> && git pull --ff-only`.
- Manifest write goes through `ops/_artifact.write_artifact` *only if* we treat the manifest as YAML-only (no markdown body). Otherwise write directly via `yaml.safe_dump` to an atomic temp file. Pick one and be consistent across all importers.

## Acceptance criteria
- [ ] With a `references.yaml` pointing to a local bare repo fixture, running the importer creates `import/git/<name>/` containing a checked-out working tree and `.import-manifest.yaml`.
- [ ] Re-running the importer leaves the working tree on the configured branch and updates `commit` and `imported_at` if the upstream advanced.
- [ ] If `references.yaml` is invalid, the importer refuses to run and prints the validator error.
- [ ] `--only billing-service` only touches that repo.
- [ ] `--dry-run` performs no filesystem changes.
- [ ] On a network failure for one repo, others still complete and the exit code is non-zero.
- [ ] `python -m ops.validate_artifacts validate all` recognises generated manifests as valid.

## Verification commands
```bash
python -m ops.validate_artifacts validate references
python -m ops.import_git --references tests/fixtures/references-local.yaml
python -m pytest -q tests/test_import_git.py
```

## Open questions
- Should we record dirty state or untracked files? Default: no, manifest reflects the commit only.
- Do we need to support tags or arbitrary refs in `references.yaml`? Default: branch only for the MVP; add `ref` later.
