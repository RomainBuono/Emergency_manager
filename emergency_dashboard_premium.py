import os

os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "mcp"))

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
import time
import random
import pandas as pd
import json as json_module


# Imports
from mcp.state import (
    EmergencyState,
    Patient,
    Gravite,
    UniteCible,
    StatutPatient,
    TypeStaff,
)
from mcp.controllers.emergency_controller import EmergencyController
from rag.engine import HospitalRAGEngine

# Imports des composants V2
from premium_styles import get_premium_css
from dashboard_components import (
    render_hero_zone,
    render_critical_situation_zone,
    render_kpi_secondary,
    render_staff_section_with_tension,
    render_room_with_risk,
    render_operational_timeline,
    render_queue_item_simple,
    render_spacer,
    render_divider,
    render_section_header,
)

from chatbot_component import render_chatbot_premium, initialize_chatbot

# Import du module monitoring pour l'onglet Métriques
try:
    from monitoring.monitoring import monitor

    MONITORING_AVAILABLE = True
except ImportError as e:
    MONITORING_AVAILABLE = False

    # Créer un mock pour éviter les erreurs
    class MockMonitor:
        def get_summary(self):
            return {
                "global": {
                    "total_requests": 0,
                    "total_cost": 0.0,
                    "total_energy_kwh": 0.0,
                    "total_co2_kg": 0.0,
                    "avg_latency_ms": 0.0,
                },
                "by_source": {},
            }

        def get_recent_history(self, n):
            return []

        def reset(self):
            pass

        def log_metrics_simple(self, **kwargs):
            pass

    monitor = MockMonitor()
    print(f"⚠️ Module monitoring non disponible : {e}")

# Vérifier disponibilité
try:
    from chatbot.chatbot_engine import ChatbotEngine

    CHATBOT_AVAILABLE = True
except ImportError:
    CHATBOT_AVAILABLE = False

