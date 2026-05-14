Specification: Dagu-Based Project Intelligence Dataflow

1. Purpose

This specification describes a high-level dataflow for consolidating diverse project inputs into a structured, hierarchical understanding of an organization’s software systems, requirements, ownership boundaries, and future work.

The system is built on top of Dagu as the workflow execution layer. Dagu is responsible for orchestrating workflow phases, running scripts and agents, tracking execution, handling retries, supporting approvals, and exposing logs/history.

The core value of the system is not Dagu itself, but the artifact pipeline built around it:

raw sources
  -> imported local artifacts
  -> normalized markdown/JSON artifacts
  -> system/domain summaries
  -> requirement mappings/status/conflicts
  -> final consolidated report

The system should be local-first, inspectable, minimally magical, and file-oriented.

⸻

2. Scope

In scope

The initial system should support:

1. Importing heterogeneous inputs
2. Normalizing them into local, open, inspectable formats
3. Performing domain analysis over Git repositories
4. Building a hierarchy of systems, subdomains, and domains
5. Performing requirements analysis over normalized inputs
6. Mapping requirements to systems/domains
7. Identifying requirement status and conflicts
8. Producing a consolidated final report
9. Supporting human approval at key decision points
10. Optionally triggering workflows from filesystem changes using a sidecar watcher

Out of scope for the first version

The first version should not attempt to implement:

full incremental recomputation
fine-grained dependency tracking
distributed execution
custom Dagu plugins
a new workflow language
a UI beyond Dagu’s existing UI
automatic long-term memory
fully autonomous architectural decision-making

Delta propagation may be added later, but the initial design should be batch-oriented with clear phase boundaries.

⸻

3. Architectural Principles

3.1 Dagu as execution layer

Dagu should be used for:

workflow orchestration
phase dependencies
step dependencies
manual and scheduled execution
logs and run history
retries
human approvals
agent steps
script execution

Dagu should not contain complex domain logic. Its YAML files should remain relatively simple and high-level.

3.2 Filesystem as artifact store

The filesystem is the primary durable state.

Every major step should produce inspectable files, preferably:

Markdown for human-readable artifacts
YAML or JSON for structured artifacts
PlantUML/Mermaid for diagrams
frontmatter for metadata

3.3 Scripts for deterministic mechanics

Scripts should handle deterministic operations such as:

cloning repositories
exporting spreadsheets
copying PDFs
fetching Jira issues
converting Jira JSON to markdown
validating artifact schemas
materializing approved domain boundaries
finding affected summaries

3.4 Agents for interpretive work

Agents should be used for tasks that require judgment, synthesis, or projection:

summarizing repositories
identifying responsibilities
extracting interaction models
proposing domain boundaries
normalizing inconsistent spreadsheets
converting RFP PDFs to markdown
mapping requirements to systems
classifying requirement status
detecting conflicts
proposing resolutions
generating final reports

Where possible, agents should produce reviewable files rather than making irreversible changes directly.

3.5 Human approval for structural decisions

Human approval is required before:

accepting proposed domain boundaries
moving system summaries into subdomain folders
treating generated converters as trusted
accepting high-impact requirement conflict resolutions
publishing or exporting final conclusions

⸻

4. Project Folder Structure

A recommended project layout:

project/
  references.yaml
  dagu/
    main.yaml
    00-import.yaml
    10-normalize.yaml
    20-domain-analysis.yaml
    30-domain-boundaries.yaml
    40-requirements-analysis.yaml
    90-final-report.yaml
  ops/
    import_git.py
    import_spreadsheets.py
    import_pdfs.py
    import_jira.py
    jira_json_to_markdown.py
    run_spreadsheet_converters.py
    materialize_domain_boundaries.py
    validate_artifacts.py
  generated/
    spreadsheet-converters/
  sources/
    spreadsheets/
    rfp/
  import/
    git/
    spreadsheet/
    pdf/
    jira/
  normalized/
    requirements/
    rfp/
    jira/
  domain/
    systems/
    subdomains/
    interactions.md
    interactions.puml
    suggested-boundaries.md
    suggested-boundaries.yaml
    domain.md
  requirements/
    extracted/
    mapped/
    status/
    conflicts/
    resolutions/
    roadmap.md
    roadmap.yaml
  output/
    final-report.md
  .state/
    hashes/
    runs/

