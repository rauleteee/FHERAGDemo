"""
Shared configuration for the FHE-RAG project.

IMPORTANT: This file is imported by BOTH client and server code.
It must never contain secrets, keys, or anything decryption-related.
"""

# CKKS context parameters.
# These were validated experimentally for 384-dim embeddings (all-MiniLM-L6-v2)
# with negligible numerical error (~1e-6) on dot product operations.
POLY_MODULUS_DEGREE = 8192
COEFF_MOD_BIT_SIZES = [60, 40, 40, 60]
GLOBAL_SCALE = 2 ** 40

# Embedding model. Local ONNX runtime, same approach as LLM Zoomcamp
# Module 2 (Vector Search) — no PyTorch, no CUDA, fully offline after
# a one-time download via `download_model.py`.
EMBEDDING_MODEL_PATH = "models/Xenova/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Network config for the demo (client and server as separate processes).
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8001
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 8000

# Storage
SERVER_DB_PATH = "server/ciphertext_store.db"
