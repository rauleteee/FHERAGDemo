"""
Embedding generation wrapper — local ONNX model.

Adapted from LLM Zoomcamp Module 2 (Vector Search). The `Embedder`
class below is a direct port of the course's `embedder.py`: it runs
all-MiniLM-L6-v2 through ONNX Runtime instead of sentence-transformers.

Why this matters for THIS project specifically: it needs no PyTorch
and no CUDA, and once the model is downloaded once (see
`download_model.py`), it runs fully offline — no network call to
Hugging Face at inference time. That's a nice property for a
privacy-focused project: even the embedding step has no external
dependency at runtime.

This module is used by the CLIENT ONLY, before encryption happens.
The server never imports this with real data.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from shared.config import EMBEDDING_MODEL_PATH


class Embedder:
    """Local ONNX embedding model. Ported from LLM Zoomcamp Module 2's
    `embedder.py` — same tokenizer + mean-pooling + normalization
    approach, just reused here as a library module."""

    def __init__(self, path: str = EMBEDDING_MODEL_PATH) -> None:
        model_dir = Path(path)
        if not (model_dir / "model.onnx").exists():
            raise FileNotFoundError(
                f"ONNX model not found at '{model_dir}'. "
                f"Run `python download_model.py` first (one-time, ~90MB)."
            )
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.session = ort.InferenceSession(
            str(model_dir / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        self.input_names = {inp.name for inp in self.session.get_inputs()}

    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        return self.encode_batch([text], normalize=normalize)[0]

    def encode_batch(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        self.tokenizer.enable_padding()
        encoded = self.tokenizer.encode_batch(texts)
        feed = {}
        if "input_ids" in self.input_names:
            feed["input_ids"] = np.array([e.ids for e in encoded], dtype=np.int64)
        if "attention_mask" in self.input_names:
            feed["attention_mask"] = np.array(
                [e.attention_mask for e in encoded], dtype=np.int64
            )
        if "token_type_ids" in self.input_names:
            feed["token_type_ids"] = np.array(
                [e.type_ids for e in encoded], dtype=np.int64
            )
        hidden = self.session.run(None, feed)[0]
        mask = feed["attention_mask"][..., None]
        pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1)
        if normalize:
            pooled = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)
        return pooled


@lru_cache(maxsize=1)
def _get_embedder() -> Embedder:
    """Load the model once and cache it for reuse."""
    return Embedder()


def embed_text(text: str) -> List[float]:
    """
    Generate a plaintext embedding for a single piece of text.

    Returns a plain Python list of floats (length == EMBEDDING_DIM).
    Caller is responsible for encrypting this before it leaves the
    client process.
    """
    vector = _get_embedder().encode(text)
    return vector.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate plaintext embeddings for a batch of texts."""
    vectors = _get_embedder().encode_batch(texts)
    return [v.tolist() for v in vectors]
