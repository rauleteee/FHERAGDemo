# Privacy-Preserving Vector Search for RAG using FHE

Encrypted similarity search for RAG. Document embeddings are encrypted client-side with Fully Homomorphic Encryption (CKKS via TenSEAL/Microsoft SEAL). The server does the retrieval **directly on ciphertext** — it never holds the secret key and never sees a plaintext embedding, query, or score.

**Why:** vector embeddings are often assumed "safe" to store because they aren't human-readable. They aren't — [embedding inversion attacks](https://arxiv.org/abs/2004.00053) can reconstruct the original text from stored vectors. This closes that gap for the retrieval step of a RAG pipeline.

The core insight (from [DataTalks.Club's LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp), Module 2): semantic search is just a dot product, `scores = X.dot(v)`. So — what if that dot product ran on encrypted data? That's this project.

## How it works

Your agent searches your documents, but the whole retrieval happens on ciphertext: you hold the key and do all embedding, encryption, and decryption; the untrusted server only stores and computes over encrypted data.

**Normal search** — question and documents travel as plain text; the server sees everything.

![Normal RAG search: the server can read your question and every document](docs/architecture/latest/without-fhe.svg)

**Search with FHE** — you encrypt with your key first; the server searches the encrypted database without ever decrypting, and only you can read the result.

![RAG search with FHE: the server searches encrypted data and never reads anything](docs/architecture/latest/with-fhe.svg)

## Quickstart

```bash
./run.sh
```

No arguments = set up the virtualenv, download the embedding model, and run the educational demo. Re-run any time; setup steps are skipped once done. See every command with `./run.sh help`. If a port is stuck, `./run.sh stop` frees it (default 8001).

## Commands

| Command | What it does |
|---|---|
| `./run.sh` | Setup + model download + `learn` demo |
| `./run.sh learn` | One real encrypted search, printing every intermediate value (plaintext → ciphertext → encrypted score → decrypted result) |
| `./run.sh ui` | Animated web explainer on the real pipeline (auto-picks a free port) |
| `./run.sh demo` | One-command end-to-end run |
| `./run.sh server` / `client` | Run client and server as separate processes over HTTP |
| `./run.sh stop` | Kill anything left on the default port |

`./run.sh learn` is the best way to understand the project: it shows the actual bytes and numbers, so "the server never sees plaintext" is something you watch happen rather than a claim.

### The web explainer (`./run.sh ui`)

Built for talks and runs on the real ciphertext-only pipeline (not mock data): real embeddings, real ciphertext (~100× larger), real encrypted scores, real decrypted ranking.

![Embedding-search view: 13 real embeddings in 2D with a query point and the real dot-product ranking](images/image.png)

![Sin FHE / Con FHE comparison of the same real search, showing what the server can read](images/image1.png)

## Layout

```
client/   Holds the secret key. Embeds, encrypts, decrypts, ranks.
server/   Public context only. Stores ciphertexts, computes homomorphic dot products. Never decrypts.
shared/   Local ONNX embedding model, config, and the sample documents.
run.sh    Single entry point (setup, test, server, client, demo, learn, stop).
```

Sample set (`shared/sample_documents.py`): 13 documents — 8 on FHE/cryptography, 5 unrelated — so retrieval demonstrably ranks the relevant ones on top, on ciphertext.

Full design rationale (including why CKKS over TFHE/Zama): [`docs/FHE_RAG_Design_Document.md`](docs/FHE_RAG_Design_Document.md). Contributor guide: [`AGENT.md`](AGENT.md).

## Limitations

- Homomorphic brute-force against every stored vector — fine for hundreds-to-thousands of docs; efficient encrypted ANN is still an open problem.
- CKKS is approximate: expect ~1e-6 numerical error on decrypted scores.
- Ciphertext is ~100× larger than the plaintext vector; the one-time public context is ~35MB (Galois keys).
- Protects the retrieval step only, not LLM inference.

## License

MIT · Built on [DataTalks.Club's LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp), Module 2.
