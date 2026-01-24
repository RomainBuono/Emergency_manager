import json
import faiss
import numpy as np
from pathlib import Path
from typing import Final, List, Dict
from sentence_transformers import SentenceTransformer

def build_medical_index() -> None:
    """
    Transforme les protocoles JSON en index vectoriel FAISS.
    Prépare le système pour une recherche sémantique scalable.
    """
    # 1. Configuration des constantes
    MODEL_NAME: Final[str] = 'paraphrase-multilingual-MiniLM-L12-v2'
    BASE_PATH: Final[Path] = Path(__file__).parent.parent.parent / "data_regle"
    JSON_FILE: Final[Path] = BASE_PATH / "protocoles.json"
    INDEX_FILE: Final[Path] = BASE_PATH / "protocoles.index"
    # 2. Vérification de l'existence du dossier 
    if not BASE_PATH.exists():
        BASE_PATH.mkdir(parents=True, exist_ok=True)

    if not JSON_FILE.exists():
        print(f"Erreur : Le fichier {JSON_FILE} est introuvable.")
        return

    # 3. Chargement des données
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        protocols: List[Dict[str, str]] = json.load(f)

    if not protocols:
        print("Le fichier JSON est vide.")
        return

    # 4. Préparation des textes (Concaténation titre + contenu pour plus de contexte)
    # On utilise une compréhension de liste
    documents: List[str] = [
        f"{p.get('titre', '')} {p.get('description', '')} {p.get('actions', '')}" 
        for p in protocols
    ]

    # 5. Génération des Embeddings via SentenceTransformer
    print(f"Encodage de {len(documents)} protocoles...")
    encoder = SentenceTransformer(MODEL_NAME)
    # conversion en float32, format requis par FAISS
    embeddings = encoder.encode(documents).astype('float32')

    # 6. Création de l'index FAISS
    # On utilise l'index de Produit Scalaire (Inner Product) pour la similarité cosinus
    dimension: int = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    # Normalisation L2 : indispensable pour que le produit scalaire 
    # se comporte comme une similarité cosinus (entre 0 et 1)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    # 7. Sauvegarde sur disque
    faiss.write_index(index, str(INDEX_FILE))
    
    print("-" * 30)
    print(f"✅ Index FAISS créé avec succès !")
    print(f"📍 Emplacement : {INDEX_FILE}")
    print(f"📊 Nombre de vecteurs : {index.ntotal}")
    print(f"📐 Dimension : {dimension}")
    print("-" * 30)

if __name__ == "__main__":
    build_medical_index()