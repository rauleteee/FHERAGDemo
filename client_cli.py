"""
Interactive client REPL.

Connects to an already-running Server (start one separately with
`./run.sh server`), indexes a small set of sample documents, then
lets you type queries and see ranked, decrypted results.

This is the cleanest way to see Client and Server as genuinely
separate processes — unlike `demo.py`, which starts both itself for
convenience, this only ever talks to a server over HTTP, exactly the
way it would work on two different machines.

Usage:
    python client_cli.py [server_url]
"""
import sys

from client.rag_client import FHERAGClient
from shared.sample_documents import SAMPLE_DOCUMENTS


def main() -> None:
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
    print(f"Connecting to server at {server_url} ...")
    client = FHERAGClient(server_url)

    print(f"Indexing {len(SAMPLE_DOCUMENTS)} sample documents (encrypted client-side)...")
    client.index_documents(SAMPLE_DOCUMENTS)
    print("Ready. Type a question, or 'exit' to quit.\n")

    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if query.lower() in ("exit", "quit", ""):
            break

        results = client.search(query, top_k=3)
        print()
        for r in results:
            print(f"  [{r.similarity_score:.4f}] {r.text}")
        print()


if __name__ == "__main__":
    main()
