# AGENT.md — Privacy-Preserving Vector Search for RAG using FHE

This file orients any Claude instance (or other coding agent) working on this codebase. Read this before making changes.

## Project summary

A privacy-preserving retrieval component for RAG pipelines. Document embeddings are encrypted client-side using Fully Homomorphic Encryption (CKKS scheme via TenSEAL/Microsoft SEAL). Similarity search runs homomorphically on a separate "server" process that never holds the secret key, so it never has access to plaintext vectors, plaintext similarity scores, or plaintext documents at any point.

This project is built directly on top of DataTalks.Club's LLM Zoomcamp, Module 2 (Vector Search), which supplied the core insight — semantic search is `X.dot(v)` — and the local ONNX `Embedder` class used in `shared/embeddings.py`. When editing that file, preserve the structural resemblance to the course original — that lineage is part of the project's story, not incidental.

Full design rationale lives in `docs/FHE_RAG_Design_Document.md` — read it before making architectural changes.

Deliberately kept simple: just the server/client FHE pipeline plus the educational walkthrough. No LLM agent, no web UI — those were tried and removed to keep the project focused on the cryptography itself.

## Core security invariant (do not break this)

The single most important rule in this codebase:

> **The Server process must never possess the secret key, and must never receive or produce a decrypted value.**

If you're asked to add a feature, always check: does this require the server to decrypt anything? If yes, stop and flag it — that would break the entire point of the project. All decryption happens exclusively in `client/`.

## Architecture

```
client/   -> Holds the secret key. Generates embeddings, encrypts them,
             encrypts queries, decrypts returned similarity scores,
             decides top-k, requests final documents.
server/   -> Holds only the public/eval context (no secret key).
             Stores ciphertexts. Computes homomorphic dot products.
             Returns encrypted scores only.
shared/   -> Common utilities (embedding model wrapper, serialization
             helpers, config, the shared sample document set) used by
             both sides — but NEVER the secret key.
```

Client and Server are separate FastAPI apps/processes, communicating over HTTP, to make the trust boundary real rather than simulated within one script.

## Tech stack (do not swap these without updating the design doc)

- **FHE**: TenSEAL (CKKS scheme). Chosen over Zama/TFHE because CKKS natively supports SIMD-packed real-valued vector dot products, and because our threat model needs ciphertext-times-ciphertext (both query and documents encrypted), whereas Concrete's tooling is built around ciphertext-times-cleartext (private inference against a public model). See design doc Section 2 for full reasoning.
- **Embeddings**: local ONNX model (all-MiniLM-L6-v2), ported from LLM Zoomcamp Module 2's `embedder.py`. No PyTorch, no CUDA, no network call at inference time once downloaded.
- **Backend**: Python 3.11+, FastAPI.
- **Storage**: SQLite, storing serialized ciphertexts only.
- **Explainability**: `client/rag_client.py`'s `FHERAGClient` takes a `verbose: bool` flag and always records a `Step` list (see `shared/explain.py`) into `self.call_log`, regardless of verbose. When `verbose=True`, the recorded steps are also printed to the terminal — this is what `run.sh learn`, `run.sh client`, and `run.sh demo` all show. There's exactly one implementation of "explain what's happening," not separate copies per script.
- **Demo**: `run.sh` with no arguments does a full zero-friction run — setup, model download, and `educational_demo.py` — automatically, in that order, skipping any step already done.

## Coding conventions

- Python, type-hinted, formatted with `black`.
- Every function that touches keys or ciphertexts must have a docstring stating explicitly whether it operates on plaintext, ciphertext, or both — this is a security-critical codebase, not a generic app.
- No secret key, decrypted vector, or decrypted score may ever cross from `client/` into `server/` code, not even in tests or fixtures. Test fixtures should use clearly fake/dummy data if a counter-example is needed for negative testing.
- Prefer explicit, verbose code over clever one-liners in cryptographic sections — readability matters more than brevity here, since this code will be read by recruiters and interviewers.
- Sample documents live in exactly one place: `shared/sample_documents.py`. Don't redefine the list locally in `demo.py`, `client_cli.py`, or anywhere else — import it.

## Known constraints to respect

- CKKS is approximate arithmetic. Expect small numerical error on decryption — never assume exact equality in tests; use tolerance-based comparisons.
- No efficient encrypted ANN/indexing exists yet. Search is homomorphic brute-force across all stored ciphertexts. Do not silently add a plaintext-side shortcut "to make it faster" — that would defeat the security model. If performance work is needed, it must stay within the homomorphic domain or be clearly flagged as a plaintext-side optimization that the design doc's limitations section must be updated to reflect.
- Keep dependencies minimal. This is a portfolio/demo project, not production infrastructure — avoid adding a full vector database, an LLM agent layer, a web UI, or heavy orchestration framework unless explicitly asked. These have been added and removed once already; don't reintroduce them speculatively.

## What "done" looks like for the MVP

1. Client can encrypt and send document embeddings to Server.
2. Client can encrypt and send a query embedding.
3. Server computes homomorphic dot products and returns encrypted scores only.
4. Client decrypts scores, ranks top-k, requests the corresponding documents.
5. `./run.sh` with no arguments works as a genuine zero-friction first run.

## Things NOT to do

- Do not attempt to encrypt LLM inference itself — out of scope (see design doc Section 6).
- Do not add Zama/TFHE as the primary scheme — it's a documented stretch goal for comparison benchmarking only, not a replacement.
- Do not fabricate benchmark numbers — always run and report actual measured latency.
- Do not re-add an LLM agent or a web UI without being explicitly asked — both existed in this project before and were deliberately removed to keep the scope focused on the FHE pipeline itself.
