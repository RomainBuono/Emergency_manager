"""
Medical RAG Guardrail System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Système de sécurité multi-couches pour la gestion des urgences médicales.
"""

import re
import pickle
import logging
from pathlib import Path
from typing import Final, Optional, Pattern, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from sentence_transformers import SentenceTransformer
import numpy as np
import numpy.typing as npt

from .models import MedicalProtocol, HospitalRule
import os
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'

# Configuration du logger
logger = logging.getLogger("MedicalGuardrail")

class BlockReason(Enum):
    """Énumération des raisons possibles de blocage."""
    INJECTION = "injection"
    RELEVANCE = "relevance"
    LOGIC = "logic"

@dataclass(frozen=True)
class GuardrailResult:
    """

Résultat de la vérification des garde-fous.
    Arg :
        is_safe : Indique si la requête a passé toutes les couches de vérification.
        blocked_by : La couche qui a bloqué la requête, le cas échéant.
        threat_score : Probabilité d'une attaque par injection (0,0-1,0).
        relevance_score : Score de similarité RAG (0,0-1,0).
        details : Explication du résultat en langage clair.
    """
    is_safe: bool
    blocked_by: Optional[BlockReason] = None
    threat_score: float = 0.0
    relevance_score: float = 0.0
    details: str = ""
    embedding: Optional[npt.NDArray[np.float32]] = None
    
    def __post_init__(self) -> None:
        """Validate attribute constraints."""
        if not 0.0 <= self.threat_score <= 1.0:
            raise ValueError(f"threat_score must be in [0, 1], got {self.threat_score}")
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(f"relevance_score must be in [0, 1], got {self.relevance_score}")


@dataclass(frozen=True)
class GuardrailConfig:
    """
    Paramètres de configuration du système de guardrail system.
    
    Attributes:
        ml_threshold: Seuil pour la détection d'injection basée sur l'apprentissage automatique (0,0-1,0).
        min_relevance: Score de similarité RAG minimum requis.
        model_path: Chemin d'accès au modèle de classification entraîné.
        embedding_model: Nom du modèle du sentence transformer.
    """
    
    ml_threshold: float = 0.5
    min_relevance: float = 0.4
    model_path: Optional[Path] = None
    embedding_model: str = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not 0.0 <= self.ml_threshold <= 1.0:
            raise ValueError(f"ml_threshold must be in [0, 1], got {self.ml_threshold}")
        if not 0.0 <= self.min_relevance <= 1.0:
            raise ValueError(f"min_relevance must be in [0, 1], got {self.min_relevance}")