⸻

5. Source Reference Model

The system should use a references.yaml file to define external sources.

Example:

git:
  - name: customer-api
    url: git@github.com:org/customer-api.git
    branch: main
  - name: billing-service
    url: git@github.com:org/billing-service.git
    branch: main
spreadsheets:
  - name: legacy-requirements
    type: file
    path: sources/spreadsheets/legacy-requirements.xlsx
  - name: product-requirements
    type: google
    url: https://docs.google.com/spreadsheets/...
    export: xlsx
rfp:
  - name: main-rfp
    path: sources/rfp/main-rfp.pdf
jira:
  instance: https://company.atlassian.net
  projects:
    - PLATFORM
    - BILLING
    - CUSTOMER

The reference model should be interpreted by import scripts, not by Dagu directly.

⸻

6. Functional Dataflow

6.1 Main workflow

The top-level workflow should execute the main phases in order:

Import
  -> Normalize
  -> Domain Analysis
  -> Domain Boundary Approval
  -> Requirements Analysis
  -> Final Report

In Dagu terms:

name: main
type: graph
steps:
  - id: import
    run: 00-import.yaml
  - id: normalize
    run: 10-normalize.yaml
    depends: import
  - id: domain_analysis
    run: 20-domain-analysis.yaml
    depends: normalize
  - id: domain_boundaries
    run: 30-domain-boundaries.yaml
    depends: domain_analysis
  - id: requirements_analysis
    run: 40-requirements-analysis.yaml
    depends:
      - normalize
      - domain_boundaries
  - id: final_report
    run: 90-final-report.yaml
    depends: requirements_analysis

Exact Dagu syntax may differ depending on the installed version, but the logical structure should remain this shape.

⸻

7. Phase 1: Import

7.1 Purpose

The import phase creates local copies of all relevant external inputs.

It should avoid interpretation. Its job is to acquire data and store it locally in predictable locations.

7.2 Inputs

references.yaml
sources/spreadsheets/
sources/rfp/
credentials/environment variables

7.3 Outputs

