import pickle
from pathlib import Path
from typing import Final, List, Tuple, Optional

from sentence_transformers import SentenceTransformer
from models import MedicalProtocol, HospitalRule

class RAGGuardrail:
    """Système de protection multicouche."""

    MODEL_NAME: Final[str] = 'paraphrase-multilingual-MiniLM-L12-v2'

    def __init__(self, model_path: Optional[Path] = None) -> None:
        """
         Initialise les couches de sécurité. 
        Arguments:
            model_path (str): Chemin vers le modèle entraîné (HistGradientBoosting.pkl).
        """
        if model_path is None:
            model_path = Path(__file__).parent.parent / "storage" / "guardrail.pkl"
        
        if not model_path.exists():
            print(f"❌ Erreur : Fichier introuvable ({model_path})")
            return

        with open(model_path, "rb") as f:
            self.classifier = pickle.load(f)

        self.encoder: Final[SentenceTransformer] = SentenceTransformer(self.MODEL_NAME)
        print("Guardrail Security Layer chargée (Modèle et Encoder).")


    def verify_input(self, query: str, threshold: float = 0.5) -> Tuple[bool, float, list]:
        """
        Vérifie les injections de prompt (Couche 1) via le modèle (guardrail.pkl).
        Arguments:
            query (str): La question posée par l'utilisateur.
            threshold (float): Seuil de probabilité pour bloquer la requête.
        Returns:
            Tuple[bool, float, list]: (is_safe, threat_probability, embedding)
        """
        # 1. On transforme la requête en embedding
        embedding = self.encoder.encode(query)
        # 2. On utilise le modèle .pkl pour prédire la probabilité de menace
        proba_threat = float(self.classifier.predict_proba(embedding.reshape(1, -1))[0][1])
        # Si la probabilité de menace est inférieur au seuil, c'est "Safe"
        is_safe: bool = proba_threat < threshold
        return is_safe, proba_threat, embedding
        # Ici simulation basée sur votre métrique 98.39% accuracy


    def verify_relevance(self, score: float, min_threshold: float = 0.4) -> bool:
        """
        Vérifie la pertinence de la recherche FAISS (Couche 2). Elle agit comme un filtre de qualité.
        Elle doit empêcher l'IA de répondre si elle n'est pas certaine  de ces sources.
        Utiliser le score de distance renvoyé par l'Engine. 
        Arguments:
            score (float): Score de similarité/pertinence.
            min_threshold (float): Seuil minimum requis.
        Returns:
            bool: True si la pertinence est suffisante, False sinon.
        """
        return score >= min_threshold

    def verify_logic(self, protocol: MedicalProtocol, rules: List[HospitalRule], wait_time: int = 0) -> bool: 
        """
        Vérifie la cohérence médicale et logistique (Couche 3). Elle ne vérifie plus si la question est malveillante ou pertinente. 
        Elle vérifie si les protocoles et règles récupérés sont logiquement compatibles.
        Arguments:
            protocol (MedicalProtocol): Le protocole médical récupéré.
            rules (List[HospitalRule]): Les règles logistiques associées.
        Returns:
            bool: True si la décision est logique, False s'il y a une contradiction.
        """
        # Exemple : Un patient ROUGE ne peut pas avoir une règle de retour à la maison
        # Règle de sécurité ROUGE
        if protocol.gravite == "ROUGE":
            # Bloquer si on essaie d'appliquer une règle de "Retour Maison" (GRIS/VERT)
            if any(r.id == "regle_retour_gris" for r in rules):
                return False
            
    # Vérification de l'exception VERT > 360min
        if protocol.gravite == "VERT" and wait_time > 360:
            # Le système doit confirmer qu'il applique la "regle_exception_360min"
            if not any("360min" in r.id for r in rules):
                return False
        return True