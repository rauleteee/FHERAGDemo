"""
One-command demo.

Run this with:  python demo.py

This starts the Server in a background thread, connects a Client to
it, indexes a handful of sample documents, runs a sample query, and
prints the decrypted results — all in one process, one command, for
a fast first look at the whole system working end to end.

This is NOT the "real" deployment topology (where Client and Server
would genuinely run on separate machines) — it's a convenience
wrapper for trying things out. See README.md "Manual setup" for the
two-terminal version that mirrors a real deployment.
"""
from __future__ import annotations

import threading
import time

import uvicorn

from server.app import app as server_app
from shared.sample_documents import SAMPLE_DOCUMENTS



SAMPLE_QUERY = "¿Qué me permite hacer realmente el FHE?"


def _run_server() -> None:
    uvicorn.run(server_app, host="127.0.0.1", port=8001, log_level="warning")


def main() -> None:
    print("Starting server in a background thread...")
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # give the server a moment to come up

    print("Loading embedding model and connecting client...")
    print("(first run downloads the model — this may take a minute)\n")
    from client.rag_client import FHERAGClient

    client = FHERAGClient("http://127.0.0.1:8001")

    print(f"Indexing {len(SAMPLE_DOCUMENTS)} documents (encrypted client-side):")
    for doc in SAMPLE_DOCUMENTS:
        print(f"  - {doc}")
    client.index_documents(SAMPLE_DOCUMENTS)

    print(f"\nQuery: {SAMPLE_QUERY}")
    print("Searching — the server computes on ciphertext only, it never sees")
    print("the plaintext documents, the plaintext query, or plaintext scores.\n")

    results = client.search(SAMPLE_QUERY, top_k=3)

    print("Top results (decrypted locally, client-side only):")
    for r in results:
        print(f"  [{r.similarity_score:.4f}] {r.text}")


if __name__ == "__main__":
    main()
