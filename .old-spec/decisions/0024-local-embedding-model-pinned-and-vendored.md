# [D-24] Local embedding model: nomic-embed-text-v1.5, pinned and vendored

**Status.** Accepted.

**Decision.** Embeddings use `nomic-ai/nomic-embed-text-v1.5-GGUF` at a specific HuggingFace commit SHA, Q8_0 quantization, served via LM Studio's `/v1/embeddings` endpoint. The GGUF file is **vendored** into `models/embeddings/` for true reproducibility. The expected SHA-256 of the file is recorded in `config/clustering.yaml` and verified on load.

**Rationale.** Local-first removes a network dependency, removes per-call cost, and works offline. Apache-2.0 license is clean for client work. 8k context handles long RFPs and transcripts without chunking. 768-dim vectors are cheap to store as sidecars. Vendoring the model means a `git clone` of the assessment is sufficient to reproduce.

**Alternatives considered.**
- OpenAI text-embedding-3-* — network dependency, per-call cost, vendor risk for client deliverables.
- MLX-native (Qwen3-Embedding-0.6B) — kept as a documented fallback.
- Local without vendoring — HF revisions can be force-pushed in rare cases; vendoring is the only true pin.

**Trade-offs accepted.** Adds ~300MB to the repo. Embedding quality is below frontier but plenty for cosine-similarity clustering at this scale. Quantization below Q8 is forbidden (Q4 degrades cosine quality meaningfully on embedding models).

**Related.** [embedding spec](../specs/embedding/spec.md); [R-12](../risks.md).
