"""
High-level RAG client.

This is what a Streamlit app, CLI script, or agent should import. It
owns the secret key (via FHEClient) for the lifetime of the session
and talks to the remote Server over HTTP.

The server only ever sees what crosses the `requests` calls in this
file — read this file if you want to audit exactly what leaves the
client process. You should see hex-encoded ciphertexts only, never a
plaintext vector, plaintext document, or plaintext score being
*sent*. Plaintext only appears here on the *receiving* end, after a
local `decrypt_*` call.

Every index/search call records a structured list of `Step` objects
into `self.call_log` — this is what `streamlit_app.py` reads to
render the same walkthrough visually. Set verbose=True to ALSO print
them to the terminal (used by `run.sh learn`, `run.sh client`,
`run.sh agent`). Both come from the exact same recorded steps — there
is no separate "UI version" of this logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import requests

from client.crypto_client import FHEClient
from shared import explain
from shared.explain import Step
from shared.embeddings import embed_batch, embed_text


@dataclass
class SearchResult:
    doc_id: str
    text: str
    similarity_score: float


class FHERAGClient:
    """Client-side orchestration: embeds, encrypts, talks to the
    server, decrypts, and ranks. Holds the secret key and the
    plaintext document store (documents themselves are kept client-
    side; only their embeddings are sent, encrypted, to the server)."""

    def __init__(self, server_url: str, verbose: bool = False) -> None:
        self._server_url = server_url.rstrip("/")
        self._verbose = verbose
        self._crypto = FHEClient()
        self._doc_texts: dict[str, str] = {}
        # Append-only log of every operation's recorded steps — the UI
        # reads this. Each entry: {"operation": str, "steps": [Step]}.
        self.call_log: list[dict] = []
        self._register_context()

    def _print_steps(self, steps: list[Step]) -> None:
        """Print a recorded step list using the shared formatting —
        only called when verbose=True. The UI never calls this; it
        reads `self.call_log` directly instead."""
        for s in steps:
            if s.kind == "vector":
                print(f"  {explain.C.YELLOW}{explain.vector_preview(s.value)}{explain.C.RESET}")
            elif s.kind == "bytes":
                print(f"  {explain.C.DIM}{explain.bytes_preview(s.value)}{explain.C.RESET}")
                if "size_note" in s.meta:
                    print(f"  {s.meta['size_note']}")
            elif s.kind == "score":
                print(f"  {explain.C.GREEN}[{s.value:.4f}]{explain.C.RESET} {s.meta.get('text', '')}")
            elif s.kind == "warning":
                print(f"  {explain.C.RED}{s.value}{explain.C.RESET}")
            else:
                print(f"  {s.value}")

    def _register_context(self) -> None:
        public_context = self._crypto.get_public_context_bytes()
        steps = [
            Step("Public context (no secret key)", "bytes", public_context),
            Step(
                "warning",
                "warning",
                "The server cannot decrypt anything with this, even if it wanted to.",
            ),
        ]
        if self._verbose:
            explain.step("Registering with the server (public context only)")
            self._print_steps(steps)
        self.call_log.append({"operation": "register", "steps": steps})

        resp = requests.post(
            f"{self._server_url}/register-context",
            json={"public_context_hex": public_context.hex()},
            timeout=30,
        )
        resp.raise_for_status()

    def reset_index(self) -> None:
        """Clear the server's document store and re-register the
        context. The server's in-memory store doesn't deduplicate by
        doc_id, so call this before re-indexing (e.g. from a UI's
        "Index documents" button) to avoid duplicate entries piling up
        every time it's clicked."""
        self._doc_texts = {}
        self._register_context()

    def index_documents(self, documents: List[str]) -> None:
        """Embed and encrypt a batch of documents, send only the
        ciphertexts to the server. Plaintext documents are kept
        locally, keyed by doc_id, for retrieval after a search."""
        if self._verbose:
            explain.header(f"Indexing {len(documents)} document(s)")

        embeddings = embed_batch(documents)
        all_steps: list[Step] = []
        for i, (text, vector) in enumerate(zip(documents, embeddings)):
            doc_id = f"doc_{i}"
            self._doc_texts[doc_id] = text
            ciphertext = self._crypto.encrypt_vector(vector)

            doc_steps = [
                Step(f'Document {i + 1}: "{text}"', "text", text),
                Step("Plaintext embedding", "vector", vector),
                Step(
                    "Encrypted",
                    "bytes",
                    ciphertext,
                    meta={"size_note": explain.size_comparison(vector, ciphertext)},
                ),
            ]
            all_steps.extend(doc_steps)
            if self._verbose:
                explain.step(doc_steps[0].label)
                self._print_steps(doc_steps[1:])

            resp = requests.post(
                f"{self._server_url}/index",
                json={"doc_id": doc_id, "ciphertext_hex": ciphertext.hex()},
                timeout=30,
            )
            resp.raise_for_status()

        self.call_log.append({"operation": "index", "steps": all_steps})

        if self._verbose:
            print(
                f"\n{explain.C.GREEN}All {len(documents)} document(s) sent as ciphertext only. "
                f"The server has not\nseen a single plaintext word.{explain.C.RESET}"
            )

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        """Encrypt the query, send it to the server for homomorphic
        search, decrypt the returned scores locally, and return the
        top-k matching documents (retrieved from the local plaintext
        store, never from the server)."""
        if self._verbose:
            explain.header(f'Searching: "{query}"')

        steps: list[Step] = [Step(f'Question: "{query}"', "text", query)]

        query_vector = embed_text(query)
        query_ciphertext = self._crypto.encrypt_vector(query_vector)

        steps.append(Step("Your question, as numbers (plaintext)", "vector", query_vector))
        steps.append(
            Step(
                "Encrypted before sending",
                "bytes",
                query_ciphertext,
                meta={"size_note": explain.size_comparison(query_vector, query_ciphertext)},
            )
        )
        if self._verbose:
            self._print_steps(steps[1:])

        resp = requests.post(
            f"{self._server_url}/search",
            json={"query_ciphertext_hex": query_ciphertext.hex()},
            timeout=60,
        )
        resp.raise_for_status()
        encrypted_results = resp.json()

        if encrypted_results:
            sample = bytes.fromhex(encrypted_results[0]["encrypted_score_hex"])
            server_step = Step(
                f"Server computed {len(encrypted_results)} encrypted score(s)",
                "bytes",
                sample,
            )
            warning_step = Step(
                "warning",
                "warning",
                "The server has no idea if any of these scores are high or low. "
                "It's still just ciphertext to it.",
            )
            steps.extend([server_step, warning_step])
            if self._verbose:
                explain.step(server_step.label)
                self._print_steps([server_step, warning_step])

        scored: List[Tuple[str, float]] = []
        for item in encrypted_results:
            score_bytes = bytes.fromhex(item["encrypted_score_hex"])
            score = self._crypto.decrypt_scalar(score_bytes)
            scored.append((item["doc_id"], score))

        scored.sort(key=lambda pair: -pair[1])
        top = scored[:top_k]

        if self._verbose:
            explain.step("Decrypted locally with the secret key (never sent anywhere)")

        score_steps = []
        for doc_id, score in top:
            text = self._doc_texts.get(doc_id, "")
            s = Step(text, "score", score, meta={"text": text})
            score_steps.append(s)
        steps.extend(score_steps)
        if self._verbose:
            self._print_steps(score_steps)

        self.call_log.append({"operation": "search", "steps": steps})

        return [
            SearchResult(
                doc_id=doc_id,
                text=self._doc_texts.get(doc_id, ""),
                similarity_score=score,
            )
            for doc_id, score in top
        ]
