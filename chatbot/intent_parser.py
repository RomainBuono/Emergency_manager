"""
Intent Parser for Emergency Chatbot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Parse les commandes en langage naturel vers des actions MCP structurees.
Utilise regex pour les patterns courants + Mistral pour les cas complexes.
"""

import re
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Pattern

logger = logging.getLogger("IntentParser")


class IntentType(Enum):
    """Types d'intentions supportees par le chatbot."""
    ADD_PATIENT = "add_patient"
    TRANSPORT_CONSULTATION = "transport_consultation"
    TRANSPORT_UNITE = "transport_unite"
    ASSIGN_ROOM = "assign_room"
    ASSIGN_SURVEILLANCE = "assign_surveillance"
    GET_STATUS = "get_status"
    ASK_PROTOCOL = "ask_protocol"
    EXPLAIN_DECISION = "explain_decision"
    LIST_PATIENTS = "list_patients"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Representation structuree d'une intention parsee."""
    intent_type: IntentType
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_query: str = ""
    requires_rag: bool = False

    def __post_init__(self):
        # Determiner si RAG est necessaire
        if self.intent_type == IntentType.ASK_PROTOCOL:
            self.requires_rag = True


@dataclass
class ActionPlan:
    """Plan d'actions MCP a executer."""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    estimated_count: int = 0