st.set_page_config(
    page_title="🤖 AI Emergency Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injection CSS Premium V2
st.markdown(get_premium_css(), unsafe_allow_html=True)

# ========== SESSION STATE ==========

if "state" not in st.session_state:
    st.session_state.state = EmergencyState()
    st.session_state.temps = 0
    st.session_state.running = False
    st.session_state.events = []
    st.session_state.agent_enabled = True
    st.session_state.agent_speed = 1.0
    st.session_state.agent = None
    st.session_state.actions_count = 0
    if "controller" not in st.session_state:
        st.session_state.controller = EmergencyController(st.session_state.state)
    controller = st.session_state.controller

if "agent_loaded" not in st.session_state:
    st.session_state.agent_loaded = False

if "decision_history" not in st.session_state:
    st.session_state.decision_history = []

if "chatbot" not in st.session_state and CHATBOT_AVAILABLE:
    st.session_state.chatbot = initialize_chatbot(
        controller=st.session_state.controller,
        state=st.session_state.state,
        decision_history=st.session_state.decision_history,
    )
    st.session_state.chat_history = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def add_event(msg, emoji="ℹ️"):
    """Ajoute un événement au log"""
    st.session_state.events.append(
        {
            "time": st.session_state.temps,
            "msg": msg,
            "emoji": emoji,
        }
    )
    if len(st.session_state.events) > 50:
        st.session_state.events = st.session_state.events[-50:]


def ajouter_patient_complet(gravite: Gravite = None) -> Patient:
    """Ajoute un patient ET l'assigne automatiquement à une salle."""
    if gravite is None:
        gravites = [Gravite.ROUGE, Gravite.JAUNE, Gravite.VERT, Gravite.GRIS]
        weights = [0.2, 0.3, 0.3, 0.2]
        gravite = random.choices(gravites, weights=weights)[0]

    # 80 PRÉNOMS
    prenoms = [
        "Jean",
        "Marie",
        "Pierre",
        "Sophie",
        "Luc",
        "Emma",
        "Thomas",
        "Julie",
        "Lucas",
        "Hugo",
        "Léa",
        "Chloé",
        "Nathan",
        "Camille",
        "Antoine",
        "Nicolas",
        "Sarah",
        "Alexandre",
        "Charlotte",
        "Maxime",
        "Laura",
        "Julien",
        "Océane",
        "Mathieu",
        "Pauline",
        "Raphaël",
        "Manon",
        "Benjamin",
        "Clara",
        "Romain",
        "Louise",
        "Théo",
        "Zoé",
        "Louis",
        "Alice",
        "Gabriel",
        "Inès",
        "Arthur",
        "Jade",
        "Tom",
        "Lola",
        "Paul",
        "Lily",
        "Enzo",
        "Anna",
        "Adam",
        "Rose",
        "Victor",
        "Eva",
        "Jules",
        "Mia",
        "Ethan",
        "Nina",
        "Mathis",
        "Lucie",
        "Noah",
        "Amélie",
        "Clément",
        "Anaïs",
        "Simon",
        "Margaux",
        "Baptiste",
        "Justine",
        "Valentin",
        "Emilie",
        "Adrien",
        "Melissa",
        "Bastien",
        "Aurore",
        "Damien",
        "Fanny",
        "Kevin",
        "Coralie",
        "Anthony",
        "Elise",
        "David",
        "Céline",
        "Florian",
        "Audrey",
        "Quentin",
    ]

    # 80 NOMS
    noms = [
        "Martin",
        "Bernard",
        "Dubois",
        "Thomas",
        "Robert",
        "Richard",
        "Petit",
        "Durand",
        "Leroy",
        "Moreau",
        "Simon",
        "Laurent",
        "Lefebvre",
        "Michel",
        "Garcia",
        "David",
        "Bertrand",
        "Roux",
        "Vincent",
        "Fournier",
        "Morel",
        "Girard",
        "Andre",
        "Mercier",
        "Dupont",
        "Lambert",
        "Bonnet",
        "Francois",
        "Martinez",
        "Legrand",
        "Garnier",
        "Faure",
        "Rousseau",
        "Blanc",
        "Guerin",
        "Muller",
        "Henry",
        "Roussel",
        "Nicolas",
        "Perrin",
        "Morin",
        "Mathieu",
        "Clement",
        "Gauthier",
        "Dumont",
        "Lopez",
        "Fontaine",
        "Chevalier",
        "Robin",
        "Masson",
        "Sanchez",
        "Gerard",
        "Nguyen",
        "Boyer",
        "Denis",
        "Lemaire",
        "Duval",
        "Joly",
        "Gautier",
        "Roger",
        "Roche",
        "Roy",
        "Noel",
        "Meyer",
        "Lucas",
        "Meunier",
        "Jean",
        "Perez",
        "Marchand",
        "Dufour",
        "Blanchard",
        "Marie",
        "Barbier",
        "Brun",
        "Dumas",
        "Brunet",
        "Schmitt",
        "Leroux",
        "Colin",
        "Fernandez",
    ]

    symptomes_map = {
        Gravite.ROUGE: [
            "Douleur thoracique intense",
            "Difficulté respiratoire sévère",
            "Perte de conscience",
            "Hémorragie importante",
        ],
        Gravite.JAUNE: [
            "Fracture suspectée",
            "Douleurs abdominales",
            "Fièvre élevée persistante",
            "Vertiges importants",
        ],
        Gravite.VERT: [
            "Entorse cheville",
            "Plaie superficielle",
            "Fièvre modérée",
            "Mal de dos",
        ],
        Gravite.GRIS: [
            "Consultation routine",
            "Renouvellement ordonnance",
            "Certificat médical",
            "Contrôle de suivi",
        ],
    }

    # ✅ FIX : ID UNIQUE GARANTI avec timestamp + random
    # Au lieu de time.time()*1000 qui donne des doublons en boucle rapide
    patient_id = f"P{int(time.time()*1000) % 100000}-{random.randint(0, 999):03d}"

    patient = Patient(
        id=patient_id,
        prenom=random.choice(prenoms),
        nom=random.choice(noms),
        gravite=gravite,
        symptomes=random.choice(symptomes_map[gravite]),
        age=random.randint(18, 85),
        antecedents=[],
    )

    # 🔍 DEBUG : Log avant ajout
    print(
        f"🔍 DEBUG: Tentative ajout patient {patient.id} ({patient.prenom} {patient.nom})"
    )

    result = st.session_state.controller.ajouter_patient(patient)

    # 🔍 DEBUG : Log résultat ajout
    print(f"🔍 DEBUG: Résultat ajouter_patient = {result}")

    if result["success"]:
        assign_result = st.session_state.controller.assigner_salle_attente(patient.id)

        # 🔍 DEBUG : Log résultat assignation
        print(f"🔍 DEBUG: Résultat assigner_salle_attente = {assign_result}")

        if assign_result["success"]:
            salle_id = assign_result["salle_id"]
            add_event(
                f"Patient {patient.prenom} {patient.nom} assigné à {salle_id}", "🏥"
            )
            print(f"✅ Patient {patient.id} assigné avec succès à {salle_id}")
        else:
            add_event(
                f"⚠️ {patient.prenom} {patient.nom} - Échec assignation: {assign_result.get('message', 'Inconnu')}",
                "❌",
            )
            print(f"❌ Échec assignation {patient.id}: {assign_result}")
    else:
        add_event(
            f"❌ {patient.prenom} {patient.nom} - Échec création: {result.get('message', 'Inconnu')}",
            "❌",
        )
        print(f"❌ Échec création patient {patient.id}: {result}")

    return patient


# ========== AGENT (IDENTIQUE) ==========


class EmergencyAgent:
    """Agent IA orchestrant les flux."""

    def __init__(self, state: EmergencyState, controller):
        self.state = state
        self.controller = controller
        self.rag_engine = HospitalRAGEngine(mode="simulation")

        # ✨ Initialisation du client Mistral
        self.mistral_client = None
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key:
            try:
                from mistralai import Mistral

                self.mistral_client = Mistral(api_key=api_key)
                print("✅ Client Mistral initialisé")
            except ImportError:
                print("⚠️ mistralai package non installé")

        # Compteur pour limiter les appels LLM
        self.iteration_count = 0
        self.llm_frequency = 5  # Appel LLM toutes les 5 itérations

    def cycle_orchestration(self) -> list[str]:
        """Exécute le cycle complet des opérations urgences."""
        actions = []
        self.iteration_count += 1

        # 1. FINALISATION des transports (toujours exécuté)
        actions.extend(self._finaliser_transports())

        # 2. ✨ Appel LLM toutes les N itérations
        if self.mistral_client and self.iteration_count % self.llm_frequency == 0:
            llm_actions = self._decide_with_llm()
            actions.extend(llm_actions)
        else:
            # Mode règles simples entre les appels LLM
            actions.extend(self._gerer_surveillance())

            action_sortie = self._gerer_sortie_consultation()
            if action_sortie:
                actions.append(action_sortie)

            action_trans_unite = self._gerer_transport_unite()
            if action_trans_unite:
                actions.append(action_trans_unite)

            action_entree = self._gerer_consultation()
            if action_entree:
                actions.append(action_entree)

        return [a for a in actions if a is not None]

    def _decide_with_llm(self) -> list[str]:
        """✨ Utilise Mistral pour décider des actions à entreprendre."""
        actions = []

        # Construire le contexte
        etat = self.state.to_dict()
        patients = etat.get("patients", {})
        patients_actifs = [p for p in patients.values() if p.get("statut") != "sorti"]

        # Résumé de l'état
        nb_attente = len(
            [p for p in patients_actifs if p.get("statut") == "salle_attente"]
        )
        nb_rouge = len([p for p in patients_actifs if p.get("gravite") == "ROUGE"])
        nb_jaune = len([p for p in patients_actifs if p.get("gravite") == "JAUNE"])
        consultation_libre = etat.get("consultation", {}).get("patient_id") is None
        patient_en_consultation = etat.get("consultation", {}).get("patient_id")

        staff_data = etat.get("staff", [])
        staff_dispo = len(
            [s for s in staff_data if s.get("disponible") and not s.get("en_transport")]
        )

        queue_consultation = etat.get("queue_consultation", [])
        queue_transport = etat.get("queue_transport", [])

        prompt = f"""Tu es un agent IA gérant un service d'urgences hospitalières.

    ÉTAT ACTUEL:
    - Patients en attente: {nb_attente} (Rouge: {nb_rouge}, Jaune: {nb_jaune})
    - Consultation: {"LIBRE" if consultation_libre else f"OCCUPÉE par {patient_en_consultation}"}
    - Personnel disponible: {staff_dispo}
    - File consultation: {len(queue_consultation)} patients
    - File transport: {len(queue_transport)} patients

    RÈGLES:
    1. Priorité ROUGE > JAUNE > VERT
    2. Surveillance obligatoire toutes les 15 min
    3. Garder au moins 2 soignants pour la surveillance
    4. Orienter les patients VERT/GRIS vers MAISON après consultation
    5. Orienter les ROUGE/JAUNE vers l'unité appropriée (CARDIO, CHIRURGIE, etc.)

    Quelle action prioritaire dois-tu faire? Réponds en JSON:
    {{"action": "TRANSPORT_CONSULTATION|TRANSPORT_UNITE|SURVEILLANCE|TERMINER_CONSULTATION|ATTENDRE", "patient_id": "Pxxxx ou null", "destination": "MAISON|CARDIO|CHIRURGIE|null", "justification": "raison courte"}}"""

        try:
            start_time = time.perf_counter()

            response = self.mistral_client.chat.complete(
                model="ministral-3b-2512",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # ✨ CRUCIAL : Enregistrer les métriques
            if hasattr(response, "usage") and response.usage:
                try:
                    monitor.log_metrics_simple(
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                        latency_ms=latency_ms,
                        model_name="ministral-3b-2512",
                        source="agent",
                    )
                except Exception as e:
                    print(f"Erreur log métriques: {e}")

            # Parser la réponse
            response_text = response.choices[0].message.content.strip()

            # Nettoyer le JSON
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            decision = json_module.loads(response_text)
            action_type = decision.get("action", "ATTENDRE")
            patient_id = decision.get("patient_id")
            destination = decision.get("destination")
            justification = decision.get("justification", "")

            # Exécuter l'action décidée
            if action_type == "TRANSPORT_CONSULTATION" and patient_id:
                staff_dispo_list = [
                    s
                    for s in self.state.staff
                    if s.disponible
                    and not s.en_transport
                    and s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]
                ]
                if staff_dispo_list and self.state.consultation.est_libre():
                    res = self.controller.demarrer_transport_consultation(
                        patient_id, staff_dispo_list[0].id
                    )
                    if res.get("success"):
                        st.session_state.actions_count += 1
                        actions.append(
                            f"🤖 LLM: {patient_id} → consultation ({justification})"
                        )

            elif action_type == "TERMINER_CONSULTATION" and patient_id:
                dest_map = {
                    "MAISON": UniteCible.MAISON,
                    "CARDIO": UniteCible.CARDIO,
                    "CHIRURGIE": UniteCible.CHIRURGIE,
                    "REA": UniteCible.REA,
                }
                dest = dest_map.get(destination, UniteCible.MAISON)
                res = self.controller.terminer_consultation(patient_id, dest)
                if res.get("success"):
                    st.session_state.actions_count += 1
                    actions.append(
                        f"🤖 LLM: Consultation terminée → {destination} ({justification})"
                    )

            elif action_type == "TRANSPORT_UNITE" and patient_id:
                staff_dispo_list = [
                    s
                    for s in self.state.staff
                    if s.disponible
                    and not s.en_transport
                    and s.type == TypeStaff.AIDE_SOIGNANT
                ]
                if staff_dispo_list:
                    res = self.controller.demarrer_transport_unite(
                        patient_id, staff_dispo_list[0].id
                    )
                    if res.get("success"):
                        st.session_state.actions_count += 1
                        actions.append(
                            f"🤖 LLM: {patient_id} → unité ({justification})"
                        )

            elif action_type == "SURVEILLANCE":
                actions.extend(self._gerer_surveillance())
                if actions:
                    actions[-1] = f"🤖 LLM: Surveillance ({justification})"

            else:
                actions.append(f"🤖 LLM: Attente ({justification})")

            # Enregistrer la décision
            st.session_state.decision_history.append(
                {
                    "timestamp": datetime.now(),
                    "decision": decision,
                    "temps_simulation": st.session_state.temps,
                }
            )

        except Exception as e:
            print(f"Erreur LLM: {e}")
            actions.append(f"⚠️ Erreur LLM: {str(e)[:50]}")

        return actions

    def _finaliser_transports(self) -> list[str]:
        actions = []
        for staff in self.state.staff:
            if staff.en_transport and staff.fin_transport_prevue:
                if self.state.current_time >= staff.fin_transport_prevue:
                    pid = staff.patient_transporte_id
                    if staff.destination_transport == "consultation":
                        self.controller.finaliser_transport_consultation(pid)
                        actions.append(f"✅ Arrivée en consultation : {pid}")
                        st.session_state.actions_count += 1
                    else:
                        self.controller.finaliser_transport_unite(pid)
                        p = self.state.patients.get(pid)
                        actions.append(f"🏁 {p.prenom if p else pid} arrivé en unité")
                        st.session_state.actions_count += 1
        return actions

    def _gerer_transport_unite(self) -> Optional[str]:
        queue = self.state.get_queue_transport_sortie()
        if not queue:
            return None
        p = queue[0]
        staff_mobiles = [
            s
            for s in self.state.staff
            if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]
        ]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]
        as_dispo = [s for s in staff_dispo if s.type == TypeStaff.AIDE_SOIGNANT]

        if as_dispo and len(staff_dispo) >= 3:
            res = self.controller.demarrer_transport_unite(p.id, as_dispo[0].id)
            if res.get("success"):
                st.session_state.actions_count += 1
                return f"🚑 {p.prenom} {p.nom} ({p.id}) -> {p.unite_cible.value} (AS, 45 min)"

        if staff_dispo:
            agent = staff_dispo[0]
            res = self.controller.retourner_patient_salle_attente(p.id, agent.id)
            if res.get("success"):
                st.session_state.actions_count += 1
                return (
                    f"🔄 {p.prenom} {p.nom} ({p.id}) replacé en salle (Secours, 5 min)"
                )
        return None

    def _gerer_consultation(self) -> Optional[str]:
        if not self.state.consultation.est_libre():
            return None
        staff_mobiles = [
            s
            for s in self.state.staff
            if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]
        ]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]
        if len(staff_dispo) < 2:
            return None
        queue = self.state.get_queue_consultation()
        if queue and staff_dispo:
            res = self.controller.demarrer_transport_consultation(
                queue[0].id, staff_dispo[0].id
            )
            if res.get("success"):
                st.session_state.actions_count += 1
                return f"🚑 {queue[0].prenom} {queue[0].nom} ({queue[0].id}) vers consultation"
        return None

    def _gerer_surveillance(self) -> list[str]:
        actions = []
        staff_dispo = self.state.get_staff_disponible(
            TypeStaff.INFIRMIERE_MOBILE
        ) + self.state.get_staff_disponible(TypeStaff.AIDE_SOIGNANT)
        for salle in self.state.salles_attente:
            if (
                salle.temps_sans_surveillance(self.state.current_time) > 10
                and len(salle.patients) > 0
            ):
                en_poste = any(
                    s.salle_surveillee == salle.id and not s.en_transport
                    for s in self.state.staff
                )
                if not en_poste and staff_dispo:
                    agent = staff_dispo.pop(0)
                    res = self.controller.assigner_surveillance(agent.id, salle.id)
                    if res.get("success"):
                        st.session_state.actions_count += 1
                        actions.append(f"📋 {agent.id} affecté à {salle.id}")
        return actions

    def _gerer_sortie_consultation(self) -> Optional[str]:
        if self.state.consultation.est_libre():
            return None
        pid = self.state.consultation.patient_id
        patient = self.state.patients.get(pid)
        debut = self.state.consultation.debut_consultation
        if not debut:
            return None
        duree_ecoulee = (self.state.current_time - debut).total_seconds() / 60
        duree_min = 10 if patient.gravite == Gravite.VERT else 20
        if duree_ecoulee >= duree_min:
            destination = (
                UniteCible.MAISON
                if patient.gravite in [Gravite.VERT, Gravite.GRIS]
                else UniteCible.CARDIO
            )
            res = self.controller.terminer_consultation(pid, destination)
            if res.get("success"):
                st.session_state.actions_count += 1
                return f"✅ Consultation terminée : {patient.prenom} {patient.nom} ({patient.id}) -> {destination.value}"
        return None


