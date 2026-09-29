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
    print(C.BOLD + f"PASO {n} — {title}" + C.RESET)
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
    header("Demo educativa de FHE-RAG")
    print(
        "Recorre una búsqueda cifrada completa, paso a paso, mostrando los\n"
        "números reales, el ciphertext real y el resultado descifrado real\n"
        "en cada etapa."
    )

    document = (
        "El Cifrado Totalmente Homomórfico (FHE) permite realizar cálculos "
        "directamente sobre datos cifrados, sin necesidad de descifrarlos primero."
    )
    question = "¿Qué me permite hacer realmente el FHE?"

    # ------------------------------------------------------------------
    step(1, "Convertir tu documento en números (en claro, en el cliente)")
    print(f'Documento: "{document}"')
    pause()
    doc_vector = embed_text(document)
    print(f"\nEsto se convierte en una huella numérica de su significado:")
    print(C.YELLOW + "  " + vector_preview(doc_vector) + C.RESET)
    print(
        f"\n{C.RED}En un RAG normal, este mismo vector es lo que se almacena y se\n"
        f"busca. Cualquiera con acceso a él puede lanzar un ataque de inversión\n"
        f"para reconstruir tu frase original.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(2, "Cifrarlo antes de que salga de tu máquina")
    client = FHEClient()
    pause()
    doc_ciphertext = client.encrypt_vector(doc_vector)
    print("Con el cifrado homomórfico CKKS, este vector se convierte en:")
    print(C.DIM + "  " + bytes_preview(doc_ciphertext) + C.RESET)
    plaintext_size = len(doc_vector) * 8  # 8 bytes por float64
    expansion = len(doc_ciphertext) / plaintext_size
    print(
        f"\n{C.YELLOW}Compromiso honesto: el vector en claro ocupa solo {plaintext_size:,} bytes.\n"
        f"Cifrado ocupa {len(doc_ciphertext):,} bytes — unas {expansion:.0f}x más grande.\n"
        f"La privacidad no es gratis; este es su coste real.{C.RESET}"
    )
    print(
        f"\n{C.GREEN}Pero esto es lo que realmente se envía por la red. No hay forma de\n"
        f"recuperar los números originales sin la clave secreta — y la clave\n"
        f"secreta nunca sale de tu máquina.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(3, "El servidor recibe el ciphertext")
    public_context = client.get_public_context_bytes()
    server = FHEServer(public_context)
    pause()
    print("El servidor se inicializa solo con el contexto PÚBLICO:")
    print(C.DIM + "  " + bytes_preview(public_context, n=24) + C.RESET)
    print(
        f"\n{C.RED}Este contexto no contiene la clave secreta. El servidor,\n"
        f"literalmente, no puede descifrar nada, aunque quisiera.{C.RESET}"
    )
    print(
        f"{C.DIM}(Este contexto es grande porque incluye las claves de Galois\n"
        f"necesarias para los productos punto cifrados. Se envía una vez por\n"
        f"sesión, no una vez por documento o consulta.){C.RESET}"
    )
    server.load_vector(doc_ciphertext)  # valida que deserializa; sin descifrar
    print(f"\n{C.GREEN}El servidor guardó el ciphertext del documento. No tiene ni idea\nde lo que dice este documento.{C.RESET}")

    # ------------------------------------------------------------------
    step(4, "Haces una pregunta")
    print(f'Pregunta: "{question}"')
    pause()
    query_vector = embed_text(question)
    print(f"\n{C.YELLOW}  " + vector_preview(query_vector) + C.RESET)
    query_ciphertext = client.encrypt_vector(query_vector)
    print("\nCifrada, igual que antes:")
    print(C.DIM + "  " + bytes_preview(query_ciphertext) + C.RESET)

    # ------------------------------------------------------------------
    step(5, "El servidor calcula una puntuación de similitud — SOBRE el ciphertext")
    pause()
    print("El servidor ejecuta:  consulta_cifrada.dot(documento_cifrado)")
    print("Es matemática real sobre números cifrados. En este paso no se")
    print("descifra nada en ningún momento.")
    encrypted_score = server.homomorphic_dot_product(query_ciphertext, doc_ciphertext)
    print("\nLa propia salida del servidor SIGUE cifrada:")
    print(C.DIM + "  " + bytes_preview(encrypted_score, n=24) + C.RESET)
    print(
        f"\n{C.RED}El servidor no tiene ni idea de si esta puntuación es alta o baja,\n"
        f"relevante o irrelevante. Para él es solo más ruido.{C.RESET}"
    )

    # ------------------------------------------------------------------
    step(6, "Solo tú puedes descifrar el resultado")
    pause()
    decrypted_score = client.decrypt_scalar(encrypted_score)
    print(f"Descifrando localmente con la clave secreta (nunca se envía a ningún sitio)...")
    print(f"\n{C.GREEN}{C.BOLD}  Puntuación de similitud descifrada: {decrypted_score:.4f}{C.RESET}")

    plaintext_score = sum(a * b for a, b in zip(query_vector, doc_vector))
    error = abs(decrypted_score - plaintext_score)
    print(
        f"\nComprobación — ¿coincide con la misma operación hecha en claro?\n"
        f"  Producto punto en claro (solo de referencia): {plaintext_score:.4f}\n"
        f"  Diferencia: {error:.8f}  "
        f"{C.DIM}(ruido de aproximación de CKKS, minúsculo y esperado){C.RESET}"
    )

    # ------------------------------------------------------------------
    header("Resumen")
    print(
        f"El servidor guardó ciphertext, computó sobre ciphertext y devolvió\n"
        f"ciphertext. En ningún momento vio un solo número real de tu documento\n"
        f"ni de tu pregunta — y sin embargo la puntuación de similitud que\n"
        f"descifraste es correcta, con una diferencia de {error:.6f} respecto al\n"
        f"valor verdadero.\n"
    )


if __name__ == "__main__":
    main()