class InjectionDetector:
    """
    Détecteur de schémas d'injection heuristique amélioré.
    Implémente la correspondance de modèles basée sur les expressions régulières pour les techniques d'injection courantes,
    les injections SQL, les attaques XSS et la détection de mots clés sensibles.
    """
    
    INJECTION_PATTERNS: Final[tuple[Pattern, ...]] = (
        # Prompt injection patterns (existants)
        re.compile(r'ignore\s+(previous|preceding|instructions?|prompts?)', re.IGNORECASE),
        re.compile(r'(oublie|forget|discard)\s+(ton rôle|your role|instructions?)', re.IGNORECASE),
        re.compile(r'(tu es|you are)\s+(maintenant|now)\s+(?!un patient|le médecin)', re.IGNORECASE),
        re.compile(r'mode\s+(développeur|developer|admin|debug|test)', re.IGNORECASE),
        re.compile(r'(désactive|disable|override)\s+(sécurité|security|validation|protocole)', re.IGNORECASE),
        re.compile(r'répète\s+après\s+moi', re.IGNORECASE),
        re.compile(r'(system|admin):\s*', re.IGNORECASE),
        re.compile(r'###\s*(new|nouvelle)\s*instruction', re.IGNORECASE),
        re.compile(r'(jailbreak|DAN|do anything now)', re.IGNORECASE),
        re.compile(r'pretend\s+you', re.IGNORECASE),
        re.compile(r'simulation\s+(de\s+)?test', re.IGNORECASE),
        
        # SQL Injection patterns (NOUVEAUX)
        re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+', re.IGNORECASE),
        re.compile(r'\bFROM\s+\w+', re.IGNORECASE),
        re.compile(r'\bWHERE\s+.*=', re.IGNORECASE),
        re.compile(r'(AND|OR)\s+\d+\s*=\s*\d+', re.IGNORECASE),  # AND 1=1, OR 1=1
        re.compile(r';\s*--', re.IGNORECASE),  # SQL comment
        re.compile(r"'\s*;\s*", re.IGNORECASE),  # Statement termination
        re.compile(r'\bUNION\s+SELECT', re.IGNORECASE),
        
        # XSS patterns (NOUVEAUX)
        re.compile(r'<\s*script[^>]*>', re.IGNORECASE),
        re.compile(r'</\s*script\s*>', re.IGNORECASE),
        re.compile(r'<\s*iframe[^>]*>', re.IGNORECASE),
        re.compile(r'javascript\s*:', re.IGNORECASE),
        re.compile(r'on(load|error|click|mouse)\s*=', re.IGNORECASE),
        re.compile(r'<\s*img[^>]*on', re.IGNORECASE),
        
        # Parameter injection 
        re.compile(r'(SYSTEM|ADMIN|ROOT)_\w+\s*=', re.IGNORECASE),
        re.compile(r'OVERRIDE\s*=\s*(True|False|1|0)', re.IGNORECASE),
        re.compile(r'\${.*}', re.IGNORECASE),  # Template injection
        re.compile(r'{{.*}}', re.IGNORECASE),  # Template injection
        
        # Command injection 
        re.compile(r';\s*(ls|cat|wget|curl|bash|sh|python)', re.IGNORECASE),
        re.compile(r'\|\s*(ls|cat|grep|awk)', re.IGNORECASE),
        re.compile(r'`[^`]+`', re.IGNORECASE),  # Backtick execution
        re.compile(r'\$\([^)]+\)', re.IGNORECASE),  # $() execution
    )
    
    SENSITIVE_KEYWORDS: Final[frozenset[str]] = frozenset({
        # Credentials 
        'mot de passe', 'password', 'clé api', 'api key', 'token',
        
        # Code/System 
        'code source', 'source code', 'guardrail',
        
        # Database operations 
        'drop table', 'delete from', 'insert into', 'update set',
        'truncate', 'exec', 'execute',
        
        # Data extraction 
        'dump', 'export', 'affiche toutes', 'affiche tous',
        'liste toutes', 'liste tous', 'données patients',
        'base de données', 'database', 'sqlite',
        
        # System internals 
        'pydantic', 'fastapi', 'système', 'config',
        'environnement', 'variables', 'secrets',
        
        # File operations 
        'télécharge', 'download', 'upload', 'fichier système',
    })
    
    # Patterns de détection de longueur/structure suspecte
    SUSPICIOUS_STRUCTURE_PATTERNS: Final[tuple[Pattern, ...]] = (
        re.compile(r'(.)\1{50,}'),  # Répétition excessive (>50 fois)
        re.compile(r'[<>]{3,}'),  # Multiples balises
        re.compile(r'[\[\]]{5,}'),  # Multiples crochets
        re.compile(r'[;|&]{2,}'),  # Multiples séparateurs shell
    )
    
    @classmethod
    def detect(cls, query: str) -> tuple[bool, str]:
        """
        Détecter les schémas d'injection dans la requête.
        
        Args:
            query: Données saisies par l'utilisateur à analyser.
            
        Returns:
            Tuple of (is_injection, matched_pattern).
            Si aucune injection n'est détectée, retourne (False, "").
        """
        # 1. Check regex patterns
        for pattern in cls.INJECTION_PATTERNS:
            if match := pattern.search(query):
                return True, f"Pattern: {pattern.pattern[:50]}"
        
        # 2. Check sensitive keywords
        query_lower = query.lower()
        for keyword in cls.SENSITIVE_KEYWORDS:
            if keyword in query_lower:
                return True, f"Keyword: {keyword}"
        
        # 3. Check suspicious structure 
        for pattern in cls.SUSPICIOUS_STRUCTURE_PATTERNS:
            if match := pattern.search(query):
                return True, f"Suspicious structure: {match.group()[:30]}"
        
        # 4. Check for excessive length 
        if len(query) > 1000:
            return True, "La requête dépasse la longueur maximale (1000 caractères)."
        
        return False, ""