# ========== SIDEBAR ==========

with st.sidebar:
    st.markdown("### ⏱️ Temps")
    heures = st.session_state.temps // 60
    minutes = st.session_state.temps % 60
    st.markdown(
        f"<h2 style='color: #667eea; font-size: 2.5rem; margin: 0;'>{heures:02d}h{minutes:02d}</h2>",
        unsafe_allow_html=True,
    )

    render_divider()

    # ✅ AJOUT : Section chatbot
    st.markdown("### 💬 AI Assistant")

    if st.button("🤖 Ouvrir Assistant", use_container_width=True, type="secondary"):
        st.session_state.show_chatbot = not st.session_state.get("show_chatbot", False)
        st.rerun()

    st.markdown("### Simulation")

    # Play / Pause
    if st.button(
        "▶️ Play" if not st.session_state.running else "⏸️ Pause",
        use_container_width=True,
        type="primary",
        key="play_pause_btn",
    ):
        st.session_state.running = not st.session_state.running
        st.rerun()

    # Reset
    if st.button(
        "🔄 Reset", use_container_width=True, type="secondary", key="reset_btn"
    ):
        st.session_state.state = EmergencyState()
        st.session_state.controller = EmergencyController(st.session_state.state)
        st.session_state.temps = 0
        st.session_state.events = []
        st.session_state.agent = None
        st.session_state.actions_count = 0
        st.session_state.decision_history = []
        st.rerun()
    # st.markdown("### 🎮 Simulation")
    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("▶️ Play" if not st.session_state.running else "⏸️ Pause", use_container_width=True):
    #         st.session_state.running = not st.session_state.running
    #         st.rerun()
    # with col2:
    #     if st.button("🔄 Reset", use_container_width=True):
    #         st.session_state.state = EmergencyState()
    #         st.session_state.controller = EmergencyController(st.session_state.state)
    #         st.session_state.temps = 0
    #         st.session_state.events = []
    #         st.session_state.agent = None
    #         st.session_state.actions_count = 0
    #         st.rerun()

    render_divider()
    st.markdown("### 🤖 Agent")
    st.session_state.agent_enabled = st.checkbox(
        "Activer l'agent", value=st.session_state.agent_enabled
    )
    if st.session_state.agent_enabled:
        st.success("✅ Agent actif")
    else:
        st.warning("⏸️ Agent désactivé")
    st.markdown("**Vitesse agent**")
    st.session_state.agent_speed = st.slider(
        "Vitesse (s)",
        0.1,
        2.0,
        st.session_state.agent_speed,
        0.1,
        label_visibility="collapsed",
    )

    render_divider()
    st.markdown("### ➕ Actions")
    if st.button("👤 +1 Patient", use_container_width=True, type="primary"):
        patient = ajouter_patient_complet()
        st.success(f"✅ {patient.prenom} {patient.nom} ({patient.gravite}) ajouté !")
        time.sleep(0.3)
        st.rerun()
    if st.button("👥 +5 Patients", use_container_width=True):
        patients_ajoutes = 0
        patients_refuses = 0
        for _ in range(5):
            patient = ajouter_patient_complet()
            # Vérifier si vraiment assigné
            if patient.id in st.session_state.state.patients:
                patients_ajoutes += 1
            else:
                patients_refuses += 1

        if patients_refuses > 0:
            st.warning(
                f"⚠️ {patients_ajoutes}/5 ajoutés ({patients_refuses} refusés - salles pleines)"
            )
        else:
            add_event(f"📊 {patients_ajoutes} patients ajoutés", "📊")
            st.success(f"✅ {patients_ajoutes} patients ajoutés !")
        time.sleep(0.3)
        st.rerun()
    if st.button("🚨 Afflux (15)", use_container_width=True):
        rouge_count = 0
        jaune_count = 0
        refused_count = 0

        for _ in range(15):
            if random.random() < 0.7:
                patient = ajouter_patient_complet(Gravite.ROUGE)
                if patient.id in st.session_state.state.patients:
                    rouge_count += 1
                else:
                    refused_count += 1
            else:
                patient = ajouter_patient_complet(Gravite.JAUNE)
                if patient.id in st.session_state.state.patients:
                    jaune_count += 1
                else:
                    refused_count += 1

        total_added = rouge_count + jaune_count
        add_event(f"🚨 Afflux : {rouge_count} ROUGE + {jaune_count} JAUNE", "🚨")

        if refused_count > 0:
            st.error(
                f"🚨 AFFLUX : {total_added}/15 ajoutés ({refused_count} refusés - SATURATION !)"
            )
        else:
            st.error(f"🚨 AFFLUX : {rouge_count} ROUGE + {jaune_count} JAUNE !")

        time.sleep(0.5)
        st.rerun()

    render_divider()
    st.markdown("### 📊 Statistiques Agent")
    st.markdown(f"**Actions prises**")
    st.markdown(
        f"<h2 style='color: #00D084; font-size: 2rem; margin: 0;'>{st.session_state.actions_count}</h2>",
        unsafe_allow_html=True,
    )

