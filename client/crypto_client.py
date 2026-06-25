"""
Client-side cryptography module.

SECURITY-CRITICAL FILE.

This is the ONLY module in the entire codebase that is allowed to:
  - generate the secret key
  - encrypt plaintext embeddings
  - decrypt anything

The server must NEVER import the secret-key-holding context produced
here. Only the public/eval context (see `get_public_context_bytes`)
is ever sent to the server.
"""
from __future__ import annotations

from typing import List

import tenseal as ts

from shared.config import COEFF_MOD_BIT_SIZES, GLOBAL_SCALE, POLY_MODULUS_DEGREE


class FHEClient:
    """
    Holds the secret key for the lifetime of the client process.

    One instance of this class should exist per client session.
    The `context` object internally contains the secret key — it must
    never be serialized with `save_secret_key=True` and sent anywhere.
    """

    def __init__(self) -> None:
        self._context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=POLY_MODULUS_DEGREE,
            coeff_mod_bit_sizes=COEFF_MOD_BIT_SIZES,
        )
        self._context.global_scale = GLOBAL_SCALE
        self._context.generate_galois_keys()

    def get_public_context_bytes(self) -> bytes:
        """
        Serialize ONLY the public parts of the context (public key,
        Galois keys, relinearization keys) for sending to the server.

        The secret key is explicitly excluded here. This is the single
        most important line in this file — review it carefully if you
        ever touch this method.
        """
        return self._context.serialize(
            save_secret_key=False,
            save_public_key=True,
            save_galois_keys=True,
            save_relin_keys=True,
        )

    def encrypt_vector(self, vector: List[float]) -> bytes:
        """Encrypt a plaintext embedding. Returns serialized ciphertext bytes."""
        encrypted = ts.ckks_vector(self._context, vector)
        return encrypted.serialize()

    def decrypt_scalar(self, ciphertext_bytes: bytes) -> float:
        """
        Decrypt a single encrypted scalar (e.g. a similarity score
        returned by the server). This is the ONLY place in the whole
        codebase where a similarity score becomes plaintext.
        """
        encrypted = ts.ckks_vector_from(self._context, ciphertext_bytes)
        return encrypted.decrypt()[0]

    def decrypt_scalars(self, ciphertext_bytes_list: List[bytes]) -> List[float]:
        """Decrypt a batch of encrypted scalars."""
        return [self.decrypt_scalar(ct) for ct in ciphertext_bytes_list]