class OperationalQueryClassifier:
    """
    Classificateur pour les requêtes opérationnelles (non médicales)
    
    Ces requêtes interagissent avec le système MCP et ne nécessitent pas
    des scores de pertinence RAG élevés.
    """
    
    OPERATIONAL_PATTERNS: Final[tuple[Pattern, ...]] = (
        re.compile(r'assigner?\s+patient\s+P\d+', re.IGNORECASE),
        re.compile(r'(libérer|free)\s+salle\s+\d+', re.IGNORECASE),
        re.compile(r'(état|status)\s+(des\s+)?(salles?|rooms?)', re.IGNORECASE),
        re.compile(r'temps\s+d\'attente', re.IGNORECASE),
        re.compile(r'(staff|personnel)\s+disponible', re.IGNORECASE),
        re.compile(r'(appeler|call)\s+(médecin|infirmière|staff)', re.IGNORECASE),
        re.compile(r'(total|nombre)\s+(tokens?|patients?|co2)', re.IGNORECASE),
        re.compile(r'liste\s+patients?\s+en\s+attente', re.IGNORECASE),
    )
    
    @classmethod
    def is_operational(cls, query: str) -> bool:
        """
        Vérifiez si la requête est opérationnelle.
        Args:
            query: Saisie utilisateur pour la classification.
        Returns:
            Vrai si la requête correspond aux modèles opérationnels.
        """
        return any(pattern.search(query) for pattern in cls.OPERATIONAL_PATTERNS)

class MedicalLogicValidator:
    
    MAX_WAIT_VERT: Final[int] = 360
    MAX_WAIT_JAUNE: Final[int] = 120
    
    @classmethod
    def validate(
        cls,
        protocol: MedicalProtocol,
        rules: list[HospitalRule],
        wait_time: int = 0
    ) -> tuple[bool, str]:
        """
        Valider uniquement les règles de cohérence essentielles.
        Version simplifiée axée sur les contrôles de sécurité essentiels.
        """
        # Règle 1 : ROUGE incompatible avec retour maison
        if protocol.gravite == "ROUGE":
            if any(r.id == "regle_retour_gris" for r in rules):
                return False, "Protocole incomplet"
        
        # Règle 2 : VERT > 360min nécessite exception
        if protocol.gravite == "VERT" and wait_time > cls.MAX_WAIT_VERT:
            if not any("360min" in r.id for r in rules):
                return False, f"VERT > {cls.MAX_WAIT_VERT}min sans execption"
        
        # Règle 3 : JAUNE > 120min nécessite réévaluation
        if protocol.gravite == "JAUNE" and wait_time > cls.MAX_WAIT_JAUNE:
            if not any("réévaluation" in getattr(r, 'titre', '').lower() for r in rules):
                return False, f"JAUNE > {cls.MAX_WAIT_JAUNE}min without reassessment"
        
        return True, "Coherent"