# ========== ONGLETS ==========

tab1, tab2, tab3 = st.tabs(["DASHBOARD", " AI Assistant", "Monitoring"])

# ========== MAIN CONTENT - STRUCTURE STORY-DRIVEN ==========
with tab1:
    etat = st.session_state.controller.get_etat_systeme()
    patients = etat.get("patients", {})

    # Calculs KPI
    nb_total = len([p for p in patients.values() if p.get("statut") != "sorti"])
    nb_rouge_attente = len(
        [
            p
            for p in patients.values()
            if p.get("gravite") == "ROUGE" and p.get("statut") == "salle_attente"
        ]
    )
    nb_attente = len(
        [p for p in patients.values() if p.get("statut") == "salle_attente"]
    )
    nb_consultation = 1 if etat.get("consultation", {}).get("patient_id") else 0
    nb_en_transport = len(
        [p for p in patients.values() if "transport" in p.get("statut", "")]
    )

    # Déterminer statut système
    if nb_rouge_attente >= 3:
        system_status = "CRITICAL"
    elif nb_rouge_attente > 0:
        system_status = "TENSION"
    else:
        system_status = "SAFE"

    # ==========  1️⃣ HERO ZONE ==========

    render_hero_zone(
        critical_backlog=nb_rouge_attente,
        ai_managing=nb_total,
        status=system_status,
        temps=st.session_state.temps,
    )

    render_spacer("lg")

    # ========== 2️⃣ CRITICAL SITUATION ==========

    alertes = etat.get("alertes_surveillance", [])
    patients_critiques = [
        p
        for p in patients.values()
        if p.get("gravite") == "ROUGE"
        and p.get("statut") == "salle_attente"
        and p.get("temps_attente_minutes", 0) > 30
    ]

    if alertes or patients_critiques:
        render_critical_situation_zone(alertes, patients_critiques)
        render_spacer("lg")

    # ========== 3️⃣ KPI SECONDAIRES (Niveau B) ==========

    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_secondary("CAPACITY", f"{nb_attente}/{20}", "📊")
    with col2:
        avg_wait = 12  # À calculer réellement
        render_kpi_secondary("AVG WAIT", f"{avg_wait} min", "⏱️")
    with col3:
        ai_status = "✅ ACTIVE" if st.session_state.agent_enabled else "⏸️ PAUSED"
        render_kpi_secondary("AI STATUS", ai_status, "🤖")

    render_spacer("xl")

    # ========== 4️⃣ OPERATIONS FLOW ==========

    render_section_header("Operations Flow", "🏥")

    # Salles d'attente
    salles = etat.get("salles_attente", [])
    for salle in salles:
        render_room_with_risk(salle, patients)

    render_spacer("md")

    # File consultation
    render_section_header("Consultation Queue", "📋")
    queue = etat.get("queue_consultation", [])
    if queue:
        for i, pid in enumerate(queue[:5], 1):
            p = patients.get(pid, {})
            if p:
                render_queue_item_simple(i, p, st.session_state.state.current_time)
        if len(queue) > 5:
            st.caption(f"... et {len(queue) - 5} autres patients")
    else:
        st.success("✅ No patients waiting")

    render_spacer("xl")

    # ========== 5️⃣ RESOURCES ==========

    render_section_header("Resources", "👥")

    staff_data = etat.get("staff", [])
    medecins = [s for s in staff_data if s.get("type") == "médecin"]
    inf_mobiles = [s for s in staff_data if s.get("type") == "infirmier(ere)_mobile"]
    aides_soignants = [s for s in staff_data if s.get("type") == "aide_soignant"]

    # Vérifier si consultation occupée
    consultation_occupee = etat.get("consultation", {}).get("patient_id") is not None

    col1, col2, col3 = st.columns(3)
    with col1:
        render_staff_section_with_tension(
            "Médecins",
            "👨‍⚕️",
            medecins,
            1,
            is_medecin=True,
            consultation_occupee=consultation_occupee,
        )
    with col2:
        render_staff_section_with_tension("Inf. Mobiles", "🏃", inf_mobiles, 2)
    with col3:
        render_staff_section_with_tension("Aides-Soignants", "🤝", aides_soignants, 2)

    render_spacer("xl")

    # ========== 6️⃣ OPERATIONAL TIMELINE ==========

    render_section_header("Operational Timeline", "📋")
    render_operational_timeline(st.session_state.events)