import/git/[repo-name]/
import/spreadsheet/[spreadsheet-name].xlsx or .ods
import/pdf/[rfp-name].pdf
import/jira/[project-key]/*.json

7.4 Logical steps

7.4.1 Import Git repositories

Input:

references.yaml git section

Output:

import/git/[repo-name]/

Suggested implementation:

ops/import_git.py

Responsibilities:

clone missing repositories
pull/update existing repositories
checkout configured branch
record commit hash
write import manifest

Recommended manifest:

repo: billing-service
url: git@github.com:org/billing-service.git
branch: main
commit: abc123
imported_at: 2026-05-14T12:00:00Z

⸻

7.4.2 Import spreadsheets

Input:

references.yaml spreadsheets section
sources/spreadsheets/

Output:

import/spreadsheet/[name].xlsx
import/spreadsheet/[name].ods

Suggested implementation:

ops/import_spreadsheets.py

Responsibilities:

copy local spreadsheet files
export online spreadsheets to open or stable local formats
convert proprietary formats where useful
write import manifest

⸻

7.4.3 Import RFP PDFs

Input:

sources/rfp/
references.yaml rfp section

Output:

import/pdf/[rfp-name].pdf

Suggested implementation:

ops/import_pdfs.py

Responsibilities:

copy PDFs into import folder
normalize filenames
record source metadata
write import manifest

⸻

7.4.4 Import Jira issues

Input:

references.yaml jira section
Jira credentials

Output:

import/jira/[project-key]/issue-payloads/*.json

Suggested implementation:

ops/import_jira.py

Responsibilities:

fetch all relevant issues per configured project
store raw JSON response payloads
preserve pagination metadata if relevant
write project-level manifest

⸻

8. Phase 2: Normalization

8.1 Purpose

The normalization phase converts imported data into consistent, local, text-first artifacts.

This phase should preserve traceability to original sources.

8.2 Inputs

import/spreadsheet/
import/pdf/
import/jira/

8.3 Outputs

normalized/requirements/*.md
normalized/rfp/*.md
normalized/jira/[project-key]/*.md

8.4 Logical steps

8.4.1 Normalize spreadsheets into requirements markdown

Input:

import/spreadsheet/*

Output:

normalized/requirements/[spreadsheet-name].md

Suggested implementation:

agent generates converter scripts
human optionally approves converter scripts
ops/run_spreadsheet_converters.py executes converters

The agent should inspect each spreadsheet and produce converter code under:

generated/spreadsheet-converters/

The converter should produce markdown with a structure like:

---
source_type: spreadsheet
source_file: import/spreadsheet/legacy-requirements.xlsx
normalized_at: 2026-05-14T12:00:00Z
---
# Requirements from Legacy Requirements
## REQ-001: Customer lookup
Source row: Sheet1!A12:F12
Requirement text...

Dagu should include a human approval step before running newly generated converters.

⸻

8.4.2 Normalize RFP PDFs into markdown

Input:

import/pdf/*.pdf

Output:

normalized/rfp/[rfp-name].md

Suggested implementation:

agent-assisted PDF-to-markdown conversion

The output should preserve:

headings
page references
requirement-like statements
tables where practical
source traceability
uncertainty notes for extraction failures

Recommended output frontmatter:

source_type: rfp_pdf
source_file: import/pdf/main-rfp.pdf
normalized_at: 2026-05-14T12:00:00Z
extraction_confidence: medium

⸻

8.4.3 Normalize Jira JSON into markdown

Input:

import/jira/[project-key]/*.json

Output:

normalized/jira/[project-key]/[issue-key].md

Suggested implementation:

ops/jira_json_to_markdown.py

This should be deterministic code, not an agent.

Each issue markdown file should use frontmatter:

---
source_type: jira
project: BILLING
issue_key: BILLING-123
status: In Progress
issue_type: Story
assignee: Jane Doe
labels:
  - payments
  - migration
updated: 2026-05-10T09:30:00Z
---
# BILLING-123: Support invoice reconciliation
Description...
## Comments
...

⸻

9. Phase 3: Domain Analysis

9.1 Purpose

The domain analysis phase derives a structured understanding of the software estate from the imported Git repositories.

This is a projection phase, not a normalization phase.

9.2 Inputs

import/git/[repo-name]/
normalized/jira/
possibly normalized/requirements/

9.3 Outputs

domain/systems/[repo-name].md
domain/interactions.md
domain/interactions.puml
domain/suggested-boundaries.md
domain/suggested-boundaries.yaml

9.4 Logical steps

9.4.1 Summarize each repository as a system

Input:

import/git/[repo-name]/

Output:

domain/systems/[repo-name].md

Suggested implementation:

agent per repository
or script that calls agent per repository

Each system summary should include:

application purpose
main roles
responsibilities
owned data
external dependencies
internal modules
public APIs/events/interfaces
runtime/deployment hints
technology stack
known consumers/providers
ownership/team hints
evidence and confidence

Recommended structure:

---
artifact_type: system-summary
system: billing-service
source_repo: import/git/billing-service
commit: abc123
generated_at: 2026-05-14T12:00:00Z
confidence: medium
---
# billing-service
## Purpose
...
## Responsibilities
...
## Interactions
...
## Ownership Hints
...
## Evidence
...

Ownership hints may come from:

CODEOWNERS
README files
package metadata
Git contributor history
Jira ticket references
module naming
team mentions in docs
deployment files

⸻

9.4.2 Derive interaction model between systems

Input:

domain/systems/*.md
import/git/*

Output:

domain/interactions.md
domain/interactions.puml

Suggested implementation:

agent synthesis over system summaries
optional deterministic pre-indexing of code references

The interaction model should include:

nodes: systems
edges: dependencies/interactions
direction
interaction type
evidence
confidence
notes/open questions

Example edge model:

edges:
  - from: checkout-service
    to: billing-service
    type: synchronous-api
    evidence:
      - import/git/checkout-service/src/BillingClient.kt
    confidence: high

The markdown version should be readable for humans; the PlantUML version should be useful for diagrams.

⸻

9.4.3 Propose domain boundaries

Input:

domain/systems/*.md
domain/interactions.md
domain/interactions.puml

Output:

domain/suggested-boundaries.md
domain/suggested-boundaries.yaml

Suggested implementation:

agent proposes hierarchy

Boundary suggestions should consider:

high coupling
low coupling
functional cohesion
ownership/team hints
data ownership
runtime dependencies
business capabilities
known organizational structure

The YAML output should be machine-readable, for example:

subdomains:
  - name: billing
    systems:
      - billing-service
      - invoice-reconciliation
    rationale: >
      These systems share invoice lifecycle responsibilities and are commonly
      referenced by the same Jira project.
    confidence: high
  - name: customer
    systems:
      - customer-api
      - customer-profile-service
    rationale: >
      These systems own customer identity and profile concerns.
    confidence: medium

⸻

10. Phase 4: Domain Boundary Approval and Hierarchical Summarization

10.1 Purpose

This phase turns proposed domain boundaries into an approved hierarchy and derives recursive summaries.

10.2 Inputs

domain/suggested-boundaries.md
domain/suggested-boundaries.yaml
domain/systems/*.md

10.3 Outputs

domain/subdomains/[subdomain-name]/
domain/subdomains/[subdomain-name]/[subdomain-name].md
domain/domain.md

10.4 Logical steps

10.4.1 Human approval of proposed boundaries

Input:

domain/suggested-boundaries.md
domain/suggested-boundaries.yaml

Output:

approval decision
possibly edited domain/suggested-boundaries.yaml

Suggested implementation:

Dagu approval step

The user may edit the suggested boundaries before approval.

⸻

10.4.2 Materialize subdomain folders

Input:

approved domain/suggested-boundaries.yaml
domain/systems/*.md

Output:

domain/subdomains/[subdomain-name]/

Suggested implementation:

ops/materialize_domain_boundaries.py

This script should either:

move system summaries into subdomain folders
or copy/link them while preserving canonical system summaries

Recommended conservative approach:

keep domain/systems/*.md as canonical
create subdomain index files referencing systems
avoid destructive moves initially

Example:

domain/subdomains/billing/
  systems.yaml
  billing.md

Where systems.yaml contains:

systems:
  - ../../systems/billing-service.md
  - ../../systems/invoice-reconciliation.md

⸻

10.4.3 Summarize each subdomain

Input:

domain/subdomains/[subdomain-name]/systems.yaml
domain/systems/*.md
domain/interactions.md

Output:

domain/subdomains/[subdomain-name]/[subdomain-name].md

Suggested implementation:

agent per subdomain

Each subdomain summary should include:

subdomain purpose
included systems
roles and responsibilities
internal interactions
external interactions
ownership hints
requirement relevance if known
evidence gaps
confidence

⸻

10.4.4 Summarize the root domain

Input:

domain/subdomains/*/*.md
domain/interactions.md

