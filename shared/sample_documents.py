"""
Sample documents used by demo.py, client_cli.py, and educational_demo.py.

One shared list so there's a single place to edit, instead of four
copies drifting out of sync. Mixes genuine FHE/crypto explainers with
unrelated business/health documents on purpose — it makes the search
demo more convincing, since you can ask "what is homomorphic
encryption?" and watch it correctly rank the FHE documents above the
unrelated ones, on ciphertext, the whole point of this project.
"""

SAMPLE_DOCUMENTS = [
    # --- FHE / cryptography basics ---
    "Fully Homomorphic Encryption (FHE) allows computations to be performed "
    "directly on encrypted data, without ever needing to decrypt it first.",
    "The CKKS scheme is a type of FHE that supports approximate arithmetic "
    "on real numbers, which makes it well suited for machine learning and "
    "similarity search workloads like this one.",
    "Every FHE ciphertext carries a small amount of numerical noise, and "
    "that noise grows a little with each homomorphic operation performed on it.",
    "Bootstrapping is the technique used in some FHE schemes to refresh a "
    "ciphertext and reduce its accumulated noise, at a significant "
    "computational cost.",
    "Unlike traditional encryption, FHE lets a server compute on data it "
    "can never actually read — that's the core idea this whole project "
    "demonstrates.",
    "Post-quantum cryptography refers to algorithms believed to remain "
    "secure even against attacks from future quantum computers.",
    "A vector embedding is a list of numbers that represents the meaning "
    "of a piece of text, used to power semantic search.",
    "Embedding inversion attacks can reconstruct the original text from a "
    "stored vector, which is why encrypting embeddings before storage matters.",
    # --- unrelated documents, to prove the search actually discriminates ---
    "The patient was diagnosed with hypertension in early 2023.",
    "Quarterly revenue increased by 12 percent year over year.",
    "The new encryption protocol protects sensitive health records.",
    "Our marketing campaign reached 2 million users this quarter.",
    "The patient's blood pressure medication was adjusted at the last visit.",
]
