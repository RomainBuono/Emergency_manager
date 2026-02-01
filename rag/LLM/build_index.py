import json
import faiss
import numpy as np
from pathlib import Path
from typing import Final, List, Dict
from sentence_transformers import SentenceTransformer

def build_medical_index() -> None:
    """
    Transforme les protocoles JSON en index vectoriel FAISS avec Boosting de Précision.
    Utilise une structure de document enrichie pour améliorer la discrimination sémantique.
    """
    # 1. Configuration des constantes
    MODEL_NAME: Final[str] = 'paraphrase-multilingual-MiniLM-L12-v2'
    # Utilisation de chemins robustes
    BASE_PATH: Final[Path] = Path(__file__).resolve().parent.parent.parent / "data_regle"
    JSON_FILE: Final[Path] = BASE_PATH / "protocoles.json"
    INDEX_FILE: Final[Path] = BASE_PATH / "protocoles.index"

    if not BASE_PATH.exists():
        BASE_PATH.mkdir(parents=True, exist_ok=True)

    if not JSON_FILE.exists():
        print(f"Erreur : Le fichier {JSON_FILE} est introuvable.")
        return

    # 3. Chargement des données
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        protocols: List[Dict] = json.load(f)

    if not protocols:
        print("Le fichier JSON est vide.")
        return

    # 4. Préparation des textes avec Boosting de Précision
    # On structure le document pour que l'Embedding se focalise sur les bons clusters
    documents: List[str] = []
    for p in protocols:
        patho = p.get('pathologie', 'Inconnu')
        symptomes_list = p.get('symptomes', [])
        sympts_str = ", ".join(symptomes_list)
        
        # TECHNIQUE DE BOOSTING AVANCÉE :
        # - Répétition du titre (Boosting de classe)
        # - Séparateurs sémantiques (|) pour l'attention du Transformer
        # - Inclusion explicite des symptômes pour la granularité
        doc_text = (
            f"[PATHOLOGIE] {patho} | "
            f"[PATHOLOGIE] {patho} | "
            f"[SYMPTOMES] {sympts_str}"
        )
        documents.append(doc_text)

    # 5. Génération des Embeddings
    print(f"Encodage de {len(documents)} protocoles avec {MODEL_NAME}...")
    # On charge le modèle une seule fois ici
    encoder = SentenceTransformer(MODEL_NAME)
    
    # Encodage massif (convert_to_numpy=True assure la compatibilité FAISS)
    embeddings = encoder.encode(
        documents, 
        batch_size=32, 
        show_progress_bar=True, 
        convert_to_numpy=True
    ).astype('float32')

    # 6. Création de l'index FAISS
    # IndexFlatIP + normalize_L2 = Similarité Cosinus (Best practice pour NLP)
    dimension: int = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    # Normalisation L2 critique pour transformer le produit scalaire en Cosine Similarity
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    # 7. Sauvegarde sur disque
    faiss.write_index(index, str(INDEX_FILE))
    
    print(f"Index FAISS boosté créé avec succès !")
    print(f"rotocoles indexés : {index.ntotal}")
    print(f"Dimension vectorielle : {dimension}")
    print(f"Fichier : {INDEX_FILE}")

if __name__ == "__main__":
    build_medical_index()