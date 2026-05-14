# WP-01: Project skeleton & conventions

## Context
Establishes the on-disk layout, base configuration files, and the canonical `references.yaml` example that every later WP consumes. Implements spec §4 (Project Folder Structure) and §5 (Source Reference Model).

Prerequisite WPs: none.

## Scope
### In scope
- Create every directory listed in spec §4 with a `.gitkeep` (or a `README.md` when the folder warrants explanation).
- Add a top-level `README.md` describing how to set up and run the project (high level only; can reference WP-31/WP-32).
- Add a `.gitignore` that excludes `.state/`, `import/`, `generated/`, `output/`, large fixtures, virtualenvs, IDE noise, and Dagu runtime data.
- Provide a fully-worked example `references.yaml` matching the spec §5 schema (git, spreadsheets, rfp, jira). Use placeholder org names but ensure all three spreadsheet variants (`type: file`, `type: google`) appear and at least two git repos and one Jira project.
- Document the env-var contract (e.g. `JIRA_API_TOKEN`, `DAGU_API_TOKEN`) in `README.md` and a `.env.example`.

### Out of scope
- Any executable code in `ops/`.
- Dagu YAML files.
- Real credentials.

## Inputs
- `SPECIFICATION.md` §4, §5.

## Outputs / Deliverables
- Directory tree exactly matching spec §4 (under repo root).
- `references.yaml` (example/seed).
- `.gitignore`.
- `.env.example`.
- `README.md` (top-level, project orientation).
- `.plan/` itself is preserved (already exists).

## Implementation notes
- No language choice — this is pure scaffolding.
- Keep `references.yaml` valid YAML with comments explaining each section.
- For folders that hold generated/imported data only, prefer `.gitkeep`; for folders humans interact with (e.g. `sources/`), use a short `README.md`.

## Acceptance criteria
- [ ] `tree -L 2` (or equivalent) shows every directory from spec §4.
- [ ] `references.yaml` parses as YAML (`python -c "import yaml,sys;yaml.safe_load(open('references.yaml'))"`).
- [ ] `references.yaml` contains at least one entry under each of `git`, `spreadsheets`, `rfp`, and `jira.projects`.
- [ ] `.gitignore` excludes `.state/`, `import/`, `generated/spreadsheet-converters/` outputs (but tracks the folder), `output/`, `.venv/`, `__pycache__/`, `.DS_Store`, and `*.tmp`.
- [ ] `.env.example` lists every env var any later WP is expected to read (start with `DAGU_API_TOKEN`, `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GOOGLE_APPLICATION_CREDENTIALS`).
- [ ] (human review) Top-level `README.md` is coherent and links to `SPECIFICATION.md` and `.plan/README.md`.

## Verification commands
```bash
test -f references.yaml && python -c "import yaml;yaml.safe_load(open('references.yaml'))"
test -f .gitignore && test -f .env.example && test -f README.md
for d in dagu ops generated/spreadsheet-converters sources/spreadsheets sources/rfp \
         import/git import/spreadsheet import/pdf import/jira \
         normalized/requirements normalized/rfp normalized/jira \
         domain/systems domain/subdomains \
         requirements/extracted requirements/mapped requirements/status \
         requirements/conflicts requirements/resolutions \
         output .state/hashes .state/runs; do
  test -d "$d" || { echo "Missing: $d"; exit 1; }
done
```

## Open questions
- Should `sources/` be gitignored or tracked? Default: tracked-but-with-`README` only; large binary inputs gitignored.