Output:

domain/domain.md

Suggested implementation:

agent synthesis

The root domain summary should include:

overall system landscape
subdomain overview
cross-subdomain interactions
architectural risks
ownership patterns
open questions
confidence assessment

⸻

11. Phase 5: Requirements Analysis

11.1 Purpose

The requirements analysis phase transforms normalized requirements and background materials into an organized view of current and future work.

It should connect requirements to the derived domain model.

11.2 Inputs

normalized/requirements/*.md
normalized/rfp/*.md
normalized/jira/**/*.md
domain/domain.md
domain/subdomains/**/*.md
domain/systems/*.md
domain/interactions.md

11.3 Outputs

requirements/extracted/requirements.md
requirements/extracted/requirements.yaml
requirements/mapped/requirements-by-system.md
requirements/mapped/requirements-by-subdomain.md
requirements/mapped/requirements-mapping.yaml
requirements/status/status.md
requirements/status/status.yaml
requirements/conflicts/conflicts.md
requirements/conflicts/conflicts.yaml
requirements/resolutions/resolutions.md
requirements/resolutions/resolutions.yaml
requirements/roadmap.md
requirements/roadmap.yaml

11.4 Logical steps

11.4.1 Extract candidate requirements

Input:

normalized/requirements/
normalized/rfp/
normalized/jira/

Output:

requirements/extracted/requirements.md
requirements/extracted/requirements.yaml

Suggested implementation:

agent extraction

Each extracted requirement should include:

stable id
title
description
source references
requirement type
source quote or pointer
confidence

Example:

requirements:
  - id: REQ-0001
    title: Support invoice reconciliation
    type: functional
    description: >
      The system must support reconciliation between invoices and payments.
    sources:
      - normalized/rfp/main-rfp.md#page-12
      - normalized/jira/BILLING/BILLING-123.md
    confidence: high

⸻

11.4.2 Map requirements to systems and subdomains

Input:

requirements/extracted/requirements.yaml
domain/domain.md
domain/subdomains/**/*.md
domain/systems/*.md
domain/interactions.md

Output:

requirements/mapped/requirements-mapping.yaml
requirements/mapped/requirements-by-system.md
requirements/mapped/requirements-by-subdomain.md

Suggested implementation:

agent mapping

Each mapping should include:

requirement id
affected systems
affected subdomains
rationale
evidence
confidence
unknowns

⸻

11.4.3 Classify requirement status

Input:

requirements/mapped/requirements-mapping.yaml
import/git/
normalized/jira/
domain/systems/*.md

Output:

requirements/status/status.yaml
requirements/status/status.md

Suggested implementation:

agent classification with optional deterministic search/indexing support

Allowed statuses:

obsolete
implemented
partially implemented
future
uncertain

Each classification should include:

requirement id
status
rationale
evidence
confidence
affected systems/subdomains
recommended follow-up

⸻

11.4.4 Detect conflicting future requirements

Input:

requirements/status/status.yaml
requirements/mapped/requirements-mapping.yaml
requirements/extracted/requirements.yaml

Output:

requirements/conflicts/conflicts.yaml
requirements/conflicts/conflicts.md

Suggested implementation:

agent conflict analysis

Each conflict should include:

conflict id
involved requirements
affected systems/subdomains
nature of conflict
criticality
confidence
evidence
possible resolution directions

⸻

11.4.5 Propose conflict resolutions

Input:

requirements/conflicts/conflicts.yaml
domain/domain.md
domain/subdomains/**/*.md

