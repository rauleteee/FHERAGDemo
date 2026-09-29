"""
Sample documents used by demo.py, client_cli.py, and educational_demo.py.

One shared list so there's a single place to edit, instead of four
copies drifting out of sync. Mixes genuine FHE/crypto explainers with
unrelated business/health documents on purpose — it makes the search
demo more convincing, since you can ask "¿qué es el cifrado
homomórfico?" and watch it correctly rank the FHE documents above the
unrelated ones, on ciphertext, the whole point of this project.

Documents are in Spanish so the whole demo (CLI + web) is Spanish and
queries match the documents' language, which keeps the embedding model's
semantic ranking sharp.
"""

SAMPLE_DOCUMENTS = [
    # --- Conceptos de FHE / criptografía ---
    "El Cifrado Totalmente Homomórfico (FHE) permite realizar cálculos "
    "directamente sobre datos cifrados, sin necesidad de descifrarlos primero.",
    "El esquema CKKS es un tipo de FHE que admite aritmética aproximada sobre "
    "números reales, lo que lo hace idóneo para aprendizaje automático y para "
    "búsquedas por similitud como esta.",
    "Cada ciphertext de FHE arrastra una pequeña cantidad de ruido numérico, y "
    "ese ruido crece un poco con cada operación homomórfica que se realiza sobre él.",
    "El bootstrapping es la técnica que usan algunos esquemas de FHE para "
    "refrescar un ciphertext y reducir su ruido acumulado, a un coste "
    "computacional elevado.",
    "A diferencia del cifrado tradicional, el FHE permite que un servidor "
    "compute sobre datos que nunca puede llegar a leer — esa es la idea central "
    "que demuestra todo este proyecto.",
    "La criptografía post-cuántica se refiere a algoritmos que se cree que "
    "seguirán siendo seguros incluso frente a ataques de futuros ordenadores "
    "cuánticos.",
    "Un embedding vectorial es una lista de números que representa el "
    "significado de un texto, y es lo que hace posible la búsqueda semántica.",
    "Los ataques de inversión de embeddings pueden reconstruir el texto "
    "original a partir de un vector almacenado, y por eso importa cifrar los "
    "embeddings antes de guardarlos.",
    # --- Documentos no relacionados, para probar que la búsqueda discrimina ---
    "Al paciente se le diagnosticó hipertensión a principios de 2023.",
    "Los ingresos trimestrales aumentaron un 12 por ciento interanual.",
    "El nuevo protocolo de cifrado protege registros médicos sensibles.",
    "Nuestra campaña de marketing alcanzó a 2 millones de usuarios este trimestre.",
    "La medicación para la tensión arterial del paciente se ajustó en la última visita.",
]
