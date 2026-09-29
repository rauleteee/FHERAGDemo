"""
Shared formatting helpers for explaining what's happening at each
cryptographic step, in plain terms. Used by both `educational_demo.py`
(a scripted walkthrough) and `client/rag_client.py` (the real client,
when run with `verbose=True`) — so the explanations you see in a real
agent session are the exact same, tested code as the standalone demo.
"""
from __future__ import annotations


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    """One recorded moment in an encrypted operation — label, what
    kind of thing it shows, the value itself, plus optional extras
    (e.g. byte counts for a size comparison). Built once here, then
    rendered however the caller wants: printed to a terminal (see
    rag_client.py's verbose mode) or read straight from `call_log` by
    a UI, with no parsing of printed text needed."""
    label: str
    kind: str  # "vector" | "bytes" | "text" | "score" | "info"
    value: Any
    meta: dict = field(default_factory=dict)


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


def step(title: str) -> None:
    print()
    print(C.BOLD + f"  {title}" + C.RESET)


def vector_preview(vector: list[float], n: int = 5) -> str:
    shown = ", ".join(f"{v:+.4f}" for v in vector[:n])
    return f"[{shown}, ... ]  ({len(vector)} numbers total)"


def bytes_preview(data: bytes, n: int = 32) -> str:
    hex_str = data[:n].hex()
    return f"{hex_str}...  ({len(data):,} bytes total)"


def size_comparison(vector: list[float], ciphertext: bytes) -> str:
    plaintext_size = len(vector) * 8  # 8 bytes per float64
    expansion = len(ciphertext) / plaintext_size
    return (
        f"plaintext {plaintext_size:,} bytes -> ciphertext {len(ciphertext):,} bytes "
        f"(~{expansion:.0f}x larger)"
    )