with tab2:
    # st.markdown(get_chatbot_styles_v2(), unsafe_allow_html=True)

    st.markdown(
        """
    <div style="
        background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
        color: white;
        text-align: center;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin: 2rem 0;
        box-shadow: 0 4px 15px rgba(0, 102, 204, 0.3);
        border: 2px solid #0066CC;
    ">
        <div style="
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        ">
            🤖 Votre Assistant IA
        </div>
        <div style="
            font-size: 0.9rem;
            opacity: 0.9;
        ">
            Posez vos questions sur l'état du système d'urgences
        </div>
    </div>
""",
        unsafe_allow_html=True,
    )
    # st.markdown("## 🤖 AI Assistant")
    # st.caption("Posez vos questions sur l'état du système d'urgences")

    # Résumé système en haut
    if st.session_state.get("chatbot"):
        try:
            summary = st.session_state.get("chatbot").get_system_summary()  # ← ET ICI
            st.info(f"📊 {summary}")
        except:
            pass

    render_spacer("md")

    def handle_message(user_input):
        """Callback pour traiter un message utilisateur"""
        print(f" DEBUG: Message reçu: {user_input}")

        # Ajouter message utilisateur
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        print(
            f" DEBUG: Historique après user: {len(st.session_state.chat_history)} messages"
        )

        # Traiter avec chatbot
        if st.session_state.get("chatbot"):
            print(" DEBUG: Appel chatbot.process_message...")
            try:
                response = st.session_state.get("chatbot").process_message(user_input)
                print(f" DEBUG: Réponse reçue: {response.message[:50]}...")

                # Ajouter réponse
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": response.message,
                        "metadata": {
                            "guardrail_status": response.guardrail_status,
                            "guardrail_details": response.guardrail_details,
                            "rag_context": response.rag_context,
                            "actions_executed": response.actions_executed,
                            "latency_ms": response.latency_ms,
                        },
                    }
                )
                print(
                    f" DEBUG: Historique final: {len(st.session_state.chat_history)} messages"
                )
            except Exception as e:
                print(f"❌ DEBUG: Erreur chatbot : {e}")
                # Message d'erreur
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": f"❌ Erreur : {str(e)}",
                        "metadata": {},
                    }
                )
        else:
            print("❌ DEBUG: Chatbot non initialisé !")
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "❌ Chatbot non initialisé. Vérifiez la clé API Mistral.",
                    "metadata": {},
                }
            )

        st.rerun()

    render_chatbot_premium(
        chatbot_available=CHATBOT_AVAILABLE,
        chatbot_instance=st.session_state.get("chatbot"),
        chat_history=st.session_state.chat_history,
        on_message_callback=handle_message,
    )


