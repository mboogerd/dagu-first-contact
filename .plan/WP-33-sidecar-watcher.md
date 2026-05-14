# WP-33 (optional): Sidecar filesystem watcher

## Context
Implements spec §13. The watcher is explicitly optional and listed as a 3rd-iteration concern (spec §18.3). Include only after the core pipeline is working end-to-end (WP-32 green).

Prerequisite WPs: WP-31, WP-32.

## Scope
### In scope
- A standalone watcher process, **separate from Dagu**, that:
  - Reads a `watcher.yaml` config matching the spec §13.3 example.
  - Watches configured glob patterns; ignores `.git/**`, `.dagu/**`, `.state/**`, `logs/**`, `output/published/**`, `cache/**`, `**/*.tmp`.
  - Debounces bursts (default 5s).
  - Optionally hashes files (`hash_path` from WP-02) to suppress no-op events.
  - Triggers a configured Dagu workflow via Dagu's HTTP API (`dagu.base_url`, auth via `DAGU_API_TOKEN`).
  - Passes the changed file paths as a JSON payload.
  - Implements singleton/queue policies per watcher entry.
- Logging to stdout in a structured format (JSON lines preferred).
- A systemd unit / launchd plist / `Procfile` snippet so the watcher can run as a long-lived process.
- Tests: simulate file events with `watchdog`'s in-memory observer or by directly invoking handler functions; verify debounce, ignore rules, and webhook payload.

### Out of scope
- Replacing the manual workflow trigger from `main.yaml`.
- Distributed/multi-host watching.

## Inputs
- `watcher.yaml`.
- Filesystem events.
- Dagu API.

## Outputs / Deliverables
- `sidecar/` directory containing:
  - `sidecar/watcher.py` (or `cmd/watcher/main.go` if a different language is chosen — pick at pickup based on watcher library quality on macOS+Linux).
  - `sidecar/watcher.example.yaml`.
  - `sidecar/README.md` with run instructions.
- `schemas/watcher.schema.json` + validator plug-in (so the config can be linted).
- Tests.

## Implementation notes
- Language choice: Python (`watchdog`) is simplest given the rest of the codebase; Go (`fsnotify`) gives a single binary if that becomes valuable.
- The watcher must **never** watch its own log output or Dagu's run state — spec §13.4 calls this out explicitly.
- Loop prevention: use content hashes plus the singleton policy.

## Acceptance criteria
- [ ] Config validates against the schema.
- [ ] Touching `references.yaml` triggers `main.yaml` exactly once (verify by counting Dagu API calls), even when multiple write events fire within the debounce window.
- [ ] Editing a file inside `.dagu/` does not trigger anything.
- [ ] Killing the watcher and re-launching does not replay missed events (document this behaviour; not a bug — the workflow can also be triggered manually).

## Verification commands
```bash
python -m pytest -q tests/test_watcher.py
python sidecar/watcher.py --config sidecar/watcher.example.yaml --dry-run
```

## Open questions
- Should the watcher poll `.state/runs/` to suppress overlapping triggers? Default: yes, via the singleton policy on each watcher entry.
- Do we want a "manual replay" command for missed events? Defer.
