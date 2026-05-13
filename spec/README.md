# Assessment Pipeline Spec

A reproducible, LLM-augmented pipeline for ingesting heterogeneous evidence about an existing software system, organizing it into emergent clusters, and producing a prioritized human-review queue of requirements and conflicts.

**Purpose of the assessment** the pipeline supports: establish a baseline understanding of a client's AWS SaaS solution — its software landscape, requirements, and unimplemented change plan — sufficient to estimate the scale of an on-premise transformation and judge how much of that work can be accelerated with Gen-AI.

**Scope of this spec:** the pipeline that produces the artifacts the consultant will read. The consultant's report is out of scope.

**Phase:** v1 / proof-of-concept. Calibration, the full eval framework, and cluster archival are deliberately deferred (see [open-questions.md](open-questions.md)).

---

## Layout

```
spec/
├── README.md             # this file
├── principles.md         # the immutable constraints (constitution)
├── conventions.md        # spec authoring conventions (NEEDS CLARIFICATION, [P], change folders)
├── risks.md              # known risks accepted in v1
├── open-questions.md     # deferred items, with pointers
├── specs/                # per-component behavior contracts
│   ├── ingest/                  # Stage 1
│   ├── taxonomy/                # Stage 1.5
│   ├── embedding/               # cross-cutting (supports Stages 3, 4, 4.5)
│   ├── extract/                 # Stage 2
│   ├── cluster-structural/      # Stage 3a
│   ├── cluster-semantic/        # Stage 3b
│   ├── cluster-hierarchy/       # Stage 3c
│   ├── consolidate/             # Stage 4
│   ├── cross-cluster/           # Stage 4.5
│   ├── orchestration/           # Stage 5
│   └── report/                  # Stage 5.5
├── decisions/            # one file per design decision (ADR-style)
└── changes/              # per-change folders (the unit of iterative work)
    └── README.md         # change-folder template + workflow
```

## How to read

- **Start with `principles.md`** to understand the non-negotiable constraints.
- **Browse `specs/<component>/spec.md`** for the behavior contract of each component. Each component is tagged with its pipeline phase (Stage 1, 1.5, 2, etc.) when one applies.
- **Consult `decisions/<NNNN>-slug.md`** when you want to know *why* something is the way it is. Decisions retain their original numbers from the v0 monolith for traceability.
- **Add a change folder under `changes/<NNN>-slug/`** when starting new work. See [changes/README.md](changes/README.md) for the template.

## Phase 1 scope notes

The following are intentionally **not in this spec** and are deferred (with pointers in [open-questions.md](open-questions.md)):

- Calibration framework and tunable confidence weights — defaults are used; the consultant accepts noise in the review queue.
- Eval framework (eval cases, runs, judge prompts, the `eval` subcommand) — replaced by prompt versioning + manual spot-checks.
- Cluster archival semantics — assumed not needed in the assessment timeframe.

The following are **kept** even though they may seem premature, because the consultant wants to experiment with them in v1:

- Hierarchical super-clustering ([Stage 3c](specs/cluster-hierarchy/spec.md)).

## Conventions in this spec

- Components named with their pipeline phase in the heading where one applies.
- Cross-references use the original markers: `[D-N]` for design decisions, `[R-N]` for risks. The N matches the decision/risk filename's numeric prefix.
- New work is captured via change folders (see [changes/README.md](changes/README.md)), not by editing this spec directly. When a change lands, its delta is merged back into the relevant component spec.
- `[NEEDS CLARIFICATION: ...]` markers in proposals and design docs flag silent assumptions that must be resolved before implementation.

## Origin

This spec was extracted from a v0 monolith (`SPECIFICATION.md`, since removed) after a reviewer pass. The reorganization follows the OpenSpec model (stable specs + per-change deltas) with three discipline tactics borrowed from spec-kit (constitution principles, `[NEEDS CLARIFICATION]` markers, `[P]` parallel task markers).

History before the split lives in git.