Output:

requirements/resolutions/resolutions.yaml
requirements/resolutions/resolutions.md

Suggested implementation:

agent proposes resolutions
possibly followed by human approval

Each proposed resolution should include:

recommended resolution
alternatives
trade-offs
criticality
confidence
affected systems
affected teams/ownership hints
required human decisions

⸻

11.4.6 Organize future work

Input:

requirements/status/status.yaml
requirements/resolutions/resolutions.yaml
domain/domain.md
domain/subdomains/**/*.md

Output:

requirements/roadmap.md
requirements/roadmap.yaml

Suggested implementation:

agent synthesis

The future work hierarchy should be organized by:

domain
subdomain
system
theme/capability
dependency/order
confidence
criticality

⸻

12. Phase 6: Final Report

12.1 Purpose

The final report consolidates the generated domain and requirements artifacts into a coherent deliverable.

12.2 Inputs

domain/domain.md
domain/interactions.md
domain/interactions.puml
domain/subdomains/**/*.md
requirements/status/status.md
requirements/conflicts/conflicts.md
requirements/resolutions/resolutions.md
requirements/roadmap.md

12.3 Outputs

output/final-report.md

Optional future outputs:

output/final-report.pdf
output/final-report.docx
output/diagrams/
output/executive-summary.md

12.4 Logical steps

12.4.1 Generate final report

Suggested implementation:

agent synthesis

The report should include:

executive summary
source overview
current system/domain landscape
system interaction model
ownership/team hints
domain/subdomain hierarchy
requirements landscape
requirement status assessment
future work organization
requirement conflicts
proposed resolutions
critical risks
confidence and evidence gaps
recommended next steps

⸻

13. Sidecar Filesystem Trigger

13.1 Purpose

A small sidecar watcher may be added to trigger Dagu workflows from filesystem changes.

The sidecar should remain separate from Dagu initially.

13.2 Responsibilities

The sidecar should:

watch configured glob patterns
ignore configured paths
debounce bursts of filesystem events
optionally hash files to avoid false triggers
trigger configured Dagu workflows through API or webhook
pass changed file paths as JSON payload
support singleton/queue policies

13.3 Example configuration

dagu:
  base_url: http://localhost:8080
  auth:
    type: bearer
    token_env: DAGU_API_TOKEN
defaults:
  debounce: 5s
  singleton: true
  ignore:
    - ".git/**"
    - ".dagu/**"
    - "logs/**"
    - "cache/**"
    - "**/*.tmp"
