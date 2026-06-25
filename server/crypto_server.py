"""
Server-side cryptography module.

SECURITY-CRITICAL FILE.

This module must NEVER decrypt anything, and must NEVER receive a
secret key. It operates exclusively on ciphertexts using the public
context received from the client.

If you find yourself wanting to add a `decrypt` method to this file,
stop — that almost certainly means the architecture is being broken.
"""
from __future__ import annotations

from typing import List

import tenseal as ts


class FHEServer:
    """
    Holds only the PUBLIC context (no secret key). Performs homomorphic
    computations on ciphertexts it receives from the client and returns
    encrypted results only.
    """

    def __init__(self, public_context_bytes: bytes) -> None:
        self._context = ts.context_from(public_context_bytes)

    def load_vector(self, ciphertext_bytes: bytes) -> ts.CKKSVector:
        """Deserialize a ciphertext using the public context."""
        return ts.ckks_vector_from(self._context, ciphertext_bytes)

    def homomorphic_dot_product(
        self, query_ct_bytes: bytes, stored_ct_bytes: bytes
    ) -> bytes:
        """
        Compute the encrypted dot product (similarity score) between
        an encrypted query and a single encrypted stored vector.

        Returns serialized ciphertext bytes — NEVER a plaintext float.
        """
        enc_query = self.load_vector(query_ct_bytes)
        enc_stored = self.load_vector(stored_ct_bytes)
        enc_result = enc_query.dot(enc_stored)
        return enc_result.serialize()

    def homomorphic_search(
        self, query_ct_bytes: bytes, stored_ct_bytes_list: List[bytes]
    ) -> List[bytes]:
        """
        Compute encrypted similarity scores between an encrypted query
        and every stored encrypted vector. Returns a list of serialized
        encrypted scores, in the same order as the input list.

        This is the brute-force search step. See AGENT.md / design doc
        for the known scaling limitation — there is no efficient
        encrypted ANN indexing used here.
        """
        return [
            self.homomorphic_dot_product(query_ct_bytes, stored_bytes)
            for stored_bytes in stored_ct_bytes_list
        ]
