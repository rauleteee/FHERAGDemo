"""
Educational demo.

Unlike `demo.py` (which just runs the pipeline and prints final
results) or `client_cli.py` (an interactive REPL), this script slows
everything down and shows you EVERY step, with real data: the actual
plaintext vector, the actual ciphertext bytes that cross the network,
the actual encrypted computation, and the actual decrypted result —
so you can see, concretely, what "the server never sees plaintext"
really means.

This runs Client and Server in a single process (no HTTP) so the
focus stays entirely on the cryptography, not the networking layer.
For the real two-process version, use `run.sh server` + `run.sh client`.

Usage:
    python educational_demo.py
"""
from __future__ import annotations

import time

from client.crypto_client import FHEClient
from server.crypto_server import FHEServer
from shared.embeddings import embed_text


class C:
    """Minimal ANSI colors — no external dependency needed."""
    HEADER = "\033[1;36m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


WIDTH = 74


def header(title: str) -> None:
    print()
    print(C.HEADER + "=" * WIDTH + C.RESET)
    print(C.HEADER + C.BOLD + f"  {title}" + C.RESET)
    print(C.HEADER + "=" * WIDTH + C.RESET)


def step(n: int, title: str) -> None:
    print()
    print(C.BOLD + f"STEP {n} — {title}" + C.RESET)
    print("-" * WIDTH)


def vector_preview(vector: list[float], n: int = 5) -> str:
    shown = ", ".join(f"{v:+.4f}" for v in vector[:n])
    return f"[{shown}, ... ]  ({len(vector)} numbers total)"


def bytes_preview(data: bytes, n: int = 32) -> str:
    hex_str = data[:n].hex()
    return f"{hex_str}...  ({len(data):,} bytes total)"


def pause(seconds: float = 0.6) -> None:
    """Small delay so the steps feel readable rather than instant."""
    time.sleep(seconds)


def main() -> None:
    header("FHE-RAG Educational Demo")
    print(
        "This walks through one full encrypted search, step by step,\n"
        "showing the real numbers, the real ciphertext, and the real\n"
        "decrypted result at each stage."
    )

    document = (
        "Fully Homomorphic Encryption (FHE) allows computations to be "
        "performed directly on encrypted data, without ever needing to "
        "decrypt it first."
    )
    question = "What does FHE actually let you do?"

    # ------------------------------------------------------------------
    step(1, "Turning your document into numbers (plaintext, client-side)")
    print(f'Document: "{document}"')
    pause()
    doc_vector = embed_text(document)
    print(f"\nThis becomes a numerical fingerprint of its meaning:")
    print(C.YELLOW + "  " + vector_preview(doc_vector) + C.RESET)
    print(
        f"\n{C.RED}In a normal RAG system, this exact vector is what gets stored\n"
        f"and searched. Anyone with access to it can run an inversion\n"
        f"attack to reconstruct your original sentence.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(2, "Encrypting it before it ever leaves your machine")
    client = FHEClient()
    pause()
    doc_ciphertext = client.encrypt_vector(doc_vector)
    print("Using CKKS homomorphic encryption, this vector becomes:")
    print(C.DIM + "  " + bytes_preview(doc_ciphertext) + C.RESET)
    plaintext_size = len(doc_vector) * 8  # 8 bytes per float64
    expansion = len(doc_ciphertext) / plaintext_size
    print(
        f"\n{C.YELLOW}Honest trade-off: the plaintext vector is only {plaintext_size:,} bytes.\n"
        f"Encrypted, it's {len(doc_ciphertext):,} bytes — about {expansion:.0f}x larger.\n"
        f"Privacy isn't free; this is the real cost of it.{C.RESET}"
    )
    print(
        f"\n{C.GREEN}But this is what actually gets sent over the network. There is\n"
        f"no way to recover the original numbers from this without the\n"
        f"secret key — and the secret key never leaves your machine.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(3, "The server receives the ciphertext")
    public_context = client.get_public_context_bytes()
    server = FHEServer(public_context)
    pause()
    print("The server is initialized with only the PUBLIC context:")
    print(C.DIM + "  " + bytes_preview(public_context, n=24) + C.RESET)
    print(
        f"\n{C.RED}This context has no secret key in it. The server literally\n"
        f"cannot decrypt anything, even if it wanted to.{C.RESET}"
    )
    print(
        f"{C.DIM}(This context is large because it includes the Galois keys\n"
        f"needed for encrypted dot products. It's sent once per session,\n"
        f"not once per document or query.){C.RESET}"
    )
    server.load_vector(doc_ciphertext)  # validates it deserializes; no decryption
    print(f"\n{C.GREEN}Server stored the document ciphertext. It has no idea what\nthis document says.{C.RESET}")

    # ------------------------------------------------------------------
    step(4, "You ask a question")
    print(f'Question: "{question}"')
    pause()
    query_vector = embed_text(question)
    print(f"\n{C.YELLOW}  " + vector_preview(query_vector) + C.RESET)
    query_ciphertext = client.encrypt_vector(query_vector)
    print("\nEncrypted, same as before:")
    print(C.DIM + "  " + bytes_preview(query_ciphertext) + C.RESET)

    # ------------------------------------------------------------------
    step(5, "The server computes a similarity score — ON the ciphertext")
    pause()
    print("Server runs:  encrypted_query.dot(encrypted_document)")
    print("This is real math happening on encrypted numbers. No decryption")
    print("happens anywhere in this step.")
    encrypted_score = server.homomorphic_dot_product(query_ciphertext, doc_ciphertext)
    print("\nThe server's own output is STILL encrypted:")
    print(C.DIM + "  " + bytes_preview(encrypted_score, n=24) + C.RESET)
    print(
        f"\n{C.RED}The server has no idea whether this score is high or low,\n"
        f"relevant or irrelevant. It is just more noise to it.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(6, "Only you can decrypt the result")
    pause()
    decrypted_score = client.decrypt_scalar(encrypted_score)
    print(f"Decrypting locally with the secret key (never sent anywhere)...")
    print(f"\n{C.GREEN}{C.BOLD}  Decrypted similarity score: {decrypted_score:.4f}{C.RESET}")

    plaintext_score = sum(a * b for a, b in zip(query_vector, doc_vector))
    error = abs(decrypted_score - plaintext_score)
    print(
        f"\nSanity check — does this match the same math done in plaintext?\n"
        f"  Plaintext dot product (reference only): {plaintext_score:.4f}\n"
        f"  Difference: {error:.8f}  "
        f"{C.DIM}(tiny CKKS approximation noise, expected){C.RESET}"
    )

    # ------------------------------------------------------------------
    header("Summary")
    print(
        f"The server stored ciphertext, computed on ciphertext, and\n"
        f"returned ciphertext. At no point did it see a single real\n"
        f"number from your document or your question — yet the\n"
        f"similarity score you decrypted is correct, "
        f"within {error:.6f} of the true value.\n"
    )


if __name__ == "__main__":
    main()
