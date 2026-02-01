"""
Response Builder pour Emergency Chatbot
Formate les reponses combinees pour l'interface utilisateur.
Version améliorée avec génération de langage naturel et monitoring.
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from .intent_parser import ParsedIntent, IntentType
from monitoring.monitoring import monitor


class ResponseBuilder:
    """
    Construit des reponses user-friendly combinant:
    - Reponse en langage naturel
    - Resultats d'execution des actions
    - Contexte RAG (protocoles/regles)
    - Status des guardrails
    """

    def __init__(self, mistral_client=None):
        """
        Initialise le ResponseBuilder.
        
        Args:
            mistral_client: Client Mistral optionnel pour génération de réponses naturelles
        """
        self.mistral_client = mistral_client

    def build(
        self,
        intent: ParsedIntent,
        rag_response,
        action_results: List[Dict[str, Any]],
        user_message: str,
        decision_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Construit la reponse complete basee sur le type d'intention.

        Args:
            intent: Intention parsee
            rag_response: Reponse du RAG (peut etre None)
            action_results: Resultats des actions executees
            user_message: Message original de l'utilisateur
            decision_history: Historique des decisions de l'agent

        Returns:
            Dict avec message, rag_context, actions, etc.
        """
        # Construire le message selon le type d'intention
        if intent.intent_type == IntentType.ADD_PATIENT:
            message = self._build_add_patient_response(action_results, user_message)
        elif intent.intent_type == IntentType.ASK_PROTOCOL:
            message = self._build_protocol_response(rag_response, user_message)
        elif intent.intent_type == IntentType.GET_STATUS:
            message = self._build_status_response(action_results, user_message)
        elif intent.intent_type == IntentType.LIST_PATIENTS:
            message = self._build_list_patients_response(action_results, user_message)
        elif intent.intent_type == IntentType.EXPLAIN_DECISION:
            message = self._build_explanation_response(decision_history, user_message)
        elif intent.intent_type == IntentType.TRANSPORT_CONSULTATION:
            message = self._build_transport_response(action_results, "consultation", user_message)
        elif intent.intent_type == IntentType.TRANSPORT_UNITE:
            message = self._build_transport_response(action_results, "unite", user_message)
        elif intent.intent_type == IntentType.UNKNOWN:
            message = self._build_conversational_response(user_message, rag_response)
        else:
            message = self._build_generic_response(intent, rag_response, user_message)

        # Construire le contexte RAG si disponible
        rag_context = None
        if rag_response and hasattr(rag_response, 'protocol') and rag_response.protocol:
            rag_context = {
                "protocol": {
                    "pathologie": rag_response.protocol.pathologie,
                    "gravite": rag_response.protocol.gravite,
                    "unite_cible": rag_response.protocol.unite_cible
                },
                "rules": [r.titre for r in (rag_response.applicable_rules or [])],
                "relevance_score": rag_response.relevance_score
            }

        return {
            "message": message,
            "rag_context": rag_context,
            "actions_executed": action_results,
            "intent_type": intent.intent_type.value
        }

    def _generate_natural_response(self, prompt: str, context: str = "") -> str:
        """
        Génère une réponse naturelle via Mistral avec monitoring.

        Args:
            prompt: Instructions pour la génération
            context: Contexte additionnel (données, résultats, etc.)

        Returns:
            Réponse générée ou None si échec
        """
        if not self.mistral_client:
            return None

        try:
            system_prompt = """Tu es un assistant pour un service d'urgences hospitalières.
Tu dois répondre de manière professionnelle, claire et empathique.
Tes réponses doivent être en phrases complètes et naturelles.
Utilise un ton professionnel mais accessible.
Réponds toujours en français."""

            full_prompt = prompt
            if context:
                full_prompt = f"{prompt}\n\nContexte/Données:\n{context}"

            start_time = time.perf_counter()

            response = self.mistral_client.chat.complete(
                model="ministral-8b-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Enregistrer les métriques du chatbot
            if hasattr(response, 'usage') and response.usage:
                monitor.log_metrics_simple(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    model_name="ministral-8b-latest",
                    source="chatbot"
                )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return None

    def _build_add_patient_response(self, results: List[Dict[str, Any]], user_message: str) -> str:
        """Construit la reponse pour l'ajout de patients."""
        if not results:
            return "Je n'ai pas pu effectuer l'ajout de patients. Veuillez réessayer ou vérifier les paramètres de votre demande."

        # Compter les succes
        total_added = 0
        patients_info = []
        errors = []

        for r in results:
            if r.get("success"):
                result_data = r.get("result", {})
                added = result_data.get("patients", [])
                total_added += len(added)
                for p in added:
                    patients_info.append({
                        "id": p['patient_id'],
                        "nom": p['nom'],
                        "gravite": p['gravite'],
                        "salle": p['salle']
                    })
                if result_data.get("errors"):
                    errors.extend(result_data["errors"])
            else:
                errors.append(r.get("error", "Erreur inconnue"))

        if total_added == 0:
            error_msg = ", ".join(errors) if errors else "raison inconnue"
            return f"Je n'ai pas réussi à ajouter les patients demandés. Le problème rencontré est le suivant : {error_msg}. Pouvez-vous vérifier votre demande et réessayer ?"

        # Générer une réponse naturelle si Mistral disponible
        if self.mistral_client and total_added > 0:
            context = f"Patients ajoutés: {total_added}\nDétails: {patients_info[:5]}"
            natural = self._generate_natural_response(
                f"L'utilisateur a demandé: '{user_message}'. Confirme l'ajout de {total_added} patient(s) de manière naturelle et professionnelle. Mentionne les IDs des patients et leurs salles assignées.",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        if total_added == 1:
            p = patients_info[0]
            response = f"J'ai bien enregistré le nouveau patient. {p['nom']} (ID: {p['id']}) a été admis avec une gravité {p['gravite']} et assigné à la {p['salle']}."
        else:
            response = f"J'ai bien enregistré {total_added} nouveaux patients dans le système.\n\nVoici le détail des admissions :\n"
            for p in patients_info[:10]:
                response += f"• {p['nom']} (ID: {p['id']}) - Gravité {p['gravite']} → {p['salle']}\n"
            
            if len(patients_info) > 10:
                response += f"\n...ainsi que {len(patients_info) - 10} autre(s) patient(s)."

        if errors:
            response += f"\n\nAttention : {len(errors)} erreur(s) se sont produites lors de l'enregistrement."

        return response

    def _build_protocol_response(self, rag_response, user_message: str) -> str:
        """Construit la reponse pour les questions de protocole."""
        if not rag_response:
            return "Je suis désolé, je n'ai pas pu accéder à la base de données des protocoles médicaux. Veuillez réessayer dans quelques instants ou consulter directement le référentiel médical."

        if not rag_response.is_safe:
            return f"Je ne peux pas traiter cette demande car elle a été identifiée comme potentiellement problématique par notre système de sécurité. Raison : {rag_response.status}"

        if not hasattr(rag_response, 'protocol') or not rag_response.protocol:
            return "Je n'ai pas trouvé de protocole correspondant à votre recherche dans notre base de données. Pourriez-vous reformuler votre question ou préciser la pathologie concernée ?"

        p = rag_response.protocol
        rules = rag_response.applicable_rules or []

        # Générer une réponse naturelle si Mistral disponible
        if self.mistral_client:
            context = f"Protocole trouvé:\n- Pathologie: {p.pathologie}\n- Gravité: {p.gravite}\n- Unité cible: {p.unite_cible}\n- Règles: {[r.titre for r in rules[:5]]}"
            natural = self._generate_natural_response(
                f"L'utilisateur demande: '{user_message}'. Explique le protocole médical trouvé de manière claire et professionnelle pour un personnel soignant.",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        response = f"Voici le protocole médical correspondant à votre recherche.\n\n"
        response += f"Pour la pathologie « {p.pathologie} », le niveau de gravité est classé {p.gravite}. "
        response += f"Le patient doit être orienté vers l'unité {p.unite_cible}.\n"

        if rules:
            response += "\nLes règles médicales applicables sont :\n"
            for rule in rules[:5]:
                response += f"• {rule.titre}\n"

        response += f"\nCe protocole a un score de pertinence de {rag_response.relevance_score:.0%} par rapport à votre recherche."

        return response

    def _build_status_response(self, results: List[Dict[str, Any]], user_message: str) -> str:
        """Construit la reponse pour l'etat du systeme."""
        if not results or not results[0].get("success"):
            return "Je rencontre des difficultés pour récupérer l'état actuel du système. Veuillez patienter quelques instants et réessayer."

        result = results[0].get("result", {})
        summary = result.get("summary", {})
        queues = result.get("queues", {})

        total = summary.get('total_patients', 0)
        attente = summary.get('en_attente', 0)
        rouge = summary.get('rouge', 0)
        jaune = summary.get('jaune', 0)
        vert = summary.get('vert', 0)
        consultation_libre = summary.get('consultation_libre', False)
        staff_dispo = summary.get('staff_disponible', 0)
        queue_consult = queues.get('consultation', 0)
        queue_transport = queues.get('transport', 0)
        heure = summary.get('heure_simulation', 'N/A')

        # Générer une réponse naturelle si Mistral disponible
        if self.mistral_client:
            context = f"Total patients: {total}, En attente: {attente}, Rouge: {rouge}, Jaune: {jaune}, Vert: {vert}, Consultation libre: {consultation_libre}, Staff dispo: {staff_dispo}"
            natural = self._generate_natural_response(
                f"L'utilisateur demande: '{user_message}'. Fais un résumé clair et professionnel de l'état du service d'urgences.",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        response = f"Voici l'état actuel du service des urgences (à {heure}).\n\n"
        
        response += f"Nous avons actuellement {total} patient(s) actif(s) dans le service"
        if attente > 0:
            response += f", dont {attente} en salle d'attente"
        response += ".\n\n"

        response += "Répartition par niveau de gravité :\n"
        if rouge > 0:
            response += f"• {rouge} patient(s) en urgence vitale (rouge)\n"
        if jaune > 0:
            response += f"• {jaune} patient(s) en urgence relative (jaune)\n"
        if vert > 0:
            response += f"• {vert} patient(s) en consultation simple (vert)\n"
        
        if rouge == 0 and jaune == 0 and vert == 0:
            response += "• Aucun patient actuellement\n"

        response += f"\nLa salle de consultation est {'disponible' if consultation_libre else 'actuellement occupée'}. "
        response += f"Nous disposons de {staff_dispo} membre(s) du personnel disponible(s).\n"

        if queue_consult > 0 or queue_transport > 0:
            response += f"\nFiles d'attente : {queue_consult} patient(s) pour consultation, {queue_transport} en attente de transport."

        return response

    def _build_list_patients_response(self, results: List[Dict[str, Any]], user_message: str) -> str:
        """Construit la reponse pour la liste des patients."""
        if not results or not results[0].get("success"):
            return "Je n'ai pas pu récupérer la liste des patients. Veuillez réessayer dans quelques instants."

        result = results[0].get("result", {})
        patients = result.get("patients", [])
        count = result.get("count", 0)

        if count == 0:
            return "Il n'y a actuellement aucun patient actif dans le système. Le service est vide."

        gravite_label = {
            "ROUGE": "urgence vitale",
            "JAUNE": "urgence relative", 
            "VERT": "consultation simple",
            "GRIS": "en observation"
        }

        # Générer une réponse naturelle si Mistral disponible
        if self.mistral_client:
            context = f"Nombre de patients: {count}\nListe: {patients[:10]}"
            natural = self._generate_natural_response(
                f"L'utilisateur demande: '{user_message}'. Présente la liste des patients de manière claire et organisée.",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        response = f"Voici la liste des {count} patient(s) actuellement pris en charge :\n\n"

        for p in patients[:15]:
            gravite = p.get("gravite", "")
            label = gravite_label.get(gravite, gravite.lower())
            response += f"• **{p['id']}** - {p['nom']}\n"
            response += f"  Statut : {p['statut'].replace('_', ' ')} | Gravité : {label} | Salle : {p['salle']}\n\n"

        if count > 15:
            response += f"...et {count - 15} autre(s) patient(s) non affiché(s)."

        return response

    def _build_explanation_response(self, decision_history: List[Dict] = None, user_message: str = "") -> str:
        """Construit la reponse pour expliquer les decisions de l'agent."""
        if not decision_history or len(decision_history) == 0:
            return "L'agent autonome n'a pas encore pris de décision. Dès qu'il effectuera une action, je pourrai vous expliquer son raisonnement."

        # Prendre la derniere decision
        last = decision_history[-1]

        timestamp = last.get("timestamp", "")
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime("%H:%M:%S")

        actions = last.get("actions", [])
        raisonnement = last.get("raisonnement", "Non spécifié")

        # Générer une réponse naturelle si Mistral disponible
        if self.mistral_client:
            context = f"Timestamp: {timestamp}\nRaisonnement: {raisonnement}\nActions: {actions[:5]}"
            natural = self._generate_natural_response(
                f"L'utilisateur demande: '{user_message}'. Explique la dernière décision de l'agent de manière pédagogique.",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        response = f"Voici l'explication de la dernière décision prise par l'agent (à {timestamp}).\n\n"
        response += f"**Raisonnement :** {raisonnement}\n\n"

        if actions:
            response += "**Actions effectuées :**\n"
            for i, action in enumerate(actions[:5], 1):
                if isinstance(action, dict):
                    tool = action.get("outil", action.get("tool", "action inconnue"))
                    justif = action.get("justification", "")
                    response += f"{i}. {tool}"
                    if justif:
                        response += f" — {justif}"
                    response += "\n"
                else:
                    response += f"{i}. {action}\n"
        else:
            response += "Aucune action spécifique n'a été enregistrée pour cette décision."

        if len(decision_history) > 1:
            response += f"\n\nL'agent a pris {len(decision_history)} décision(s) au total depuis le début de la session."

        return response

    def _build_transport_response(
        self,
        results: List[Dict[str, Any]],
        destination: str,
        user_message: str
    ) -> str:
        """Construit la reponse pour les transports."""
        if not results:
            return "Je n'ai pas pu initier le transport demandé. Veuillez vérifier que le patient existe et réessayer."

        result = results[0]
        if result.get("success"):
            return f"C'est fait ! Le transport vers la {destination} a bien été initié. Un membre du personnel est en route pour accompagner le patient."
        else:
            error = result.get("error", "Erreur inconnue")
            if "disponible" in error.lower():
                return f"Je ne peux pas effectuer ce transport pour le moment car aucun personnel n'est disponible. Veuillez réessayer dans quelques minutes."
            return f"Le transport n'a pas pu être initié. Raison : {error}"

    def _build_conversational_response(self, user_message: str, rag_response=None) -> str:
        """
        Construit une réponse conversationnelle pour les messages non reconnus.
        Utilise Mistral si disponible, sinon retourne une aide contextuelle.
        """
        user_lower = user_message.lower().strip()
        
        # Gérer les salutations
        greetings = ["bonjour", "salut", "hello", "hi", "coucou", "bonsoir"]
        if any(g in user_lower for g in greetings):
            if self.mistral_client:
                natural = self._generate_natural_response(
                    f"L'utilisateur te salue avec: '{user_message}'. Réponds poliment et présente-toi brièvement comme assistant du service d'urgences. Mentionne que tu peux aider à gérer les patients, consulter les protocoles et suivre l'état du service."
                )
                if natural:
                    return natural
            return "Bonjour ! Je suis l'assistant du service des urgences. Je peux vous aider à gérer les patients, consulter les protocoles médicaux et suivre l'état du service. Comment puis-je vous aider ?"

        # Gérer les remerciements
        thanks = ["merci", "thank", "parfait", "super", "génial", "excellent", "Parfait"]
        if any(t in user_lower for t in thanks):
            return "Je vous en prie ! N'hésitez pas si vous avez d'autres questions ou besoin d'aide."

        # Gérer les questions sur les capacités
        capabilities = ["que peux-tu", "que sais-tu", "aide", "help", "quoi faire", "comment", "fonctionn", "qu'es ce que", "Pourquoi"]
        if any(c in user_lower for c in capabilities):
            return self._build_help_response()

        # Utiliser Mistral pour une réponse contextuelle si disponible
        if self.mistral_client:
            context = ""
            if rag_response and hasattr(rag_response, 'protocol') and rag_response.protocol:
                context = f"Protocole trouvé: {rag_response.protocol.pathologie}"
            
            natural = self._generate_natural_response(
                f"L'utilisateur a dit: '{user_message}'. Tu es un assistant pour un service d'urgences hospitalières. Si tu ne comprends pas la demande, propose gentiment de l'aide et donne des exemples de ce que tu peux faire (gérer patients, protocoles, état du service).",
                context
            )
            if natural:
                return natural

        # Réponse par défaut améliorée
        return f"""Je n'ai pas bien compris votre demande : « {user_message} »

Je peux vous aider avec plusieurs types de tâches :

**Gestion des patients**
• Ajouter des patients (ex: "Ajoute 2 patients rouges avec douleur thoracique")
• Lister les patients actifs (ex: "Liste les patients")
• Transporter un patient (ex: "Transporte le patient P1234 en consultation")

**Protocoles médicaux**
• Rechercher un protocole (ex: "Quel protocole pour un AVC ?")
• Obtenir des recommandations de traitement

**Suivi du service**
• État du système (ex: "État du système" ou "Combien de patients ?")
• Explication des décisions de l'agent

Comment puis-je vous aider ?"""

    def _build_help_response(self) -> str:
        """Construit le message d'aide."""
        return """Je suis l'assistant du service des urgences et je peux vous aider dans plusieurs domaines :

**Gestion des patients**
• Pour ajouter des patients : "Ajoute 3 patients rouges avec douleur thoracique"
• Pour voir la liste : "Liste les patients" ou "Qui est en attente ?"
• Pour transporter : "Transporte le patient P1234 en consultation"

**Protocoles médicaux**
• Pour chercher un protocole : "Quel protocole pour un AVC ?" ou "Comment traiter une fracture ?"

**Informations sur le service**
• Pour l'état général : "État du système" ou "Résumé de la situation"
• Pour le nombre de patients : "Combien de patients ?"

**Agent autonome**
• Pour comprendre ses décisions : "Explique la dernière décision"

N'hésitez pas à me poser vos questions en langage naturel !"""

    def _build_generic_response(
        self,
        intent: ParsedIntent,
        rag_response,
        user_message: str
    ) -> str:
        """Construit une reponse generique."""
        if self.mistral_client:
            context = f"Intention détectée: {intent.intent_type.value}\nEntités: {intent.entities}"
            natural = self._generate_natural_response(
                f"L'utilisateur a demandé: '{user_message}'. L'intention détectée est {intent.intent_type.value}. Confirme que tu traites la demande et donne une indication de ce qui va se passer.",
                context
            )
            if natural:
                return natural
        
        return f"J'ai bien reçu votre demande. Je la traite comme une action de type « {intent.intent_type.value} ». Veuillez patienter..."