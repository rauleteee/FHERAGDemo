"""
Tests for the core FHE client/server boundary.

These tests don't need the embedding model — they use synthetic
vectors, since the goal here is to validate the cryptography and the
security boundary, not the NLP quality.
"""
import random

import pytest

from client.crypto_client import FHEClient
from server.crypto_server import FHEServer


def _random_vector(dim: int = 384, seed: int = 0) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(dim)]


def test_homomorphic_dot_product_matches_plaintext():
    """The core correctness check: encrypted dot product should match
    the plaintext dot product within CKKS's expected numerical tolerance."""
    client = FHEClient()
    server = FHEServer(client.get_public_context_bytes())

    query = _random_vector(seed=1)
    doc = _random_vector(seed=2)

    enc_query = client.encrypt_vector(query)
    enc_doc = client.encrypt_vector(doc)

    enc_result = server.homomorphic_dot_product(enc_query, enc_doc)
    decrypted_score = client.decrypt_scalar(enc_result)

    plaintext_score = sum(a * b for a, b in zip(query, doc))

    assert abs(decrypted_score - plaintext_score) < 1e-3


def test_homomorphic_search_ranks_correctly():
    """End-to-end: encrypt a query + several documents, search
    homomorphically, decrypt, and check the ranking matches plaintext
    ranking exactly (scores can have tiny float error, order must not)."""
    client = FHEClient()
    server = FHEServer(client.get_public_context_bytes())

    query = _random_vector(seed=42)
    docs = [_random_vector(seed=i) for i in range(5)]

    enc_query = client.encrypt_vector(query)
    enc_docs = [client.encrypt_vector(doc) for doc in docs]

    enc_scores = server.homomorphic_search(enc_query, enc_docs)
    decrypted_scores = client.decrypt_scalars(enc_scores)

    plaintext_scores = [sum(a * b for a, b in zip(query, doc)) for doc in docs]

    encrypted_ranking = sorted(range(5), key=lambda i: -decrypted_scores[i])
    plaintext_ranking = sorted(range(5), key=lambda i: -plaintext_scores[i])

    assert encrypted_ranking == plaintext_ranking


def test_server_context_has_no_secret_key():
    """Security invariant check: the context the server holds must not
    be capable of decryption. This test would fail loudly if someone
    accidentally sent the secret key to the server."""
    client = FHEClient()
    server = FHEServer(client.get_public_context_bytes())

    query = _random_vector(seed=7)
    enc_query_bytes = client.encrypt_vector(query)
    enc_vector_on_server = server.load_vector(enc_query_bytes)

    with pytest.raises(Exception):
        # The server's context has no secret key, so attempting to
        # decrypt using it must fail.
        enc_vector_on_server.decrypt()
