import json
import time
from pathlib import Path  
from typing import Final, Optional, List, Tuple
import numpy as np
import faiss
from models import RAGResponse, MedicalProtocol, HospitalRule
from guardrails import RAGGuardrail

class HospitalRAGEngine:
    """Moteur RAG principal avec orchestration des 3 couches de Guardrails."""

    def __init__(self) -> None:
        """
        Initialise le moteur, les guardrails et les index FAISS.
        """

        self.base_path: Final[Path] = Path(__file__).parent.parent
        # 1. Initialisation des Guardrails
        self.guardrail: Final[RAGGuardrail] = RAGGuardrail(model_path=self.base_path / "storage" / "guardrail.pkl")
        self.last_latency: float = 0.0

        # 2. Définition des chemin Pathlib
        proto_json = self.base_path / "data_regle" / "protocoles.json"
        rules_json = self.base_path / "data_regle" / "regles.json"
        proto_index_file = self.base_path / "data_regle" / "protocoles.index"


        self.protocols_data: List[MedicalProtocol] = []
        self.rules_data: List[HospitalRule] = []

        if proto_json.exists():
            with open(proto_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.protocols_data = [MedicalProtocol(**item) for item in data]
            print(f" {len(self.protocols_data)} protocoles chargés.")
        else:
            print(f"Attention : Fichier introuvable {proto_json}")

        if rules_json.exists():
            with open(rules_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules_data = [HospitalRule(**item) for item in data]
            print(f" {len(self.rules_data)} règles chargées.")
        else:
            print(f"Attention : Fichier introuvable {rules_json}")
            
        # 3. Chargement de l'index des Protocoles
        if proto_index_file.exists(): 
            self.protocol_index: Optional[faiss.Index] = faiss.read_index(str(proto_index_file))
            print("✅ Index des Protocoles chargé.")
        else: 
            self.protocol_index = None
            print(f"⚠️ Attention : Fichier introuvable {proto_index_file}")

        print("Hospital RAG Engine initialisé.")


    def query(self, user_query: str) -> RAGResponse:
        """
        Exécute la requête à travers les filtres de sécurité. 
        
        Arguments:
            user_query (str): La question posée par l'utilisateur.
        Returns:
            RAGResponse: Réponse structurée avec statut de sécurité et latence.
        """
        start_time: Final[float] = time.perf_counter()
        
        # 1. Input Guardrail (Adversarial Protection)
        # On vérfie les injections AVANT de solliciter les index.
        is_safe, proba, query_embedding = self.guardrail.verify_input(user_query)
        if not is_safe:
            return self._build_error_response("Inéligible : Menace détectée", proba, start_time)
        
        # 2. Retrival (Recherche FAISS)
        if self.protocol_index is None:
            return self._build_error_response("Index non chargé", proba, start_time)
            
        protocol, score = self.faiss_search_protocol(query_embedding)

        # 3. Couche de Pertinence (Retrieval Guardrail)
        # On vérifie si le document trouvé est sémantiquement lié à la question.
        if not self.guardrail.verify_relevance(score):
            return self._build_error_response("Pertinence insuffisante", proba, start_time)
        
        # 4. Récupération des données via FAISS
        # On cherche le protocole médical le plus pertinent.
        rules = self.faiss_search_rules(protocol.gravite)

        # 5. Logic Guardrail (Consistency)
        # On s'assure que les règles sont cohérentes avec le protocole.
        if not self.guardrail.verify_logic(protocol, rules):
            return self._build_error_response("Incohérence logistique détectée", proba, start_time)
        
        # Calcul de la latence totale (Performance en ms)
        latency = (time.perf_counter() - start_time) * 1000
        
        return RAGResponse(
            is_safe=True,
            threat_probability=proba,
            latency_ms=latency,
            status="Success", 
            protocol=protocol, # Optionnel : retourner les données
            rules=rules
        )

    def faiss_search_protocol(self, query_embedding: np.ndarray) -> Tuple[MedicalProtocol, float]:
        """
        Recherche le protocole le plus proche via FAISS.
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # 2. NORMALISATION L2 (Crucial pour avoir un score entre 0 et 1)
        faiss.normalize_L2(query_embedding.astype('float32'))
        distances, indices = self.protocol_index.search(query_embedding.astype('float32'), 1)
        idx_trouve = int(indices[0][0])
        score = float(distances[0][0])

        # Mapping index FAISS -> Liste  Json 
        if 0 <= idx_trouve < len(self.protocols_data): 
            protocol = self.protocols_data[idx_trouve]
        else: 
            protocol = MedicalProtocol(id="N/A", pathologie="N/A", symptomes=[], gravite="ROUGE", unite_cible="N/A")
        # Miléna - A discuter
        return protocol, score
    
    def faiss_search_rules(self, gravite: str) -> List[HospitalRule]:
        """
        Récupère les règles logistiques associées à une gravité donnée.
        Arguments:
            gravite (str): La gravité du protocole médical.
        Returns:
            List[HospitalRule]: Liste des règles correspondantes.
        """
        return [r for r in self.rules_data if r.gravite == gravite or r.gravite == "TOUS"]


    def _build_error_response(self, msg: str, proba: float, start_time: float) -> RAGResponse:
        """
        Construit une réponse d'erreur structurée avec calcul de latence. 
        Arguments: 
            msg (str): Le message d'erreur si le guardrail a bloqué. 
            proba (float): La probabilité de menace détectée.
            start_time (float): Le timestamp de début pour le calcul de latence.
        """
        
        latency: float = (time.perf_counter() - start_time) * 1000
        return RAGResponse(
            is_safe=False, 
            threat_probability=proba, 
            latency_ms=latency, 
            status=msg
        )
