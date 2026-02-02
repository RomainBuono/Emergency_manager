"""
Agent IA intelligent pour gérer automatiquement le service des urgences.
Utilise l'API Mistral AI pour prendre des décisions optimales.
"""
"""
Agent IA intelligent pour gérer automatiquement le service des urgences.
Utilise l'API Mistral AI pour prendre des décisions optimales.
"""
# --- BLOC 1 : BOOTLOADER (Infrastructure) ---
import sys
import os
from pathlib import Path

# --- BLOC 2 : CONFIGURATION DU SYSTEME (Avant tout import logique) ---
# 1. Définition de la racine du projet (Absolue)
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent  # Remonte de 'mcp' vers la racine

# 2. Injection dans le PYTHONPATH (Pour que Python voie le dossier 'rag')
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 3. Chargement des variables d'environnement
from dotenv import load_dotenv  # On l'importe ici car on a fixé le path juste avant si besoin
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # On utilise sys.stderr pour ne pas polluer la sortie standard (si pipe MCP)
    print(f"ATTENTION : .env introuvable à {ENV_PATH}", file=sys.stderr)

import re
import json
import time
import requests
from datetime import datetime
from typing import Any, Optional, Dict, List

try:
    from rag.engine import HospitalRAGEngine
    from mistralai import Mistral
except ImportError as e:
    print(f"Erreur critique d'import : {e}", file=sys.stderr)
    print(f"Root détecté : {PROJECT_ROOT}", file=sys.stderr)
    sys.exit(1)


