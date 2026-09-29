"""
Web backend for the animated explainer.

This runs the REAL FHE pipeline and exposes its real intermediate values to
the frontend, so the animation shows genuine output — actual embeddings,
actual ciphertext and its real size, actual encrypted scores, and the actual
decrypted ranking — never mock data.

It reuses the project's own modules:
  - shared.embeddings      -> real 384-dim embeddings (ONNX, client-side)
  - client.crypto_client   -> FHEClient, the ONLY holder of the secret key
  - server.app             -> the real ciphertext-only server, run in a thread
                              and spoken to over HTTP, exactly like the CLI

Security invariant preserved: the server process only ever receives the
public context and ciphertext — never the secret key, never a decrypted value.
Decryption happens only here on the client side (FHEClient.decrypt_scalar).

Served by `./run.sh ui`.
"""
from __future__ import annotations

import threading
import time
import traceback
from pathlib import Path

import numpy as np
import requests
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from shared.config import EMBEDDING_DIM
from shared.sample_documents import SAMPLE_DOCUMENTS
from shared.embeddings import embed_batch, embed_text
from client.crypto_client import FHEClient
from server.app import app as fhe_server_app

WEB_DIR = Path(__file__).parent
FHE_PORT = 8011
FHE_URL = f"http://127.0.0.1:{FHE_PORT}"

# Category per sample document — metadata for the "map of meaning" viz only.
DOC_CATS = ["Cripto / FHE"] * 8 + ["Salud", "Negocio", "Salud", "Negocio", "Salud"]

state: dict = {"ready": False, "error": None, "crypto": None, "doc_vecs": None, "doc_cts": None}


def _start_fhe_server() -> None:
    uvicorn.run(fhe_server_app, host="127.0.0.1", port=FHE_PORT, log_level="warning")


def _bootstrap() -> None:
    """Start the real server, generate the key, encrypt + index the real
    document embeddings. Runs once in a background thread on startup."""
    try:
        threading.Thread(target=_start_fhe_server, daemon=True).start()
        for _ in range(80):
            try:
                if requests.get(f"{FHE_URL}/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.1)

        crypto = FHEClient()
        # Only the PUBLIC context crosses to the server — never the secret key.
        requests.post(
            f"{FHE_URL}/register-context",
            json={"public_context_hex": crypto.get_public_context_bytes().hex()},
            timeout=60,
        ).raise_for_status()

        vecs = embed_batch(list(SAMPLE_DOCUMENTS))
        cts = []
        for i, v in enumerate(vecs):
            ct = crypto.encrypt_vector(v)
            cts.append(ct)
            requests.post(
                f"{FHE_URL}/index",
                json={"doc_id": f"doc_{i}", "ciphertext_hex": ct.hex()},
                timeout=60,
            ).raise_for_status()

        state.update(ready=True, crypto=crypto,
                     doc_vecs=[[float(x) for x in v] for v in vecs], doc_cts=cts)
    except Exception:  # surface bootstrap failures to the frontend
        state["error"] = traceback.format_exc().splitlines()[-1]


app = FastAPI(title="FHE-RAG web explainer")


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=_bootstrap, daemon=True).start()


@app.get("/api/health")
def health() -> dict:
    return {"ready": state["ready"], "error": state["error"], "documents": len(SAMPLE_DOCUMENTS)}


def _vec(v, n: int = 6):
    return [round(float(x), 4) for x in v[:n]]


@app.get("/api/run")
def run(q: str = Query(..., min_length=1)):
    """Run the REAL encrypted search for query `q` and return every real
    intermediate value the animation renders."""
    if not state["ready"]:
        return JSONResponse({"ready": False, "error": state["error"]}, status_code=503)

    crypto: FHEClient = state["crypto"]
    qvec = embed_text(q)
    qct = crypto.encrypt_vector(qvec)

    # Real homomorphic search on the real server (ciphertext in, ciphertext out).
    enc_results = requests.post(
        f"{FHE_URL}/search", json={"query_ciphertext_hex": qct.hex()}, timeout=120
    ).json()

    docs = []
    for item in enc_results:
        i = int(item["doc_id"].split("_")[1])
        enc_bytes = bytes.fromhex(item["encrypted_score_hex"])
        score = crypto.decrypt_scalar(enc_bytes)  # only place decryption happens
        ct = state["doc_cts"][i]
        docs.append({
            "doc_id": item["doc_id"],
            "text": SAMPLE_DOCUMENTS[i],
            "cat": DOC_CATS[i],
            "vector_preview": _vec(state["doc_vecs"][i]),
            "cipher_hex": ct[:12].hex(),
            "cipher_bytes": len(ct),
            "enc_score_hex": enc_bytes[:12].hex(),
            "enc_score_bytes": len(enc_bytes),
            "score": round(float(score), 4),
        })

    ranking = sorted(docs, key=lambda d: -d["score"])
    plain_bytes = EMBEDDING_DIM * 8
    return {
        "ready": True,
        "query": q,
        "query_vector_preview": _vec(qvec),
        "query_cipher_hex": qct[:12].hex(),
        "query_cipher_bytes": len(qct),
        "plain_bytes": plain_bytes,
        "expansion": round(len(qct) / plain_bytes),
        "docs": docs,
        "ranking": ranking,
    }


@app.get("/api/space")
def space(q: str = Query(None)):
    """Real 2D PCA of the document embeddings (+ the query projected into the
    same space, with real dot-product similarities) for the vector viz."""
    if not state["ready"]:
        return JSONResponse({"ready": False, "error": state["error"]}, status_code=503)

    X = np.array(state["doc_vecs"])
    mean = X.mean(axis=0)
    Xc = X - mean
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    comp = Vt[:2]
    coords = Xc @ comp.T

    W, H, pad = 440, 320, 44
    xlo, xspan = float(coords[:, 0].min()), (float(coords[:, 0].max() - coords[:, 0].min()) or 1.0)
    ylo, yspan = float(coords[:, 1].min()), (float(coords[:, 1].max() - coords[:, 1].min()) or 1.0)
    sx = lambda v: round(pad + (v - xlo) / xspan * (W - 2 * pad), 1)
    sy = lambda v: round(pad + (v - ylo) / yspan * (H - 2 * pad), 1)

    docs = [{"text": SAMPLE_DOCUMENTS[i], "cat": DOC_CATS[i],
             "x": sx(coords[i, 0]), "y": sy(coords[i, 1])} for i in range(len(SAMPLE_DOCUMENTS))]
    out = {"ready": True, "docs": docs}

    if q:
        qv = np.array(embed_text(q))
        qc = (qv - mean) @ comp.T
        qx = min(W - pad, max(pad, pad + (qc[0] - xlo) / xspan * (W - 2 * pad)))
        qy = min(H - pad, max(pad, pad + (qc[1] - ylo) / yspan * (H - 2 * pad)))
        sims = (X @ qv).tolist()  # real dot products (normalized embeddings -> cosine)
        ranking = sorted(
            [{"text": SAMPLE_DOCUMENTS[i], "sim": round(float(sims[i]), 4)} for i in range(len(sims))],
            key=lambda d: -d["sim"],
        )
        out.update(query={"x": round(float(qx), 1), "y": round(float(qy), 1)},
                   sims=[round(float(s), 4) for s in sims], ranking=ranking)
    return out


# Static site last, so /api/* routes take precedence.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")
