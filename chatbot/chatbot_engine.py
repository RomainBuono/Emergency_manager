"""
Chatbot Engine for Emergency Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Orchestrateur principal du chatbot avec RAG et guardrails ML.
"""

import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configuration du path pour les imports
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from rag.engine import HospitalRAGEngine
from .intent_parser import IntentParser, IntentType
from .action_executor import ActionExecutor
from .response_builder import ResponseBuilder

logger = logging.getLogger("ChatbotEngine")


@dataclass
class ChatbotResponse:
    """Reponse complete du chatbot."""
    message: str
    guardrail_status: str  # "allowed" | "blocked" | "warning"
    guardrail_details: Optional[str] = None
    rag_context: Optional[Dict[str, Any]] = None
    actions_executed: Optional[List[Dict[str, Any]]] = None
    latency_ms: float = 0.0
    timestamp: datetime = None
    intent_type: str = "unknown"

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ChatbotEngine:
    """
    Orchestrateur principal du chatbot pour les urgences.

    Architecture:
    1. Input -> Guardrails (RAG mode chatbot) -> Intent Parser
    2. Intent -> ActionPlan -> Executor -> Controller
    3. Results + RAG Context -> Response Builder -> User

    Caracteristiques:
    - Utilise RAG en mode "chatbot" avec ML guardrails actifs
    - Parse le langage naturel vers actions MCP
    - Execute les actions via le controller partage
    - Affiche le status guardrail et contexte RAG
    """

    def __init__(
        self,
        controller,
        state,
        mistral_api_key: Optional[str] = None,
        decision_history_ref: Optional[List] = None
    ):
        """
        Initialise le chatbot.

        Args:
            controller: EmergencyController instance (partage avec dashboard)
            state: EmergencyState instance (partage avec dashboard)
            mistral_api_key: Cle API Mistral (ou via env)
            decision_history_ref: Reference vers l'historique des decisions
        """
        # Charger les variables d'environnement
        env_path = PROJECT_ROOT / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

        # API Key Mistral
        self.api_key = mistral_api_key or os.environ.get("MISTRAL_API_KEY")

        # Client Mistral (optionnel, pour parsing avance)
        self.mistral_client = None
        if self.api_key:
            try:
                from mistralai import Mistral
                self.mistral_client = Mistral(api_key=self.api_key)
                logger.info("Client Mistral initialise")
            except Exception as e:
                logger.warning(f"Mistral non disponible: {e}")

        # RAG en mode chatbot (ML guardrails actifs)
        try:
            self.rag_engine = HospitalRAGEngine(mode="chatbot")
            logger.info("RAG Engine initialise en mode chatbot (ML actif)")
        except Exception as e:
            logger.error(f"Erreur initialisation RAG: {e}")
            self.rag_engine = None

        # Composants
        self.intent_parser = IntentParser(self.mistral_client)
        self.action_executor = ActionExecutor(controller, state)
        self.response_builder = ResponseBuilder(self.mistral_client)  # Passer Mistral pour réponses naturelles

        # References partagees
        self.controller = controller
        self.state = state
        self.decision_history = decision_history_ref or []

        # Historique de conversation
        self.conversation_history: List[Dict[str, str]] = []

        logger.info("ChatbotEngine initialise avec succes")

    def process_message(self, user_message: str) -> ChatbotResponse:
        """
        Point d'entree principal pour traiter les messages.

        Pipeline:
        1. Valider l'input via les guardrails RAG
        2. Parser l'intention
        3. Executer les actions si necessaire
        4. Interroger RAG pour le contexte medical
        5. Construire la reponse complete

        Args:
            user_message: Message de l'utilisateur

        Returns:
            ChatbotResponse complete
        """
        start_time = datetime.now()

        # Nettoyer l'input
        user_message = user_message.strip()
        if not user_message:
            return ChatbotResponse(
                message="Veuillez entrer un message.",
                guardrail_status="allowed",
                latency_ms=0.0
            )

        # Etape 1: Validation via guardrails RAG
        rag_response = self._validate_and_query_rag(user_message)

        if rag_response and not rag_response.is_safe:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return ChatbotResponse(
                message="⚠️ Votre requete a ete bloquee par le systeme de securite.",
                guardrail_status="blocked",
                guardrail_details=rag_response.status,
                latency_ms=latency
            )

        # Etape 2: Parser l'intention
        intent = self.intent_parser.parse(user_message)
        logger.info(f"Intent detecte: {intent.intent_type.value} (conf: {intent.confidence:.2f})")

        # Etape 3: Executer les actions si necessaire
        action_results = []
        if intent.intent_type not in [IntentType.ASK_PROTOCOL, IntentType.UNKNOWN]:
            action_plan = self.intent_parser.build_action_plan(intent)
            if action_plan.actions:
                action_results = self.action_executor.execute(action_plan)
                logger.info(f"Actions executees: {len(action_results)}")

        # Etape 4: Construire la reponse
        response_data = self.response_builder.build(
            intent=intent,
            rag_response=rag_response,
            action_results=action_results,
            user_message=user_message,
            decision_history=self.decision_history
        )

        # Mettre a jour l'historique de conversation
        self._update_history(user_message, response_data["message"])

        # Calculer la latence
        latency = (datetime.now() - start_time).total_seconds() * 1000

        return ChatbotResponse(
            message=response_data["message"],
            guardrail_status="allowed",
            guardrail_details=None,
            rag_context=response_data.get("rag_context"),
            actions_executed=response_data.get("actions_executed"),
            latency_ms=latency,
            intent_type=response_data.get("intent_type", "unknown")
        )

    def _validate_and_query_rag(self, query: str):
        """
        Valide l'input et recupere le contexte protocole.

        Utilise le RAG en mode chatbot avec:
        - Detection heuristique d'injection
        - Classification ML des menaces
        - Recherche FAISS des protocoles
        """
        if not self.rag_engine:
            return None

        try:
            return self.rag_engine.query(query)
        except Exception as e:
            logger.error(f"Erreur RAG query: {e}")
            return None

    def _update_history(self, user_msg: str, bot_msg: str) -> None:
        """Maintient l'historique de conversation."""
        self.conversation_history.append({
            "role": "user",
            "content": user_msg
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": bot_msg
        })

        # Garder les 20 derniers messages (10 echanges)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def get_system_summary(self) -> str:
        """Recupere un resume de l'etat du systeme."""
        try:
            etat = self.controller.get_etat_systeme()
            patients = etat.get("patients", {})
            nb_total = len([p for p in patients.values() if p.get("statut") != "sorti"])

            consultation = etat.get("consultation", {})
            libre = consultation.get("patient_id") is None

            return f"Patients: {nb_total} | Consultation: {'Libre' if libre else 'Occupee'}"
        except Exception as e:
            return f"Erreur: {e}"

    def set_decision_history(self, history: List[Dict]) -> None:
        """Met a jour la reference vers l'historique des decisions."""
        self.decision_history = history

    def clear_conversation(self) -> None:
        """Efface l'historique de conversation."""
        self.conversation_history = []