class RAGGuardrail:
    """
    Système de sécurité multicouche pour les requêtes médicales RAG.

    Avec la simulation dashboard : 
    - Mode simulation (use_ml=False) : rapide, sans ML
    - Mode chatbot (use_ml=True) : sécurisé, avec ML complet
    - Cache d'embeddings pour requêtes fréquentes
    
    Met en œuvre trois couches de vérification :
        1. Détection d'injection (ML + heuristics)
        2. Vérification de la pertinence (adaptive thresholds)
        3. Validation de la logique médicale (protocol coherence)
    
    Attributes:
        config: Guardrail paramètres de configuration.
        classifier: Classificateur ML pré-entraîné pour la détection d'injections.
        encoder: Sentence transformer pour les embedding generation.
    
    Example:
        >>> config = GuardrailConfig(ml_threshold=0.6)
        >>> guardrail = RAGGuardrail(config)
        >>> result = guardrail.check("Assigner patient P042 en salle 1")
        >>> assert result.is_safe
        # Mode simulation (rapide)
        >>> guardrail = RAGGuardrail(config, use_ml=False)
        # Mode chatbot (sécurisé)
        >>> guardrail = RAGGuardrail(config, use_ml=True)
    """
    
    def __init__(self, config: Optional[GuardrailConfig] = None, use_ml: bool = True ) -> None:
        """
        Initialiser le guardrail avec configuration et mode.
        
        Args:
            config: Configuration optionnelle
            use_ml: Si True, charge le ML (mode chatbot). Si False, mode rapide (simulation).
        """
        self.config = config or GuardrailConfig()
        self.use_ml = use_ml # Sauvegard 
        self.embedding_cache: Dict[str, npt.NDArray] = {}
        self._encoder = None
        self._classifier = None
        self._model_path = self._resolve_model_path()

        if use_ml:
            logger.info("Mode chatbot : Guardrails ML activés (sécurisé mais plus lent)")
        else:
            logger.info("Mode simulation : Guardrails ML désactivés (rapide)")


    @property
    def classifier(self):
        """Charge le classificateur uniquement quand nécessaire si use_ml = True"""
        if not self.use_ml:
            return None
        if self._classifier is None:
            self._classifier = self._load_classifier(self._model_path)
            logger.info("Modèle ML d'injection chargé")
        return self._classifier
    
    @property
    def encoder(self):
        """Charge l'encoder uniquement quand nécessaire."""
        if self._encoder is None:
            self._encoder = SentenceTransformer(self.config.embedding_model)
            logger.info("Modèle d'embedding chargé")
        return self._encoder
    
    def _resolve_model_path(self) -> Path:
        """Resolve the model file path."""
        if self.config.model_path is not None:
            return self.config.model_path
        
        return Path(__file__).parent.parent / "storage" / "guardrail.pkl"
    
    @staticmethod
    def _load_classifier(path: Path):
        """
        Charger le classificateur pré-entraîné depuis le disque.
        """
        if not path.exists():
            raise FileNotFoundError(f"Guardrail model not found: {path}")
        
        with open(path, "rb") as file:
            return pickle.load(file)
        
    def embed_query(self, query: str) -> npt.NDArray:
        """
        ✅ NOUVEAU : Calculer l'embedding avec cache (Solution 2).
        
        Args:
            query: Texte à encoder
            
        Returns:
            Embedding numpy array
        """
        # Normaliser la clé de cache
        cache_key = query.lower().strip()
        
        # Vérifier le cache
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        # Calculer l'embedding
        embedding = self.encoder.encode(query, convert_to_tensor=False)
        
        # Mettre en cache (limiter à 200 entrées max)
        if len(self.embedding_cache) < 200:
            self.embedding_cache[cache_key] = embedding
        
        return embedding
    
    def precompute_embeddings(self, queries: List[str]) -> None:
        """
        ✅ NOUVEAU : Pré-calculer les embeddings pour une liste de requêtes.
        
        Utile pour pré-charger les symptômes communs en mode simulation.
        
        Args:
            queries: Liste de requêtes à pré-calculer
        """
        logger.info(f"Pré-calcul de {len(queries)} embeddings...")
        for query in queries:
            _ = self.embed_query(query)  # Calcule et met en cache
        logger.info(f"✅ {len(queries)} embeddings pré-calculés et mis en cache")


    
    def verify_input(self, query: str) -> tuple[bool, float, npt.NDArray, str]:
        """
        Vérifier les entrées pour les attaques par injection (Couche 1).
        
        Utiliser seulement si use_ml=True, sinon vérification rapide.
        
        Args:
            query: Saisie utilisateur à vérifier.
            
        Returns:
            (is_safe, threat_score, embedding, reason)
        """
        # 1. Vérification heuristique (toujours active, rapide)
        is_injection, pattern = InjectionDetector.detect(query)
        if is_injection:
            empty_embedding = np.array([])
            return False, 1.0, empty_embedding, f"Injection detected: {pattern}"
        
        # 2. Calculer l'embedding (avec cache)
        embedding = self.embed_query(query)
        
        # 3. Vérification ML (seulement si use_ml=True)
        if not self.use_ml:
            # Mode rapide : pas de ML, retour immédiat
            return True, 0.0, embedding, "OK (mode rapide)"
        
        # Mode chatbot : vérification ML complète
        threat_probability = self._predict_threat(embedding)
        is_safe = threat_probability < self.config.ml_threshold
        reason = "" if is_safe else f"ML threat score: {threat_probability:.3f}"
        
        return is_safe, threat_probability, embedding, reason
    
    def _predict_threat(self, embedding: npt.NDArray) -> float:
        """
        Prédire la probabilité de menace d'injection à l'aide d'un classificateur d'apprentissage automatique.
        
        Args:
            embedding: Vecteur d'intégration de requête.
            
        Returns:
            Probabilité d'injection (0,0-1,0).
        """
        probabilities = self.classifier.predict_proba(embedding.reshape(1, -1))
        return float(probabilities[0][1])
    
    def verify_relevance(self, query: str, score: float) -> tuple[bool, str]:
        """
        Vérifier la pertinence de la récupération RAG (Couche 2).
        
        Utilise des seuils adaptatifs : les requêtes opérationnelles s’affranchissent des exigences de pertinence
        tandis que les requêtes médicales requièrent une similarité minimale.
        
        Args:
            query: Vérification des données saisies par l'utilisateur.
            score: Score de similarité RAG (0,0-1,0).
            
        Returns:
            Tuple of (is_relevant, reason).
        """
        if OperationalQueryClassifier.is_operational(query):
            return True, "Operational query (whitelist)"
        
        is_relevant = score >= self.config.min_relevance
        reason = "Sufficient" if is_relevant else f"Score {score:.3f} < {self.config.min_relevance}"
        
        return is_relevant, reason
    
    def verify_logic(
        self,
        protocol: MedicalProtocol,
        rules: list[HospitalRule],
        wait_time: int = 0
    ) -> tuple[bool, str]:
        """
        Vérifier la cohérence médicale et logistique (Couche 3).
        
        Args:
            protocol: Protocole médical récupéré.
            rules: Règles hospitalières associées.
            wait_time: Temps d'attente du patient en minutes.
            
        Returns:
            Tuple of (is_coherent, reason).
        """
        return MedicalLogicValidator.validate(protocol, rules, wait_time)
    
    def check(
        self,
        query: str,
        rag_score: Optional[float] = None,
        protocol: Optional[MedicalProtocol] = None,
        rules: Optional[list[HospitalRule]] = None,
        wait_time: int = 0
    ) -> GuardrailResult:
        """
        Exécuter la vérification complète du système guardrail.
        
        Il s'agit du point d'entrée principal du système de guardrail. Il exécute
        toutes les couches de vérification applicables en fonction des paramètres fournis.
        
        Args:
            query: Entrée utilisateur à vérifier.
            rag_score: Score de similarité RAG (facultatif) pour la couche 2.
            protocol: Protocole médical (facultatif) pour la couche 3.
            rules: Règles hospitalières (facultatives) pour la couche 3.
            wait_time: Temps d'attente du patient pour la couche 3.
            
        Returns:
            GuardrailResult avec le résultat de la vérification.
        """
        is_safe, threat_score, embedding, reason = self.verify_input(query)
        if not is_safe:
            return GuardrailResult(
                is_safe=False,
                blocked_by=BlockReason.INJECTION,
                threat_score=threat_score,
                details=reason
            )
        
        if rag_score is not None:
            is_relevant, reason = self.verify_relevance(query, rag_score)
            if not is_relevant:
                return GuardrailResult(
                    is_safe=False,
                    blocked_by=BlockReason.RELEVANCE,
                    threat_score=threat_score,
                    relevance_score=rag_score,
                    details=reason
                )
        
        if protocol is not None and rules is not None:
            is_coherent, reason = self.verify_logic(protocol, rules, wait_time)
            if not is_coherent:
                return GuardrailResult(
                    is_safe=False,
                    blocked_by=BlockReason.LOGIC,
                    threat_score=threat_score,
                    relevance_score=rag_score or 0.0,
                    details=reason
                )
        
        return GuardrailResult(
            is_safe=True,
            threat_score=threat_score,
            relevance_score=rag_score or 0.0,
            details="Toutes les couches sont validés"
        )