watchers:
  - id: references-changed
    paths:
      - references.yaml
    workflow: main.yaml
    payload:
      reason: references-changed
  - id: system-summary-changed
    paths:
      - domain/systems/*.md
    workflow: 30-domain-boundaries.yaml
    payload:
      reason: system-summary-changed
  - id: subdomain-summary-changed
    paths:
      - domain/subdomains/*/*.md
    workflow: 90-final-report.yaml
    payload:
      reason: subdomain-summary-changed
  - id: requirements-changed
    paths:
      - requirements/**/*.md
      - requirements/**/*.yaml
    workflow: 90-final-report.yaml
    payload:
      reason: requirements-changed

13.4 Loop prevention

The watcher should prevent runaway loops by:

debouncing events
ignoring temporary files
checking content hashes
not watching Dagu logs/state
not watching workflow outputs that directly trigger themselves
using singleton workflow runs

The sidecar should be considered an optional convenience layer, not part of the core functional dataflow.

⸻

14. Artifact Metadata Requirements

Generated artifacts should include metadata where practical.

Recommended frontmatter:

artifact_type: system-summary
generated_by: 20-domain-analysis
generated_at: 2026-05-14T12:00:00Z
inputs:
  - import/git/billing-service
input_hashes:
  import/git/billing-service: abc123
confidence: medium

This supports:

traceability
debugging
future incremental recomputation
human review
auditability

⸻

15. Validation Requirements

The system should include validation scripts for important structured artifacts.

Examples:

validate references.yaml
validate suggested-boundaries.yaml
validate requirements.yaml
validate requirements-mapping.yaml
validate conflicts.yaml
validate roadmap.yaml
check broken file references
check missing summaries
check unknown system names

Suggested implementation:

ops/validate_artifacts.py

Validation should run before major synthesis steps and before final report generation.

⸻

16. Human Review Requirements

Human review should be supported at least for:

spreadsheet converter scripts before execution
domain boundary proposals before materialization
conflict resolution recommendations before final acceptance
final report before publication

Dagu approval steps should be used where possible.

⸻

17. Suggested Dagu Workflow Breakdown

Recommended workflow files:

dagu/main.yaml
  Orchestrates the full pipeline.
dagu/00-import.yaml
  Imports Git, spreadsheets, PDFs, and Jira.
dagu/10-normalize.yaml
  Converts imported data into markdown/YAML artifacts.
dagu/20-domain-analysis.yaml
  Produces system summaries, interaction model, and boundary proposals.
dagu/30-domain-boundaries.yaml
  Handles approval, materialization, subdomain summaries, and root domain summary.
dagu/40-requirements-analysis.yaml
  Extracts, maps, classifies, detects conflicts, proposes resolutions, and organizes roadmap.
dagu/90-final-report.yaml
  Produces final consolidated output.

⸻

18. Implementation Strategy

18.1 First MVP

The first version should use a limited dataset:

3 Git repositories
1 spreadsheet
1 RFP PDF
1 Jira project

MVP outputs:

normalized markdown files
system summaries
interaction model
suggested domain boundaries
domain summary
extracted requirements
requirement-to-system mapping
basic status classification
final report

18.2 Second iteration

Add:

all 35 repositories
multiple Jira projects
multiple spreadsheets
multiple RFPs
human approval around boundaries
conflict detection
future work roadmap

18.3 Third iteration

Add:

filesystem sidecar watcher
hash-based change detection
selective workflow triggering
artifact metadata validation
partial recomputation experiments

⸻

19. Key Non-Functional Requirements

The system should be:

local-first
file-oriented
inspectable
auditable
reproducible where practical
agent-assisted but not agent-dependent for mechanics
simple to run
safe by default
easy to pause and review
structured enough for future incremental recomputation

The system should avoid:

hidden state
opaque agent-only transformations
large monolithic prompts
destructive file movement without approval
unreviewed generated code execution
tight coupling to one LLM provider
premature custom orchestration logic

⸻

20. Summary

The proposed system is a Dagu-orchestrated artifact dataflow for turning heterogeneous project inputs into a structured understanding of:

what systems exist
what they do
how they interact
who appears to own them
what requirements exist
where those requirements belong
what their status is
where conflicts exist
what future work is implied

Dagu should provide the workflow execution layer. Scripts should provide deterministic mechanics. Agents should provide interpretive synthesis. The filesystem should provide the artifact store. Humans should approve structural decisions.

The resulting architecture is:

Dagu YAML
  = orchestration
ops scripts
  = deterministic mechanics
agents
  = interpretation and synthesis
filesystem
  = durable artifact graph
sidecar watcher
  = optional event-based triggering