# ========== TAB3 : MÉTRIQUES ==========
with tab3:
    render_section_header("Métriques LLM")
    # st.markdown("## Métriques LLM")
    st.caption("Suivi des performances, coûts et impact écologique des modèles d'IA")

    if not MONITORING_AVAILABLE or monitor is None:
        st.error("⚠️ Module monitoring non disponible. Vérifiez l'installation.")
    else:
        render_spacer("md")

        # Récupérer les statistiques
        stats = monitor.get_summary()
        global_stats = stats["global"]
        by_source = stats["by_source"]

        # ========== SECTION 1 : KPIs GLOBAUX ==========
        render_section_header("Vue Globale")
        # st.markdown("### Vue Globale")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            ">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem;">💰 Coût Total</div>
                <div style="font-size: 2rem; font-weight: 700; color: white;">${global_stats['total_cost']:.4f}</div>
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem;">{global_stats['total_requests']} requêtes</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);
            ">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem;">⚡ Énergie</div>
                <div style="font-size: 2rem; font-weight: 700; color: white;">{global_stats['total_energy_kwh']:.4f}</div>
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem;">kWh consommés</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
            ">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem;">🌍 CO2</div>
                <div style="font-size: 2rem; font-weight: 700; color: white;">{global_stats['total_co2_kg']*1000:.2f}</div>
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem;">g CO2eq</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(250, 112, 154, 0.3);
            ">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem;">⏱️ Latence Moy</div>
                <div style="font-size: 2rem; font-weight: 700; color: white;">{global_stats['avg_latency_ms']:.0f}</div>
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem;">ms / requête</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        render_spacer("xl")

        # ========== SECTION 2 : RÉPARTITION PAR SOURCE ==========
        render_section_header("Répartition par Composant")
        # st.markdown("###  Répartition par Composant")

        col1, col2 = st.columns(2)

        # Agent
        with col1:
            agent_stats = by_source.get("agent", {})
            agent_count = agent_stats.get("count", 0)
            agent_cost = agent_stats.get("cost", 0)
            agent_latency = agent_stats.get("latency", 0) / max(1, agent_count)

            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border-left: 4px solid #764ba2;
            ">
                <div style="font-size: 1.2rem; color: white; font-weight: 600; margin-bottom: 1rem;"> Agent</div>
                <div style="color: rgba(255,255,255,0.9);">
                    <div style="margin-bottom: 0.5rem;">📊 {agent_count} requêtes</div>
                    <div style="margin-bottom: 0.5rem;">💰 ${agent_cost:.4f}</div>
                    <div style="margin-bottom: 0.5rem;">⚡ {agent_stats.get('energy', 0):.4f} kWh</div>
                    <div style="margin-bottom: 0.5rem;">🌍 {agent_stats.get('co2', 0)*1000:.2f} g CO2</div>
                    <div>⏱️ {agent_latency:.0f} ms/req</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Chatbot
        with col2:
            chatbot_stats = by_source.get("chatbot", {})
            chatbot_count = chatbot_stats.get("count", 0)
            chatbot_cost = chatbot_stats.get("cost", 0)
            chatbot_latency = chatbot_stats.get("latency", 0) / max(1, chatbot_count)

            st.markdown(
                f"""
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 1.5rem;
                border-radius: 12px;
                border-left: 4px solid #f5576c;
            ">
                <div style="font-size: 1.2rem; color: white; font-weight: 600; margin-bottom: 1rem;"> Chatbot</div>
                <div style="color: rgba(255,255,255,0.9);">
                    <div style="margin-bottom: 0.5rem;">📊 {chatbot_count} requêtes</div>
                    <div style="margin-bottom: 0.5rem;">💰 ${chatbot_cost:.4f}</div>
                    <div style="margin-bottom: 0.5rem;">⚡ {chatbot_stats.get('energy', 0):.4f} kWh</div>
                    <div style="margin-bottom: 0.5rem;">🌍 {chatbot_stats.get('co2', 0)*1000:.2f} g CO2</div>
                    <div>⏱️ {chatbot_latency:.0f} ms/req</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # # RAG
        # with col3:
        #     rag_stats = by_source.get("rag", {})
        #     rag_count = rag_stats.get("count", 0)
        #     rag_cost = rag_stats.get("cost", 0)
        #     rag_latency = rag_stats.get("latency", 0) / max(1, rag_count)

        #     st.markdown(
        #         f"""
        #     <div style="
        #         background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        #         padding: 1.5rem;
        #         border-radius: 12px;
        #         border-left: 4px solid #00f2fe;
        #     ">
        #         <div style="font-size: 1.2rem; color: white; font-weight: 600; margin-bottom: 1rem;"> RAG</div>
        #         <div style="color: rgba(255,255,255,0.9);">
        #             <div style="margin-bottom: 0.5rem;">📊 {rag_count} requêtes</div>
        #             <div style="margin-bottom: 0.5rem;">💰 ${rag_cost:.4f}</div>
        #             <div style="margin-bottom: 0.5rem;">⚡ {rag_stats.get('energy', 0):.4f} kWh</div>
        #             <div style="margin-bottom: 0.5rem;">🌍 {rag_stats.get('co2', 0)*1000:.2f} g CO2</div>
        #             <div>⏱️ {rag_latency:.0f} ms/req</div>
        #         </div>
        #     </div>
        #     """,
        #         unsafe_allow_html=True,
        #     )

        render_spacer("xl")

        # ========== SECTION 3 : GRAPHIQUES ==========
        render_section_header("Visualisations", "📈")
        # st.markdown("### 📈 Visualisations")

        col1, col2 = st.columns(2)

        with col1:
            # Graphique en barres : Coût par source
            if any(
                by_source[s].get("count", 0) > 0 for s in ["agent", "chatbot", "rag"]
            ):
                st.markdown("**💰 Coût par Composant**")

                sources = ["Agent", "Chatbot", "RAG"]
                costs = [
                    by_source["agent"].get("cost", 0),
                    by_source["chatbot"].get("cost", 0),
                    by_source["rag"].get("cost", 0),
                ]

                import pandas as pd

                df_cost = pd.DataFrame({"Composant": sources, "Coût ($)": costs})

                # Bar chart personnalisé
                st.bar_chart(
                    df_cost.set_index("Composant"), height=300, use_container_width=True
                )
            else:
                st.info("📊 Aucune donnée disponible pour le moment")

        with col2:
            # Graphique en barres : Nombre de requêtes par source
            if any(
                by_source[s].get("count", 0) > 0 for s in ["agent", "chatbot", "rag"]
            ):
                st.markdown("**📊 Requêtes par Composant**")

                counts = [
                    by_source["agent"].get("count", 0),
                    by_source["chatbot"].get("count", 0),
                    by_source["rag"].get("count", 0),
                ]

                df_count = pd.DataFrame({"Composant": sources, "Requêtes": counts})
                st.bar_chart(
                    df_count.set_index("Composant"),
                    height=300,
                    use_container_width=True,
                )
            else:
                st.info("📊 Aucune donnée disponible pour le moment")

        render_spacer("xl")

        # # ========== SECTION 4 : HISTORIQUE RÉCENT ==========
        # st.markdown("### 📋 Historique Récent")

        # recent = monitor.get_recent_history(n=10)

        # if recent:
        #     # Tableau stylisé
        #     st.markdown(
        #         """
        #     <style>
        #     .metrics-table {
        #         width: 100%;
        #         border-collapse: collapse;
        #         background: white;
        #         border-radius: 8px;
        #         overflow: hidden;
        #         box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        #     }
        #     .metrics-table th {
        #         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        #         color: white;
        #         padding: 12px;
        #         text-align: left;
        #         font-weight: 600;
        #     }
        #     .metrics-table td {
        #         padding: 10px 12px;
        #         border-bottom: 1px solid #eee;
        #     }
        #     .metrics-table tr:hover {
        #         background: #f8f9ff;
        #     }
        #     </style>
        #     """,
        #         unsafe_allow_html=True,
        #     )

        #     table_html = """
        #     <table class="metrics-table">
        #         <thead>
        #             <tr>
        #                 <th>⏰ Timestamp</th>
        #                 <th>📦 Source</th>
        #                 <th>🤖 Modèle</th>
        #                 <th>📊 Tokens (in/out)</th>
        #                 <th>💰 Coût</th>
        #                 <th>⏱️ Latence</th>
        #             </tr>
        #         </thead>
        #         <tbody>
        #     """

        #     for req in reversed(recent):  # Plus récent en premier
        #         table_html += f"""
        #         <tr>
        #             <td>{req.timestamp.strftime("%H:%M:%S")}</td>
        #             <td><span style="background: {'#667eea' if req.source == 'agent' else '#f093fb' if req.source == 'chatbot' else '#4facfe'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem;">{req.source}</span></td>
        #             <td style="font-family: monospace; font-size: 0.85rem;">{req.model_name[:20]}...</td>
        #             <td>{req.input_tokens} / {req.output_tokens}</td>
        #             <td>${req.dollar_cost:.4f}</td>
        #             <td>{req.latency_ms:.0f} ms</td>
        #         </tr>
        #         """

        #     table_html += """
        #         </tbody>
        #     </table>
        #     """

        #     st.markdown(table_html, unsafe_allow_html=True)
        # else:
        #     st.info("📋 Aucune requête enregistrée pour le moment")

        render_spacer("md")

        # ========== SECTION 5 : ACTIONS ==========
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.rerun()

        with col2:
            if st.button("🗑️ Réinitialiser", use_container_width=True, type="secondary"):
                monitor.reset()
                st.success("✅ Métriques réinitialisées !")
                st.rerun()

        with col3:
            st.markdown(
                f"<div style='text-align: right; color: #666; font-size: 0.9rem; padding-top: 8px;'>📊 {global_stats['total_requests']} requêtes totales</div>",
                unsafe_allow_html=True,
            )

    # # Input manuel
    # col1, col2 = st.columns([4, 1])
    # with col1:
    #     test_input = st.text_input("Test :", key="test_chat")
    # with col2:
    #     if st.button("📤 Send"):
    #         if test_input:
    #             # Message user
    #             st.session_state.chat_history.append({
    #                 "role": "user",
    #                 "content": test_input
    #             })

    #             # Réponse bot (factice pour test)
    #             st.session_state.chat_history.append({
    #                 "role": "assistant",
    #                 "content": f"✅ Message reçu : '{test_input}'",
    #                 "metadata": {}
    #             })

    #             st.rerun()


# ========== CYCLE AGENT ==========

#
if st.session_state.running and st.session_state.agent_enabled:
    if st.session_state.agent is None:
        st.session_state.agent = EmergencyAgent(
            st.session_state.state, st.session_state.controller
        )
        st.session_state.agent_loaded = True

    st.session_state.temps += 1
    st.session_state.controller.tick(1)
    st.session_state.agent.state = st.session_state.state
    actions = st.session_state.agent.cycle_orchestration()

    # ✅ Enregistrer décisions pour le chatbot
    if actions:
        decision_record = {
            "timestamp": datetime.now(),
            "actions": actions,
            "raisonnement": f"{len(actions)} action(s) exécutée(s)",
            "temps_simulation": st.session_state.temps,
        }
        st.session_state.decision_history.append(decision_record)

        # Garder les 50 dernières
        if len(st.session_state.decision_history) > 50:
            st.session_state.decision_history = st.session_state.decision_history[-50:]

        # Mettre à jour chatbot
        if st.session_state.get("chatbot"):
            st.session_state.get("chatbot").set_decision_history(
                st.session_state.decision_history
            )

    for action in actions:
        if action:
            emoji = "🚑" if "transport" in action.lower() else "✅"
            if "📋" in action:
                emoji = "📋"
            add_event(action, emoji)

    time.sleep(st.session_state.agent_speed)
    st.rerun()
