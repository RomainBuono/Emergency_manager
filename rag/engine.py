"""
Hospital RAG Engine
~~~~~~~~~~~~~~~~~~~
Moteur de requêtes principal avec orchestration de trois niveaux de sécurité.
Intègre la recherche basée sur FAISS avec une vérification de sécurité multicouche.

VERSION OPTIMISÉE avec modes simulation/chatbot et pré-calcul d'embeddings.
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
    
    NOUVEAUTÉS :
    - Mode 'simulation' : Rapide, sans ML, avec embeddings pré-calculés
    - Mode 'chatbot' : Sécurisé, avec ML complet
    - Support index FAISS approximatif pour recherches ultra-rapides

    Orchestre la récupération des protocoles médicaux avec une sécurité à trois niveaux :
        1. Détection d'injection (avant récupération)
        2. Vérification de la pertinence (après récupération)
        3. Validation logique (cohérence médicale)
    
    Examples:
        # Mode simulation (pour agent automatique)
        >>> engine = HospitalRAGEngine(mode="simulation")
        
        # Mode chatbot (pour interface utilisateur)
        >>> engine = HospitalRAGEngine(mode="chatbot")
    """

    # Symptômes communs pour pré-calcul (Solution 2)
    COMMON_SYMPTOMS = [
        "ROUGE douleur thoracique",
        "ROUGE détresse respiratoire",
        "ROUGE AVC suspecté",
        "ROUGE hémorragie importante",
        "ROUGE arrêt cardiaque",
        "JAUNE fracture du bras",
        "JAUNE forte fièvre",
        "JAUNE plaie profonde",
        "JAUNE douleur abdominale",
        "JAUNE traumatisme crânien",
        "VERT migraine",
        "VERT petite plaie",
        "VERT légère foulure",
        "VERT rhume",
        "VERT douleur chronique",
    ]

    def __init__(
        self, 
        base_path: Optional[Path] = None, 
        ml_threshold: float = 0.5, 
        min_relevance: float = 0.4,
        mode: str = "simulation"  # NOUVEAU : mode de fonctionnement
    ) -> None:
        """
        Initialiser le moteur RAG avec protection de type guardrail.
        
        Arguments :
            base_path : Répertoire racine des fichiers de données.
            ml_threshold : Seuil de détection des injections ML.
            min_relevance : Score de similarité RAG minimal requis.
            mode : 'simulation' (rapide) ou 'chatbot' (sécurisé)
        """
        self.base_path: Final[Path] = base_path or Path(__file__).parent.parent
        self.mode: Final[str] = mode  # ✅ Sauvegarder le mode
        
        # ✅ Configurer le guardrail selon le mode
        config = GuardrailConfig(
            model_path=self.base_path / "storage" / "guardrail.pkl",
            ml_threshold=ml_threshold,
            min_relevance=min_relevance
        )
        
        use_ml = (mode == "chatbot")  # ML seulement en mode chatbot
        self.guardrail: Final[RAGGuardrail] = RAGGuardrail(config, use_ml=use_ml)
        
        self.protocols_data: list[MedicalProtocol] = []
        self.rules_data: list[HospitalRule] = []
        self.protocol_index: Optional[faiss.Index] = None
        
        self._load_protocols()
        self._load_rules()
        self._load_protocol_index()
        
        # Pré-calculer les embeddings communs en mode simulation
        if mode == "simulation":
            self._precompute_common_embeddings()
        
        logger.info(f"Hospital RAG Engine initialisé en mode '{mode}'")

    def _load_protocols(self) -> None:
        """Load medical protocols from JSON file."""
        proto_path = self.base_path / "data_regle" / "protocoles.json"
        
        if not proto_path.exists():
            logger.warning(f"Avertissement : fichier de protocole introuvable à l'emplacement indiqué : {proto_path}")
            return
        
        with open(proto_path, encoding="utf-8") as file:
            data = json.load(file)
            self.protocols_data = [MedicalProtocol(**item) for item in data]
        
        logger.info(f"Chargement de {len(self.protocols_data)} medical protocols")

    def _load_rules(self) -> None:
        """Chargement des règles hospitalières depuis le fichier JSON."""
        rules_path = self.base_path / "data_regle" / "regles.json"
        
        if not rules_path.exists():
            logger.info(f"Avertissement : fichier de règles introuvable à l'emplacement indiqué : {rules_path}")
            return
        
        with open(rules_path, encoding="utf-8") as file:
            data = json.load(file)
            self.rules_data = [HospitalRule(**item) for item in data]
        
        logger.info(f"Chargement de {len(self.rules_data)} hospital rules")

    def _load_protocol_index(self) -> None:
        """
        Chargement de FAISS index pour les embeddings de protocoles.
        Utilise index approximatif (_fast) en mode simulation si disponible.
        """
        if self.mode == "simulation":
            # Essayer d'abord l'index rapide
            fast_index_path = self.base_path / "data_regle" / "protocoles_fast.index"
            if fast_index_path.exists():
                self.protocol_index = faiss.read_index(str(fast_index_path))
                logger.info("✅ FAISS index RAPIDE chargé (approximatif)")
                return
        
        # Fallback sur index standard
        index_path = self.base_path / "data_regle" / "protocoles.index"
        
        if not index_path.exists():
            logger.warning(f"Avertissement : FAISS index non trouvé à l'emplacement indiqué : {index_path}")
            return
        
        self.protocol_index = faiss.read_index(str(index_path))
        logger.info("FAISS protocol index chargé avec succès.")

    def _precompute_common_embeddings(self) -> None:
        """
        Pré-calculer les embeddings des symptômes communs (Solution 2).
        
        Réduit le temps de calcul de 200ms à <1ms pour les requêtes fréquentes.
        """
        logger.info("Pré-calcul des embeddings communs...")
        self.guardrail.precompute_embeddings(self.COMMON_SYMPTOMS)
        logger.info(f"✅ {len(self.COMMON_SYMPTOMS)} embeddings pré-calculés")

    def query(self, user_query: str, wait_time: int = 0) -> RAGResponse:
        """
        Exécution de la requête via les filtres de sécurité et le pipeline de récupération.

        Étapes du pipeline :
            1. Vérification d'injection avant récupération
            2. Recherche de similarité FAISS
            3. Vérification de la pertinence après récupération
            4. Validation de la logique médicale    
        
        Arguments :
            user_query : Question saisie par l'utilisateur.
            wait_time : Temps d'attente du patient pour la validation de la logique (minutes).
        
        Returns :
            RAGResponse avec le statut de sécurité, la latence et les résultats.
        """
        start_time = time.perf_counter()
        
        # 1. Vérification d'injection (rapide en mode simulation)
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
                message="FAISS index ne sont pas chargé.",
                threat_score=0.0,
                relevance_score=0.0,
                start_time=start_time
            )
        
        # 2. Recherche FAISS (rapide avec index approximatif)
        query_embedding = pre_check.embedding
        protocol, similarity_score = self._search_protocol(query_embedding)
        
        rules = self._search_rules(protocol.gravite)
        
        # 3. Vérification complète post-récupération
        post_check = self.guardrail.check(
            query=user_query,
            rag_score=similarity_score,
            protocol=protocol,
            rules=rules,
            wait_time=wait_time
        )
        
        if not post_check.is_safe:
            return self._build_error_response(
                message=f"Blocked by {post_check.blocked_by.value}: {post_check.details}",
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
            status="Validé par toutes les couches de sécurité",
            protocol=protocol,
            applicable_rules=rules
        )

    def _verify_input_safety(self, query: str) -> GuardrailResult:
        """
        Vérifier la sécurité de l'entrée. 
        Assure un retour systématique d'un GuardrailResult.
        Utilise le cache d'embeddings et skip ML en mode simulation.
        """
        try:
            is_safe, threat_score, embedding, reason = self.guardrail.verify_input(query)
        
            if not is_safe:
                return GuardrailResult(
                    is_safe=False,
                    blocked_by=BlockReason.INJECTION,
                    threat_score=threat_score,
                    details=reason
                )
        
            # Retour obligatoire en cas de succès
            return GuardrailResult(
                is_safe=True,
                threat_score=threat_score,
                details="Sûr",
                embedding=embedding
            )   
        
        except Exception as e:
            # Sécurité : si le code plante, on bloque par défaut
            logger.error(f"Erreur dans verify_input: {e}")
            return GuardrailResult(
                is_safe=False,
                blocked_by=BlockReason.INJECTION,
                details=f"Erreur interne lors de la vérification : {str(e)}"
            )

    def _search_protocol(
        self,
        query_embedding: npt.NDArray[np.float32]
    ) -> Tuple[MedicalProtocol, float]:
        """
        Chercher le protocole le plus similaire en utilisant FAISS.
        Utilise index approximatif en mode simulation.
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        embedding_normalized = query_embedding.astype('float32')
        faiss.normalize_L2(embedding_normalized)
        
        distances, indices = self.protocol_index.search(embedding_normalized, k=1)
        
        best_idx = int(indices[0][0])
        raw_score = float(1.0 - (distances[0][0] / 2.0))
        similarity_score = max(0.0, min(1.0, raw_score))
        
        if 0 <= best_idx < len(self.protocols_data):
            protocol = self.protocols_data[best_idx]
        else:
            protocol = MedicalProtocol(
                id="N/A",
                pathologie="Unknown",
                symptomes=[],
                gravite="ROUGE",
                unite_cible="N/A"
            )
        
        return protocol, similarity_score

    def _search_rules(self, gravite: str) -> list[HospitalRule]:
        """Retrieve hospital rules pour donnée niveau de gravité."""
        return [
            rule for rule in self.rules_data
            if rule.gravite in (gravite, "TOUS")
        ]

    def _build_error_response(
        self,
        message: str,
        threat_score: float,
        relevance_score: float,
        start_time: float
    ) -> RAGResponse:
        """Générer une réponse d'erreur avec calcul de la latence."""
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return RAGResponse(
            is_safe=False,
            threat_probability=threat_score,
            latency_ms=latency_ms,
            relevance_score=relevance_score,
            status=message,
            applicable_rules=[]
        )