class EmergencyAgent:
    """Agent IA qui gère automatiquement les urgences."""

    def __init__(
        self, api_key: Optional[str] = None, mcp_base_url: str = "http://localhost:8000"
    ):
        """
        Initialise l'agent.

        Args:
            api_key: Clé API Mistral (ou via MISTRAL_API_KEY)
            mcp_base_url: URL du serveur MCP
        """
        env_path = Path(__file__).resolve().parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY non trouvée")

        self.client = Mistral(api_key=self.api_key)
        self.rag_engine = HospitalRAGEngine()
        self.mcp_base_url = mcp_base_url
        self.conversation_history = []

    def consulter_protocole_medical(self, symptomes: str, wait_time: int = 0) -> str:
        """Interroge la RAG pour obtenir le protocole sécurisé."""
        #  Appel au moteur RAG (FAISS + Guardrails)
        rag_res = self.rag_engine.query(user_query=symptomes, wait_time=wait_time)
    
        if not rag_res.is_safe:
            return f"ALERTE SÉCURITÉ : {rag_res.status}"
        
        # On renvoie le protocole et les règles à Mistral
        return f"""
            Protocole trouvé : {rag_res.protocol.pathologie}
            Gravité recommandée : {rag_res.protocol.gravite}
            Unité cible : {rag_res.protocol.unite_cible}
            Règles applicables : {[r.titre for r in rag_res.applicable_rules]}
                """     

    # ==================== INTERACTION MCP ====================

    def get_etat_systeme(self) -> Dict[str, Any]:
        """Récupère l'état complet du système."""
        try:
            response = requests.get(
                f"{self.mcp_base_url}/tools/get_etat_systeme", timeout=5
            )
            return response.json() if response.status_code == 200 else {}
        except:
            return {}

    def get_alertes(self) -> Dict[str, Any]:
        """Récupère les alertes."""
        try:
            response = requests.get(f"{self.mcp_base_url}/tools/get_alertes", timeout=5)
            return response.json() if response.status_code == 200 else {}
        except:
            return {}

    def appeler_outil_mcp(self, outil: str, params: Dict) -> Dict[str, Any]:
        """
        Appelle un outil MCP.

        Args:
            outil: Nom de l'outil (ex: "assigner_salle_attente")
            params: Paramètres de l'outil

        Returns:
            Résultat de l'outil
        """
        try:
            response = requests.post(
                f"{self.mcp_base_url}/controller/{outil}", json=params, timeout=10
            )
            return (
                response.json()
                if response.status_code == 200
                else {"success": False, "error": "Erreur HTTP"}
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== ANALYSE INTELLIGENTE ====================

    def analyser_situation(self) -> str:
        """
        Analyse l'état actuel et génère un rapport textuel.

        Returns:
            Rapport textuel de la situation
        """
        etat = self.get_etat_systeme()
        alertes = self.get_alertes()

        # Patients
        patients = etat.get("patients", {})
        nb_total = len([p for p in patients.values() if p["statut"] != "sorti"])
        nb_attente = len(
            [p for p in patients.values() if p["statut"] == "salle_attente"]
        )
        nb_rouge = len(
            [
                p
                for p in patients.values()
                if p["gravite"] == "ROUGE" and p["statut"] != "sorti"
            ]
        )
        nb_jaune = len(
            [
                p
                for p in patients.values()
                if p["gravite"] == "JAUNE" and p["statut"] != "sorti"
            ]
        )
        nb_vert = len(
            [
                p
                for p in patients.values()
                if p["gravite"] == "VERT" and p["statut"] != "sorti"
            ]
        )

        # Files
        queue_consultation = etat.get("queue_consultation", [])
        queue_transport = etat.get("queue_transport", [])

        # Consultation
        consultation = etat.get("consultation", {})
        consultation_libre = consultation.get("patient_id") is None

        # Staff
        staff = etat.get("staff", [])
        staff_dispo = [
            s
            for s in staff
            if s.get("disponible", False) and not s.get("en_transport", False)
        ]
        infirmieres_mobiles = [
            s for s in staff_dispo if s.get("type") == "infirmière_mobile"
        ]
        aides_soignants = [s for s in staff_dispo if s.get("type") == "aide_soignant"]

        # Salles
        salles = etat.get("salles_attente", [])

        rapport = f"""
=== SITUATION ACTUELLE DES URGENCES ===
Timestamp: {datetime.now().strftime("%H:%M:%S")}

📊 PATIENTS:
- Total actifs: {nb_total}
- En attente salle: {nb_attente}
- ROUGE (urgent): {nb_rouge}
- JAUNE: {nb_jaune}
- VERT: {nb_vert}

📋 FILES D'ATTENTE:
- Queue consultation: {len(queue_consultation)} patients
- Queue transport: {len(queue_transport)} patients

💼 CONSULTATION:
- Statut: {"🟢 LIBRE" if consultation_libre else "🔴 OCCUPÉE"}
{f"- Patient en cours: {consultation.get('patient_id')}" if not consultation_libre else ""}

👨‍⚕️ PERSONNEL DISPONIBLE:
- Infirmières mobiles: {len(infirmieres_mobiles)}/2 ({[s['id'] for s in infirmieres_mobiles]})
- Aides-soignants: {len(aides_soignants)}/2 ({[s['id'] for s in aides_soignants]})

🏥 SALLES D'ATTENTE:
"""
        for salle in salles:
            occupation = len(salle["patients"])
            capacite = salle["capacite"]
            taux = (occupation / capacite * 100) if capacite > 0 else 0
            surveillee = "OUI" if salle.get("surveillee_par") else "NON"
            rapport += f"- {salle['id']}: {occupation}/{capacite} ({taux:.0f}%) - Surveillée: {surveillee}\n"

        # Alertes
        rapport += "\n ALERTES:\n"
        if alertes.get("surveillance"):
            for alert in alertes["surveillance"]:
                rapport += f"- {alert}\n"
        if alertes.get("patients_longue_attente"):
            for alert in alertes["patients_longue_attente"]:
                rapport += f"- {alert}\n"
        if not alertes.get("surveillance") and not alertes.get(
            "patients_longue_attente"
        ):
            rapport += "- Aucune alerte\n"

        # Détails patients en attente consultation
        if queue_consultation:
            rapport += f"\n DÉTAILS PATIENTS EN ATTENTE CONSULTATION (top 3):\n"
            for i, patient_id in enumerate(queue_consultation[:3]):
                patient = patients.get(patient_id, {})
                temps_attente = self._calculer_temps_attente(
                    patient.get("arrived_at", "")
                )
                salle_actuelle = patient.get("salle_actuelle", "Non assigné")
                rapport += f"{i+1}. ID={patient_id} | {patient.get('prenom')} {patient.get('nom')} - {patient.get('gravite')} - {temps_attente} min - Salle: {salle_actuelle} - Symptômes: {patient.get('symptomes', '')}\n"

        return rapport

    def _calculer_temps_attente(self, arrived_at: str) -> int:
        """Calcule le temps d'attente en minutes."""
        try:
            arrival = datetime.fromisoformat(arrived_at.replace("Z", "+00:00"))
            delta = datetime.now() - arrival.replace(tzinfo=None)
            return int(delta.total_seconds() / 60)
        except:
            return 0

    def demander_decision_a_mistral(self, situation: str) -> str:
        """
        Demande à Mistral de prendre une décision basée sur la situation actuelle
        en utilisant le moteur RAG pour valider les protocoles médicaux.
        """
        # 1. Interroger la RAG pour obtenir un contexte médical sécurisé
        # On utilise le moteur FAISS et les Guardrails pour valider l'entrée
        rag_res = self.rag_engine.query(user_query=situation)
        
        # 2. Préparer le bloc de connaissances médicales (Augmentation)
        # Si le Guardrail détecte une menace, on injecte l'alerte
        if not rag_res.is_safe:
            contexte_medical = f"⚠️ ALERTE SÉCURITÉ RAG : {rag_res.status}"
        else:
            contexte_medical = f"""
        === PROTOCOLE MÉDICAL VALIDÉ (RAG) ===
        Pathologie détectée : {rag_res.protocol.pathologie}
        Gravité recommandée : {rag_res.protocol.gravite}
        Unité cible prioritaire : {rag_res.protocol.unite_cible}
        Règles de gestion applicables : {[r.titre for r in rag_res.applicable_rules]}
        Score de pertinence : {rag_res.relevance_score:.2f}
        """

        # 3. Construction du prompt enrichi
        prompt = f"""Tu es un agent IA expert en gestion des urgences hospitalières, piloté par un moteur RAG.

=== SITUATION ACTUELLE ===
{situation}

{contexte_medical}

=== TES OUTILS DISPONIBLES (MCP) ===
1. ajouter_patient(id, prenom, nom, gravite, symptomes, age)
2. assigner_salle_attente(patient_id, salle_id=None)
3. assigner_surveillance(staff_id, salle_id)
4. verifier_et_gerer_surveillance() -> Gère auto les salles vides
5. demarrer_transport_consultation(patient_id, staff_id)
6. finaliser_transport_consultation(patient_id)
7. terminer_consultation(patient_id, unite_cible)
8. sortir_patient(patient_id) -> Pour les retours à domicile
9. demarrer_transport_unite(patient_id, staff_id)
10. finaliser_transport_unite(patient_id)

=== DIRECTIVES DE DÉCISION ===
1. Respecte STRICTEMENT la gravité indiquée par le protocole RAG.
2. Priorité absolue aux patients ROUGE.
3. Un patient VERT avec attente > 360 min passe avant un JAUNE.
4. Ne réassigne JAMAIS un patient possédant déjà une salle.

=== FORMAT DE RÉPONSE ===
Réponds UNIQUEMENT avec un JSON. Le champ "raisonnement" doit être sur UNE SEULE LIGNE.

{{
  "actions": [
    {{
      "outil": "nom_outil",
      "params": {{"param1": "valeur1"}},
      "justification": "Explication courte"
    }}
  ],
  "raisonnement": "Stratégie globale sur une seule ligne"
}}
"""

        try:
            # Appel à l'API Mistral avec le contexte augmenté
            response = self.client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content

            # Nettoyage du bloc JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return response_text

        except Exception as e:
            return json.dumps({
                "actions": [], 
                "raisonnement": f"Erreur lors de la génération Mistral : {str(e)}"
            })

    def executer_decision(self, decision_json: str) -> Dict:
        """
        Exécute les actions décidées par Mistral.

        Args:
            decision_json: JSON contenant les actions

        Returns:
            Rapport d'exécution
        """
        match = re.search(r"\{.*\}", decision_json, re.DOTALL)
        if match:
            decision_json = match.group()
        try:
            # Essayer de parser directement
            decision = json.loads(decision_json)
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur JSON initiale: {str(e)}")
            print(f"Tentative de nettoyage...")

            # Nettoyer les retours à la ligne dans les strings JSON
            try:
                # Remplacer les vrais retours à la ligne par des espaces
                cleaned = decision_json.replace("\n", " ").replace("\r", " ")
                # Supprimer espaces multiples

                cleaned = re.sub(r"\s+", " ", cleaned)

                decision = json.loads(cleaned)
                print(" JSON nettoyé et parsé avec succès")
            except json.JSONDecodeError as e2:
                print(f" Échec même après nettoyage: {str(e2)}")
                print(f"Réponse brute (300 premiers chars): {decision_json[:300]}")
                return {
                    "success": False,
                    "error": f"JSON invalide: {str(e2)}",
                    "raw_response": decision_json,
                    "raisonnement": "Erreur de parsing",
                    "nb_actions": 0,
                    "resultats": [],
                }

        actions = decision.get("actions", [])
        raisonnement = decision.get("raisonnement", "")

        print(f"\n {len(actions)} actions à exécuter")

        resultats = []

        for i, action in enumerate(actions, 1):
            outil = action.get("outil")
            params = action.get("params", {})
            justification = action.get("justification", "")

            print(f"\n🤖 Action {i}/{len(actions)}: {outil}")
            print(f"   Params: {params}")
            print(f"   Justification: {justification}")

            resultat = self.appeler_outil_mcp(outil, params)

            resultats.append(
                {
                    "outil": outil,
                    "params": params,
                    "justification": justification,
                    "resultat": resultat,
                }
            )

            if resultat.get("success"):
                print(f"  Succès")
            else:
                print(f" Échec: {resultat.get('error', 'Erreur inconnue')}")

        return {
            "success": True,
            "raisonnement": raisonnement,
            "nb_actions": len(actions),
            "resultats": resultats,
        }

    # ==================== CYCLE PRINCIPAL ====================

    def cycle_decision(self) -> Dict[str, Any]:
        """
        Effectue un cycle complet de décision:
        1. Analyse la situation
        2. Demande décision à Mistral
        3. Exécute les actions

        Returns:
            Rapport complet du cycle
        """
        print("\n" + "=" * 60)
        print(" NOUVEAU CYCLE DE DÉCISION (Mistral AI)")
        print("=" * 60)

        # 1. Analyser
        print("\n📊 Analyse de la situation...")
        situation = self.analyser_situation()
        print(situation)

        # 2. Décider
        print("\n🧠 Demande de décision à Mistral...")
        decision_json = self.demander_decision_a_mistral(situation)
        print(f"\n Décision reçue:")
        print(decision_json)

        # 3. Exécuter
        print("\n⚙️ Exécution des actions...")
        rapport = self.executer_decision(decision_json)

        print("\n Cycle terminé")
        print(f"   Raisonnement: {rapport.get('raisonnement', 'N/A')}")
        print(f"   Actions exécutées: {rapport.get('nb_actions', 0)}")

        return {
            "timestamp": datetime.now().isoformat(),
            "situation": situation,
            "decision": decision_json,
            "execution": rapport,
        }

    def mode_autonome(self, intervalle_sec: int = 10, nb_cycles: Optional[int] = None):
        """
        Mode autonome: l'agent tourne en boucle.

        Args:
            intervalle_sec: Temps entre chaque cycle
            nb_cycles: Nombre de cycles (None = infini)
        """
        import time

        print(" Démarrage du mode autonome (Mistral AI)")
        print(f"   Intervalle: {intervalle_sec} secondes")
        print(f"   Cycles: {'Infini' if nb_cycles is None else nb_cycles}")

        cycle_count = 0

        try:
            while nb_cycles is None or cycle_count < nb_cycles:
                cycle_count += 1

                print(f"\n{'='*60}")
                print(f" CYCLE #{cycle_count}")
                print(f"{'='*60}")

                self.cycle_decision()

                if nb_cycles is None or cycle_count < nb_cycles:
                    print(f"\n💤 Pause de {intervalle_sec} secondes...")
                    time.sleep(intervalle_sec)

        except KeyboardInterrupt:
            print("\n\n Arrêt demandé par l'utilisateur")
            print(f"   Total cycles effectués: {cycle_count}")


# ==================== SCRIPT PRINCIPAL ====================

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    # Charger le .env
    load_dotenv()

    print(" Emergency Manager - Agent IA (Mistral)")
    print("=" * 60)

    # Vérifier la clé API
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print(" ERREUR: Variable d'environnement MISTRAL_API_KEY non définie")
        print("\n Pour définir la clé:")
        print("   Créez un fichier .env avec:")
        print("   MISTRAL_API_KEY='votre_clé'")
        sys.exit(1)

    print(f" Clé API trouvée: {api_key[:15]}...")

    # Créer l'agent
    try:
        agent = EmergencyAgent()
        print(" Agent créé avec succès")
    except Exception as e:
        print(f" Erreur création agent: {e}")
        sys.exit(1)

    # Menu
    print("\n Choisissez un mode:")
    print("1. Cycle unique (teste une fois)")
    print("2. Mode autonome (boucle infinie)")
    print("3. Mode autonome limité (N cycles)")

    choix = input("\nVotre choix (1/2/3): ").strip()

    if choix == "1":
        print("\n Exécution d'un cycle unique...")
        agent.cycle_decision()

    elif choix == "2":
        intervalle = input("Intervalle entre cycles (secondes, défaut=10): ").strip()
        intervalle = int(intervalle) if intervalle.isdigit() else 10
        agent.mode_autonome(intervalle_sec=intervalle)

    elif choix == "3":
        nb_cycles = input("Nombre de cycles: ").strip()
        nb_cycles = int(nb_cycles) if nb_cycles.isdigit() else 5
        intervalle = input("Intervalle (secondes, défaut=10): ").strip()
        intervalle = int(intervalle) if intervalle.isdigit() else 10
        agent.mode_autonome(intervalle_sec=intervalle, nb_cycles=nb_cycles)

    else:
        print(" Choix invalide")
        sys.exit(1)

    print("\n Agent terminé")