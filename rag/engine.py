"""
Hospital RAG Engine
~~~~~~~~~~~~~~~~~~~
Moteur de requêtes principal avec orchestration de trois niveaux de sécurité.
Intègre la recherche basée sur FAISS avec une vérification de sécurité multicouche.

VERSION OPTIMISÉE :
- Ajout du MIN_CONFIDENCE_THRESHOLD (0.65) pour éviter le Semantic Drift.
- Modes simulation/chatbot et pré-calcul d'embeddings.
"""

import json
import time
import logging
from pathlib import Path
from typing import Final, Optional, Tuple

import numpy as np
import numpy.typing as npt
import faiss

from .models import RAGResponse, MedicalProtocol, HospitalRule
from .guardrails import RAGGuardrail, GuardrailConfig, GuardrailResult, BlockReason

logger = logging.getLogger("HospitalRAGEngine")

class HospitalRAGEngine:
    """
    Moteur RAG principal avec système de guardrail intégré.
    """

    # Seuil de confiance minimal pour valider une récupération sémantique
    # En dessous de 0.65, on considère que le RAG "hallucine" une proximité.
    MIN_CONFIDENCE_THRESHOLD: Final[float] = 0.65

    # Symptômes communs pour pré-calcul
    COMMON_SYMPTOMS = [
        "ROUGE douleur thoracique", "ROUGE détresse respiratoire",
        "ROUGE AVC suspecté", "ROUGE hémorragie importante",
        "ROUGE arrêt cardiaque", "JAUNE fracture du bras",
        "JAUNE forte fièvre", "JAUNE plaie profonde",
        "JAUNE douleur abdominale", "JAUNE traumatisme crânien",
        "VERT migraine", "VERT petite plaie",
        "VERT légère foulure", "VERT rhume",
        "VERT douleur chronique",
    ]

    def __init__(
        self, 
        base_path: Optional[Path] = None, 
        ml_threshold: float = 0.5, 
        min_relevance: float = 0.4,
        mode: str = "simulation"
    ) -> None:
        """
        Initialiser le moteur RAG.
        """
        self.base_path: Final[Path] = base_path or Path(__file__).parent.parent
        self.mode: Final[str] = mode
        
        # Configuration du guardrail
        config = GuardrailConfig(
            model_path=self.base_path / "storage" / "guardrail.pkl",
            ml_threshold=ml_threshold,
            min_relevance=min_relevance
        )
        
        use_ml = (mode == "chatbot")
        self.guardrail: Final[RAGGuardrail] = RAGGuardrail(config, use_ml=use_ml)
        
        self.protocols_data: list[MedicalProtocol] = []
        self.rules_data: list[HospitalRule] = []
        self.protocol_index: Optional[faiss.Index] = None
        
        self._load_protocols()
        self._load_rules()
        self._load_protocol_index()
        
        if mode == "simulation":
            self._precompute_common_embeddings()
        
        logger.info(f"Hospital RAG Engine initialisé en mode '{mode}' (Threshold: {self.MIN_CONFIDENCE_THRESHOLD})")

    def _load_protocols(self) -> None:
        proto_path = self.base_path / "data_regle" / "protocoles.json"
        if not proto_path.exists():
            logger.warning(f"Fichier introuvable : {proto_path}")
            return
        
        with open(proto_path, encoding="utf-8") as file:
            data = json.load(file)
            self.protocols_data = [MedicalProtocol(**item) for item in data]
        logger.info(f"{len(self.protocols_data)} protocoles chargés.")

    def _load_rules(self) -> None:
        rules_path = self.base_path / "data_regle" / "regles.json"
        if not rules_path.exists():
            logger.info(f"Fichier de règles introuvable : {rules_path}")
            return
        
        with open(rules_path, encoding="utf-8") as file:
            data = json.load(file)
            self.rules_data = [HospitalRule(**item) for item in data]
        logger.info(f"{len(self.rules_data)} règles chargées.")

    def _load_protocol_index(self) -> None:
        if self.mode == "simulation":
            fast_index_path = self.base_path / "data_regle" / "protocoles_fast.index"
            if fast_index_path.exists():
                self.protocol_index = faiss.read_index(str(fast_index_path))
                logger.info("Index FAISS RAPIDE chargé.")
                return
        
        index_path = self.base_path / "data_regle" / "protocoles.index"
        if not index_path.exists():
            logger.warning(f"Index FAISS non trouvé : {index_path}")
            return
        
        self.protocol_index = faiss.read_index(str(index_path))
        logger.info("Index FAISS standard chargé.")

    def _precompute_common_embeddings(self) -> None:
        self.guardrail.precompute_embeddings(self.COMMON_SYMPTOMS)

    def query(self, user_query: str, wait_time: int = 0) -> RAGResponse:
        """
        Exécution de la requête RAG avec seuil de confiance strict.
        """
        start_time = time.perf_counter()
        
        # 1. Validation de sécurité (Injections)
        pre_check = self._verify_input_safety(user_query)
        if not pre_check.is_safe:
            return self._build_error_response(
                message=pre_check.details,
                threat_score=pre_check.threat_score,
                relevance_score=0.0,
                start_time=start_time
            )
        
        if self.protocol_index is None:
            return self._build_error_response(
                message="Système de recherche indisponible (FAISS non chargé).",
                threat_score=0.0, relevance_score=0.0, start_time=start_time
            )
        
        # 2. Recherche sémantique FAISS
        query_embedding = pre_check.embedding
        protocol, similarity_score = self._search_protocol(query_embedding)
        
        # --- AJOUT DU SEUIL DE CONFIANCE (Lead Data Solution) ---
        if similarity_score < self.MIN_CONFIDENCE_THRESHOLD:
            logger.warning(f"Rejet par seuil de confiance : {similarity_score:.4f} < {self.MIN_CONFIDENCE_THRESHOLD}")
            return self._build_error_response(
                message="Aucun protocole médical fiable trouvé pour cette pathologie.",
                threat_score=0.0,
                relevance_score=similarity_score,
                start_time=start_time
            )
        # --------------------------------------------------------

        rules = self._search_rules(protocol.gravite)
        
        # 3. Validation Logic & Guardrail post-récupération
        post_check = self.guardrail.check(
            query=user_query,
            rag_score=similarity_score,
            protocol=protocol,
            rules=rules,
            wait_time=wait_time
        )
        
        if not post_check.is_safe:
            return self._build_error_response(
                message=f"Bloqué par {post_check.blocked_by.value}: {post_check.details}",
                threat_score=post_check.threat_score,
                relevance_score=similarity_score,
                start_time=start_time
            )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return RAGResponse(
            is_safe=True,
            threat_probability=post_check.threat_score,
            latency_ms=latency_ms,
            relevance_score=similarity_score,
            status="Protocole validé et extrait avec succès.",
            protocol=protocol,
            applicable_rules=rules
        )

    def _verify_input_safety(self, query: str) -> GuardrailResult:
        try:
            is_safe, threat_score, embedding, reason = self.guardrail.verify_input(query)
            if not is_safe:
                return GuardrailResult(is_safe=False, blocked_by=BlockReason.INJECTION,
                                     threat_score=threat_score, details=reason)
            return GuardrailResult(is_safe=True, threat_score=threat_score, details="Sûr", embedding=embedding)   
        except Exception as e:
            logger.error(f"Erreur verify_input: {e}")
            return GuardrailResult(is_safe=False, blocked_by=BlockReason.INJECTION,
                                 details="Erreur interne de sécurité.")

    def _search_protocol(self, query_embedding: npt.NDArray[np.float32]) -> Tuple[MedicalProtocol, float]:
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        embedding_normalized = query_embedding.astype('float32')
        faiss.normalize_L2(embedding_normalized)
        
        distances, indices = self.protocol_index.search(embedding_normalized, k=1)
        best_idx = int(indices[0][0])
        
        # Conversion distance L2 vers score de similarité [0, 1]
        raw_score = float(1.0 - (distances[0][0] / 2.0))
        similarity_score = max(0.0, min(1.0, raw_score))
        
        # Log de debug pour traquer le Semantic Drift
        logger.debug(f"FAISS Search | Index: {best_idx} | Score: {similarity_score:.4f}")

        if 0 <= best_idx < len(self.protocols_data):
            protocol = self.protocols_data[best_idx]
        else:
            protocol = MedicalProtocol(id="N/A", pathologie="Inconnu", symptomes=[], gravite="ROUGE", unite_cible="N/A")
        
        return protocol, similarity_score

    def _search_rules(self, gravite: str) -> list[HospitalRule]:
        return [rule for rule in self.rules_data if rule.gravite in (gravite, "TOUS")]

    def _build_error_response(self, message: str, threat_score: float, relevance_score: float, start_time: float) -> RAGResponse:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return RAGResponse(
            is_safe=False, threat_probability=threat_score,
            latency_ms=latency_ms, relevance_score=relevance_score,
            status=message, applicable_rules=[]
        )