class IntentParser:
    """
    Parse les commandes en langage naturel vers des actions MCP.

    Supporte:
    - Ajout de patients: "Ajoute 5 patients rouges avec dyspnee"
    - Transport: "Transporte le patient P1234 en consultation"
    - Questions protocole: "Quel protocole pour douleur thoracique?"
    - Etat systeme: "Quel est l'etat du systeme?"
    - Explications: "Explique la derniere decision"
    """

    # Patterns regex pour detection rapide (en francais)
    PATTERNS: Dict[IntentType, List[Pattern]] = {
        IntentType.ADD_PATIENT: [
            re.compile(
                r"ajout(?:e|er?)?\s+(\d+)?\s*patients?\s*(rouges?|jaunes?|verts?|gris)?(?:\s+avec\s+(.+))?",
                re.IGNORECASE
            ),
            re.compile(
                r"cr[ée](?:e|er?)?\s+(\d+)?\s*patients?\s*(rouges?|jaunes?|verts?|gris)?",
                re.IGNORECASE
            ),
            re.compile(
                r"(\d+)\s*patients?\s*(rouges?|jaunes?|verts?|gris)?(?:\s+avec\s+(.+))?",
                re.IGNORECASE
            ),
        ],
        IntentType.TRANSPORT_CONSULTATION: [
            re.compile(
                r"transport(?:e|er?)?\s+(?:le\s+)?patient\s+(P\d+)\s+(?:en|vers)\s+consultation",
                re.IGNORECASE
            ),
            re.compile(
                r"(?:envoie|amene|emmene)\s+(?:le\s+)?patient\s+(P\d+)\s+(?:en|vers)\s+consultation",
                re.IGNORECASE
            ),
        ],
        IntentType.TRANSPORT_UNITE: [
            re.compile(
                r"transport(?:e|er?)?\s+(?:le\s+)?patient\s+(P\d+)\s+(?:en|vers)\s+(?:unite|unité)\s+(\w+)",
                re.IGNORECASE
            ),
        ],
        IntentType.GET_STATUS: [
            re.compile(r"(?:etat|état|status|situation)\s+(?:du\s+)?(?:systeme|système)", re.IGNORECASE),
            re.compile(r"(?:comment\s+va|resume|résumé)\s+(?:le\s+)?(?:service|urgences?)", re.IGNORECASE),
            re.compile(r"combien\s+(?:de\s+)?patients?", re.IGNORECASE),
        ],
        IntentType.ASK_PROTOCOL: [
            re.compile(r"(?:quel(?:le)?|qu'est-ce que)\s+(?:le\s+)?protocole\s+(?:pour\s+)?(.+)", re.IGNORECASE),
            re.compile(r"protocole\s+(?:medical\s+)?(?:pour\s+)?(.+)", re.IGNORECASE),
            re.compile(r"(?:comment\s+traiter|que\s+faire\s+pour)\s+(.+)", re.IGNORECASE),
        ],
        IntentType.EXPLAIN_DECISION: [
            re.compile(r"expliqu(?:e|er?)\s+(?:la\s+)?(?:derniere|derni[èe]re)?\s*decision", re.IGNORECASE),
            re.compile(r"pourquoi\s+(?:l'agent|le\s+systeme)\s+a\s+(?:fait|pris)", re.IGNORECASE),
            re.compile(r"(?:quelle|quelles)\s+(?:etait|était)\s+(?:la\s+)?(?:decision|raison)", re.IGNORECASE),
        ],
        IntentType.LIST_PATIENTS: [
            re.compile(r"(?:liste|lister|montre|affiche)\s+(?:les\s+)?patients?", re.IGNORECASE),
            re.compile(r"(?:qui\s+est|quels?\s+patients?)\s+(?:en\s+)?(?:attente|consultation)", re.IGNORECASE),
        ],
    }

    # Mapping couleurs francaises -> enum
    GRAVITE_MAP = {
        "rouge": "ROUGE",
        "rouges": "ROUGE",
        "jaune": "JAUNE",
        "jaunes": "JAUNE",
        "vert": "VERT",
        "verts": "VERT",
        "gris": "GRIS",
    }

    def __init__(self, mistral_client=None):
        """
        Initialise le parser.

        Args:
            mistral_client: Client Mistral optionnel pour parsing complexe
        """
        self.mistral_client = mistral_client

    def parse(self, user_input: str) -> ParsedIntent:
        """
        Parse l'input utilisateur en intention structuree.

        Utilise une approche en deux etapes:
        1. Pattern matching rapide pour les commandes courantes
        2. Fallback Mistral pour les cas complexes

        Args:
            user_input: Texte saisi par l'utilisateur

        Returns:
            ParsedIntent avec le type et les entites extraites
        """
        user_input = user_input.strip()

        # Etape 1: Pattern matching rapide
        intent = self._try_pattern_match(user_input)
        if intent and intent.confidence >= 0.7:
            return intent

        # Etape 2: Fallback Mistral si disponible
        if self.mistral_client:
            mistral_intent = self._parse_with_mistral(user_input)
            if mistral_intent.confidence > (intent.confidence if intent else 0):
                return mistral_intent

        # Retourner le meilleur resultat ou UNKNOWN
        return intent or ParsedIntent(
            intent_type=IntentType.UNKNOWN,
            raw_query=user_input,
            confidence=0.0
        )

    def _try_pattern_match(self, text: str) -> Optional[ParsedIntent]:
        """Tente de matcher avec les patterns regex."""

        for intent_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    entities = self._extract_entities(intent_type, match, text)
                    return ParsedIntent(
                        intent_type=intent_type,
                        entities=entities,
                        confidence=0.85,
                        raw_query=text
                    )

        return None

    def _extract_entities(
        self,
        intent_type: IntentType,
        match: re.Match,
        full_text: str
    ) -> Dict[str, Any]:
        """Extrait les entites selon le type d'intention."""

        entities = {}
        groups = match.groups()

        if intent_type == IntentType.ADD_PATIENT:
            # Pattern: (count)? (gravite)? (symptomes)?
            count = int(groups[0]) if groups[0] else 1
            gravite = self.GRAVITE_MAP.get(groups[1].lower() if groups[1] else "", "JAUNE")
            symptomes = groups[2].strip() if len(groups) > 2 and groups[2] else "Symptomes non precises"

            entities = {
                "count": count,
                "gravite": gravite,
                "symptomes": symptomes
            }

        elif intent_type == IntentType.TRANSPORT_CONSULTATION:
            entities = {"patient_id": groups[0]}

        elif intent_type == IntentType.TRANSPORT_UNITE:
            entities = {
                "patient_id": groups[0],
                "unite": groups[1] if len(groups) > 1 else None
            }

        elif intent_type == IntentType.ASK_PROTOCOL:
            # Extraire la condition medicale
            condition = groups[0] if groups else full_text
            entities = {"condition": condition.strip()}

        return entities

    def _parse_with_mistral(self, text: str) -> ParsedIntent:
        """Utilise Mistral pour parser les intentions complexes."""

        prompt = f"""Tu es un parseur d'intentions pour un systeme de gestion des urgences hospitalieres.

Analyse cette commande et retourne un JSON avec:
- intent: ADD_PATIENT | TRANSPORT_CONSULTATION | TRANSPORT_UNITE | ASSIGN_ROOM | GET_STATUS | ASK_PROTOCOL | EXPLAIN_DECISION | LIST_PATIENTS | UNKNOWN
- entities: dictionnaire des entites extraites (count, gravite, symptomes, patient_id, condition, etc.)
- confidence: score de confiance (0-1)

Exemples:
- "Ajoute 5 patients rouges avec dyspnee" -> {{"intent": "ADD_PATIENT", "entities": {{"count": 5, "gravite": "ROUGE", "symptomes": "dyspnee"}}, "confidence": 0.95}}
- "Quel protocole pour douleur thoracique?" -> {{"intent": "ASK_PROTOCOL", "entities": {{"condition": "douleur thoracique"}}, "confidence": 0.9}}

Commande a analyser: "{text}"

Reponds UNIQUEMENT avec le JSON, sans explication."""

        try:
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content.strip()

            # Nettoyer le JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(response_text)

            intent_str = parsed.get("intent", "UNKNOWN")
            try:
                intent_type = IntentType(intent_str.lower())
            except ValueError:
                intent_type = IntentType.UNKNOWN

            return ParsedIntent(
                intent_type=intent_type,
                entities=parsed.get("entities", {}),
                confidence=parsed.get("confidence", 0.5),
                raw_query=text
            )

        except Exception as e:
            logger.warning(f"Erreur parsing Mistral: {e}")
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                raw_query=text,
                confidence=0.0
            )

    def build_action_plan(self, intent: ParsedIntent) -> ActionPlan:
        """
        Convertit une intention en plan d'actions MCP executable.

        Gere les actions multiplicatives:
        - "Ajoute 5 patients" -> 5 appels ajouter_patient

        Args:
            intent: Intention parsee

        Returns:
            ActionPlan avec liste d'actions
        """
        actions = []
        explanation = ""

        if intent.intent_type == IntentType.ADD_PATIENT:
            count = intent.entities.get("count", 1)
            # On prépare les paramètres de base
            base_params = {
                "gravite": intent.entities.get("gravite", "JAUNE"),
                "symptomes": intent.entities.get("symptomes", "Non precise"),
                "prenom": intent.entities.get("prenom"),
                "nom": intent.entities.get("nom"),       
                "age": intent.entities.get("age")       
            }
            
            # On nettoie pour ne pas envoyer de clés None
            tool_params = {k: v for k, v in base_params.items() if v is not None}

            for i in range(count):
                actions.append({
                    "tool": "ajouter_patient",
                    "params": tool_params
                })

            explanation = f"Ajout de {count} patient(s)"

        elif intent.intent_type == IntentType.TRANSPORT_CONSULTATION:
            patient_id = intent.entities.get("patient_id")
            if patient_id:
                actions.append({
                    "tool": "demarrer_transport_consultation",
                    "params": {"patient_id": patient_id}
                })
                explanation = f"Transport du patient {patient_id} vers consultation"

        elif intent.intent_type == IntentType.TRANSPORT_UNITE:
            patient_id = intent.entities.get("patient_id")
            if patient_id:
                actions.append({
                    "tool": "demarrer_transport_unite",
                    "params": {"patient_id": patient_id}
                })
                explanation = f"Transport du patient {patient_id} vers unite"

        elif intent.intent_type == IntentType.GET_STATUS:
            actions.append({
                "tool": "get_status",
                "params": {}
            })
            explanation = "Recuperation de l'etat du systeme"

        elif intent.intent_type == IntentType.LIST_PATIENTS:
            actions.append({
                "tool": "list_patients",
                "params": {}
            })
            explanation = "Liste des patients"

        return ActionPlan(
            actions=actions,
            explanation=explanation,
            estimated_count=len(actions)
        )
