"""
Server FastAPI application.

This process NEVER holds a secret key. It receives a public context
once at startup/registration, then only ever stores and computes on
ciphertexts. Every endpoint here should be auditable by checking:
"does this function ever call .decrypt()?" — the answer must always
be no.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from server.crypto_server import FHEServer

app = FastAPI(title="FHE-RAG Server (ciphertext-only)")

# Global state for the demo. In a real deployment this would be
# per-session/per-tenant, not a single global — flagged here
# deliberately as a known simplification for the portfolio scope.
_server_state: dict = {"fhe_server": None, "documents": []}


class RegisterContextRequest(BaseModel):
    public_context_hex: str  # hex-encoded serialized public context


class IndexDocumentRequest(BaseModel):
    doc_id: str
    ciphertext_hex: str  # hex-encoded encrypted embedding


class SearchRequest(BaseModel):
    query_ciphertext_hex: str


class SearchResponse(BaseModel):
    doc_id: str
    encrypted_score_hex: str


@app.post("/register-context")
def register_context(req: RegisterContextRequest) -> dict:
    """
    Client calls this once at startup, sending ONLY the public context.
    No secret key ever arrives here — there is no field for it.
    """
    public_bytes = bytes.fromhex(req.public_context_hex)
    _server_state["fhe_server"] = FHEServer(public_bytes)
    _server_state["documents"] = []
    return {"status": "registered"}


@app.post("/index")
def index_document(req: IndexDocumentRequest) -> dict:
    """Store an encrypted document embedding. The server never sees
    the plaintext text or plaintext embedding for this document."""
    if _server_state["fhe_server"] is None:
        raise HTTPException(status_code=400, detail="Context not registered yet")

    ciphertext_bytes = bytes.fromhex(req.ciphertext_hex)
    # Validate it deserializes correctly under the public context
    # (this does NOT decrypt it — just confirms it's a valid ciphertext).
    _server_state["fhe_server"].load_vector(ciphertext_bytes)

    _server_state["documents"].append(
        {"doc_id": req.doc_id, "ciphertext": ciphertext_bytes}
    )
    return {"status": "indexed", "doc_id": req.doc_id}


@app.post("/search", response_model=List[SearchResponse])
def search(req: SearchRequest) -> List[SearchResponse]:
    """
    Homomorphic search across all indexed documents. Returns ENCRYPTED
    similarity scores only — the client decrypts these locally to
    determine ranking. This server never learns which document was the
    best match.
    """
    fhe_server: Optional[FHEServer] = _server_state["fhe_server"]
    if fhe_server is None:
        raise HTTPException(status_code=400, detail="Context not registered yet")

    query_ct = bytes.fromhex(req.query_ciphertext_hex)
    results = []
    for doc in _server_state["documents"]:
        enc_score = fhe_server.homomorphic_dot_product(query_ct, doc["ciphertext"])
        results.append(
            SearchResponse(
                doc_id=doc["doc_id"], encrypted_score_hex=enc_score.hex()
            )
        )
    return results


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "context_registered": _server_state["fhe_server"] is not None,
        "documents_indexed": len(_server_state["documents"]),
    }
