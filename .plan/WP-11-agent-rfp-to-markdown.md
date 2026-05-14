# WP-11: RFP PDF → markdown (agent)

## Context
Implements spec §8.4.2. Converts each imported RFP PDF into a normalized markdown file with frontmatter, preserving headings, page references, tables (where practical), and uncertainty notes.

Prerequisite WPs: WP-02, WP-06.

## Scope
### In scope
- A driver `ops/agent_rfp_to_markdown.py`:
  - For each `import/pdf/<name>.pdf` without an up-to-date `normalized/rfp/<name>.md` (compare `input_hashes`):
    - Run a deterministic pre-extraction (text + page-anchored blocks) using `pypdf`, `pdfminer.six`, or `pymupdf` (pick at pickup; record choice). Produce an intermediate `.state/rfp/<name>.blocks.json` listing page-anchored text/table blocks. This is *not* the final artifact; it is reviewable and feeds the agent.
    - Call the agent (via `ops/_agent.py` from WP-10) with a prompt committed at `prompts/rfp-to-markdown.md` that includes the block JSON and instructs the agent to produce:
      - headings preserved
      - page references inline (e.g. `<sup>p. 12</sup>`)
      - requirement-like statements clearly marked
      - tables as markdown where extracted; otherwise an explicit `<!-- table extraction failed: page N -->` marker
      - uncertainty notes inline (`> [extraction-uncertain] ...`)
    - Write `normalized/rfp/<name>.md` via `write_artifact` with frontmatter:
      ```yaml
      artifact_type: rfp-normalized
      generated_by: 10-normalize
      generated_at: ...
      inputs: [import/pdf/<name>.pdf]
      input_hashes: { ... }
      source_type: rfp_pdf
      source_file: import/pdf/<name>.pdf
      extraction_confidence: low|medium|high   # agent's self-assessment
      ```
- Idempotent on unchanged inputs.

### Out of scope
- Requirement *extraction* (WP-18).
- OCR for image-only PDFs (note as open question — out for MVP).

## Inputs
- `import/pdf/*.pdf`.
- `prompts/rfp-to-markdown.md`.

## Outputs / Deliverables
- `ops/agent_rfp_to_markdown.py`
- `prompts/rfp-to-markdown.md`
- Intermediate block JSON under `.state/rfp/`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- The deterministic block extraction reduces token usage and gives a reviewable trail. Keep this step pure.
- Large PDFs may exceed agent context windows — chunk by page range, call the agent per chunk, then concatenate. Define the chunking strategy in the prompt template.

## Acceptance criteria
- [ ] With a stubbed agent returning a known markdown body, the driver produces a valid `normalized/rfp/<name>.md` whose frontmatter validates.
- [ ] An image-only PDF results in a `extraction_confidence: low` artifact with explicit uncertainty markers (or a clear failure with a non-zero exit code — decide and document).
- [ ] Re-running with no changes is a no-op.
- [ ] (human review) Prompt template is committed and reviewable.

## Verification commands
```bash
python -m pytest -q tests/test_agent_rfp_to_markdown.py
```

## Open questions
- Library choice for PDF extraction. Recommendation at pickup: `pymupdf` for layout + text, fallback `pdfminer.six`.
- Chunk size by tokens vs by pages. Default: by pages with a configurable max.
