"""
🏥 Emergency Dashboard avec Agent de Décision
==============================================
Version avec orchestration automatique des patients
"""

import os
# Augmenter le timeout HuggingFace AVANT tout import
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

import sys
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "mcp"))

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional  # ✅ Ajouté
import time
import random

# Imports
from mcp.state import EmergencyState, Patient, Gravite, UniteCible, StatutPatient, TypeStaff
from mcp.controllers.emergency_controller import EmergencyController
from rag.engine import HospitalRAGEngine
from monitoring.monitoring import monitor

# Import Chatbot
try:
    from chatbot.chatbot_engine import ChatbotEngine
    CHATBOT_AVAILABLE = True
except ImportError as e:
    CHATBOT_AVAILABLE = False
    print(f"Chatbot non disponible: {e}")

st.set_page_config(page_title="🏥 Emergency Dashboard + Agent", layout="wide")

# ========== SESSION STATE ==========

if 'state' not in st.session_state:
    st.session_state.state = EmergencyState()
    st.session_state.temps = 0
    st.session_state.running = False
    st.session_state.events = []
    st.session_state.temps = 0
    st.session_state.agent_enabled = True  # Agent activé par défaut
    st.session_state.agent_speed = 1.0  # Vitesse agent
    st.session_state.agent = None  # Agent sera chargé avec le RAG
    if 'controller' not in st.session_state:
            st.session_state.controller = EmergencyController(st.session_state.state)
    # Utilisation pour l'agent
    controller = st.session_state.controller

# Charger l'agent une seule fois au démarrage
if 'agent_loaded' not in st.session_state:
    st.session_state.agent_loaded = False

# Initialiser l'historique des decisions de l'agent
if 'decision_history' not in st.session_state:
    st.session_state.decision_history = []

# Initialiser le chatbot
if 'chatbot' not in st.session_state and CHATBOT_AVAILABLE:
    try:
        st.session_state.chatbot = ChatbotEngine(
            controller=st.session_state.controller,
            state=st.session_state.state,
            decision_history_ref=st.session_state.decision_history
        )
        st.session_state.chat_history = []
    except Exception as e:
        st.session_state.chatbot = None
        print(f"Erreur initialisation chatbot: {e}")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def add_event(msg, emoji="ℹ️"):
    st.session_state.events.append({
        "time": st.session_state.temps,
        "msg": msg,
        "emoji": emoji,
        
    })
    if len(st.session_state.events) > 30:
        st.session_state.events = st.session_state.events[-30:]

# ========== AGENT DE DÉCISION LLM ==========

import os
import json as json_module
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class EmergencyAgent:
    """
    Agent IA utilisant Mistral pour orchestrer les flux urgences.

    Cet agent fait de vrais appels LLM pour:
    - Décider quelle action entreprendre
    - Orienter les patients après consultation
    - Justifier ses décisions

    Les métriques (coût, latence, CO2) sont trackées automatiquement.
    """

    def __init__(self, state: EmergencyState, controller):
        self.state = state
        self.controller = controller
        self.rag_engine = HospitalRAGEngine(mode="simulation")

        # Initialisation du client Mistral
        self.mistral_client = None
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key:
            try:
                from mistralai import Mistral
                self.mistral_client = Mistral(api_key=api_key)
            except ImportError:
                pass

        # Compteur pour limiter les appels LLM (1 appel toutes les N itérations)
        self.iteration_count = 0
        self.llm_frequency = 5  # Appel LLM toutes les 5 itérations

    def cycle_orchestration(self) -> list[str]:
        """Exécute le cycle complet des opérations urgences."""
        actions = []
        self.iteration_count += 1

        # 1. FINALISATION des transports (toujours exécuté, pas besoin de LLM)
        actions.extend(self._finaliser_transports())

        # 2. Appel LLM pour décider des actions (toutes les N itérations)
        if self.mistral_client and self.iteration_count % self.llm_frequency == 0:
            llm_actions = self._decide_with_llm()
            actions.extend(llm_actions)
        else:
            # Mode règles simples entre les appels LLM
            actions.extend(self._gerer_surveillance())

            action_sortie = self._gerer_sortie_consultation_simple()
            if action_sortie:
                actions.append(action_sortie)

            action_trans = self._gerer_transport_unite_simple()
            if action_trans:
                actions.append(action_trans)

            action_consult = self._gerer_consultation_simple()
            if action_consult:
                actions.append(action_consult)

        return [a for a in actions if a is not None]

    def _decide_with_llm(self) -> list[str]:
        """Utilise Mistral pour décider des actions à entreprendre."""
        actions = []

        # Construire le contexte
        etat = self.state.to_dict()
        patients = etat.get("patients", {})
        patients_actifs = [p for p in patients.values() if p.get("statut") != "sorti"]

        # Résumé de l'état
        nb_attente = len([p for p in patients_actifs if p.get("statut") == "salle_attente"])
        nb_rouge = len([p for p in patients_actifs if p.get("gravite") == "ROUGE"])
        nb_jaune = len([p for p in patients_actifs if p.get("gravite") == "JAUNE"])
        consultation_libre = etat.get("consultation", {}).get("patient_id") is None
        patient_en_consultation = etat.get("consultation", {}).get("patient_id")

        staff_data = etat.get("staff", [])
        staff_dispo = len([s for s in staff_data if s.get("disponible") and not s.get("en_transport")])

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
                temperature=0.3
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Enregistrer les métriques
            if hasattr(response, 'usage') and response.usage:
                monitor.log_metrics_simple(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    model_name="ministral-3b-2512",
                    source="agent"
                )

            # Parser la réponse
            response_text = response.choices[0].message.content.strip()

            # Nettoyer le JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            decision = json_module.loads(response_text)
            action_type = decision.get("action", "ATTENDRE")
            patient_id = decision.get("patient_id")
            destination = decision.get("destination")
            justification = decision.get("justification", "")

            # Exécuter l'action décidée
            if action_type == "TRANSPORT_CONSULTATION" and patient_id:
                staff_dispo_list = [s for s in self.state.staff
                                   if s.disponible and not s.en_transport
                                   and s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]]
                if staff_dispo_list and self.state.consultation.est_libre():
                    res = self.controller.demarrer_transport_consultation(patient_id, staff_dispo_list[0].id)
                    if res.get("success"):
                        actions.append(f"🤖 LLM: {patient_id} → consultation ({justification})")

            elif action_type == "TERMINER_CONSULTATION" and patient_id:
                dest_map = {"MAISON": UniteCible.MAISON, "CARDIO": UniteCible.CARDIO,
                           "CHIRURGIE": UniteCible.CHIRURGIE, "REA": UniteCible.REA}
                dest = dest_map.get(destination, UniteCible.MAISON)
                res = self.controller.terminer_consultation(patient_id, dest)
                if res.get("success"):
                    actions.append(f"🤖 LLM: Consultation terminée → {destination} ({justification})")

            elif action_type == "TRANSPORT_UNITE" and patient_id:
                staff_dispo_list = [s for s in self.state.staff
                                   if s.disponible and not s.en_transport
                                   and s.type == TypeStaff.AIDE_SOIGNANT]
                if staff_dispo_list:
                    res = self.controller.demarrer_transport_unite(patient_id, staff_dispo_list[0].id)
                    if res.get("success"):
                        actions.append(f"🤖 LLM: {patient_id} → unité ({justification})")

            elif action_type == "SURVEILLANCE":
                actions.extend(self._gerer_surveillance())
                if actions:
                    actions[-1] = f"🤖 LLM: Surveillance ({justification})"

            else:
                actions.append(f"🤖 LLM: Attente ({justification})")

        except Exception as e:
            actions.append(f"⚠️ Erreur LLM: {str(e)[:50]}")

        return actions

    def _finaliser_transports(self) -> list[str]:
        """Vérifie si les transports sont arrivés et libère le personnel."""
        actions = []
        for staff in self.state.staff:
            if staff.en_transport and staff.fin_transport_prevue:
                if self.state.current_time >= staff.fin_transport_prevue:
                    pid = staff.patient_transporte_id
                    if staff.destination_transport == "consultation":
                        self.controller.finaliser_transport_consultation(pid)
                        actions.append(f"✅ Arrivée en consultation : {pid}")
                    else:
                        self.controller.finaliser_transport_unite(pid)
                        p = self.state.patients.get(pid)
                        actions.append(f"🏁 {p.prenom if p else pid} arrivé en unité")
        return actions

    def _gerer_surveillance(self) -> list[str]:
        """Assure la ronde de surveillance toutes les 15 min."""
        actions = []
        staff_dispo = self.state.get_staff_disponible(TypeStaff.INFIRMIERE_MOBILE) + \
                      self.state.get_staff_disponible(TypeStaff.AIDE_SOIGNANT)

        for salle in self.state.salles_attente:
            if salle.temps_sans_surveillance(self.state.current_time) > 10 and len(salle.patients) > 0:
                en_poste = any(s.salle_surveillee == salle.id and not s.en_transport for s in self.state.staff)
                if not en_poste and staff_dispo:
                    agent = staff_dispo.pop(0)
                    res = self.controller.assigner_surveillance(agent.id, salle.id)
                    if res.get("success"):
                        actions.append(f"📋 {agent.id} affecté à {salle.id}")
        return actions

    def _gerer_sortie_consultation_simple(self) -> Optional[str]:
        """Version simple de la gestion de sortie (entre les appels LLM)."""
        if self.state.consultation.est_libre():
            return None

        pid = self.state.consultation.patient_id
        patient = self.state.patients.get(pid)
        if not patient:
            return None

        debut = self.state.consultation.debut_consultation
        if not debut:
            return None
        duree_ecoulee = (self.state.current_time - debut).total_seconds() / 60
        duree_min = 10 if patient.gravite == Gravite.VERT else 20

        if duree_ecoulee >= duree_min:
            destination = UniteCible.MAISON if patient.gravite in [Gravite.VERT, Gravite.GRIS] else UniteCible.CARDIO
            res = self.controller.terminer_consultation(pid, destination)
            if res.get("success"):
                return f"✅ {patient.prenom} → {destination}"
        return None

    def _gerer_transport_unite_simple(self) -> Optional[str]:
        """Version simple du transport unité."""
        queue = self.state.get_queue_transport_sortie()
        if not queue:
            return None

        p = queue[0]
        staff_mobiles = [s for s in self.state.staff if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]
        as_dispo = [s for s in staff_dispo if s.type == TypeStaff.AIDE_SOIGNANT]

        if as_dispo and len(staff_dispo) >= 3:
            res = self.controller.demarrer_transport_unite(p.id, as_dispo[0].id)
            if res.get("success"):
                return f"🚑 {p.prenom} → {p.unite_cible}"
        return None

    def _gerer_consultation_simple(self) -> Optional[str]:
        """Version simple de la gestion consultation."""
        if not self.state.consultation.est_libre():
            return None

        staff_mobiles = [s for s in self.state.staff if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]

        if len(staff_dispo) < 2:
            return None

        queue = self.state.get_queue_consultation()
        if queue and staff_dispo:
            res = self.controller.demarrer_transport_consultation(queue[0].id, staff_dispo[0].id)
            if res.get("success"):
                return f"🚑 {queue[0].prenom} → consultation"
        return None
# ========== FONCTIONS UTILITAIRES ==========

def get_state():
    return st.session_state.state.to_dict()

def gen_patient():
    noms = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Petit"]
    prenoms = ["Sophie", "Lucas", "Emma", "Thomas", "Léa", "Hugo"]
    gravites = [Gravite.ROUGE, Gravite.JAUNE, Gravite.VERT]
    g = random.choices(gravites, weights=[0.2, 0.3, 0.5])[0]
    
    symptomes = {
        Gravite.ROUGE: ["Douleur thoracique", "AVC suspecté", "Détresse respiratoire"],
        Gravite.JAUNE: ["Fracture du bras", "Forte fièvre", "Plaie profonde"],
        Gravite.VERT: ["Migraine", "Petite plaie", "Légère foulure"]
    }
    
    return {
        "id": f"P{random.randint(1000,9999)}",
        "prenom": random.choice(prenoms),
        "nom": random.choice(noms),
        "gravite": g,
        "symptomes": random.choice(symptomes[g]),
        "age": random.randint(20, 80),
        "antecedents": []
    }

def add_patient(data):
    controller = st.session_state.controller
    p = Patient(**data)

    r = controller.ajouter_patient(p)

    if r and r.get("success"):
        salle_result = controller.assigner_salle_attente(p.id)
        if salle_result.get("success"):
            add_event(f"Patient {p.id} ({p.prenom}) assigné à {salle_result.get('salle_id')}", "🏥")
        else:
            add_event(f"⚠️ {p.prenom} : {salle_result.get('error')}", "⚠️")

    return r





# ========== SIDEBAR ==========

with st.sidebar:
    st.title("🏥 Emergency Dashboard")
    st.caption("avec Agent de Décision")
    
    st.divider()
    
    # Temps simulé
    st.metric("⏰ Temps", f"{st.session_state.temps//60:02d}h{st.session_state.temps%60:02d}")
    
    # Contrôles simulation
    st.subheader("🎮 Simulation")
    
    col1, col2 = st.columns(2)
    if col1.button("▶️" if not st.session_state.running else "⏸️", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
    
    if col2.button("🔄 Reset", use_container_width=True):
        st.session_state.state = EmergencyState()
        st.session_state.temps = 0
        st.session_state.events = []
        st.session_state.agent_loaded = False
        st.session_state.agent = None
        add_event("Système réinitialisé", "✅")
        time.sleep(0.5)
        st.rerun()
    
    # Contrôle agent
    st.divider()
    st.subheader("🤖 Agent")
    
    st.session_state.agent_enabled = st.checkbox(
        "Activer l'agent",
        value=st.session_state.agent_enabled,
        help="L'agent prend des décisions automatiquement"
    )
    
    if st.session_state.agent_enabled:
        st.success("✅ Agent actif")
        
        speed_options = {
            "🐌 Lent (2s)": 2.0,
            "⚡ Normal (1s)": 1.0,
            "🚀 Rapide (0.5s)": 0.5,
            "💨 Ultra (0.2s)": 0.2
        }
        
        speed_label = st.select_slider(
            "Vitesse agent",
            options=list(speed_options.keys()),
            value="⚡ Normal (1s)"
        )
        st.session_state.agent_speed = speed_options[speed_label]
    else:
        st.info("⏸️ Agent désactivé")
    
    st.divider()
    
    # Actions rapides
    st.subheader("➕ Actions")
    
    if st.button("👤 +1 Patient", use_container_width=True):
        p = gen_patient()
        r = add_patient(p)
        if r.get("success"):
            emoji_map = {Gravite.ROUGE: "🔴", Gravite.JAUNE: "🟡", Gravite.VERT: "🟢"}
            add_event( f"{p['id']} ({p['prenom']} {p['nom']}) ajouté", emoji_map.get(p['gravite'], "👤"))
            st.success(f"✅ {p['prenom']} ajouté")
        time.sleep(0.3)
        st.rerun()
    
    if st.button("👥 +5 Patients", use_container_width=True):
        count = 0
        for _ in range(5):
            if add_patient(gen_patient()).get("success"):
                count += 1
        add_event(f"{count}/5 patients ajoutés", "👥")
        st.success(f"✅ {count}/5 ajoutés")
        time.sleep(0.3)
        st.rerun()
    
    if st.button("🚨 Afflux (15)", use_container_width=True):
        gravites = [Gravite.ROUGE] * 3 + [Gravite.JAUNE] * 5 + [Gravite.VERT] * 7
        count = 0
        for g in gravites:
            p = gen_patient()
            p["gravite"] = g
            if add_patient(p).get("success"):
                count += 1
        add_event(f"Afflux: {count} patients", "🚨")
        st.warning(f"⚠️ {count} patients ajoutés")
        time.sleep(0.5)
        st.rerun()
    
    st.divider()
    
    # Stats agent
    if st.session_state.agent_enabled:
        st.subheader("📊 Statistiques Agent")
        nb_actions = len([e for e in st.session_state.events if e['emoji'] in ['🚑', '✅', '🏥']])
        st.metric("Actions prises", nb_actions)

# ========== MAIN ==========

st.title("🏥 Emergency Management")

# Structure en onglets
tab_simulation, tab_chatbot, tab_monitoring = st.tabs(["📊 Simulation", "💬 Chatbot", "📈 Monitoring"])

# ========== ONGLET SIMULATION ==========
with tab_simulation:
    etat = get_state()

    # Alertes
    alertes = etat.get("alertes_surveillance", [])
    if alertes:
        for alerte in alertes:
            st.error(alerte)

    # ========== BANDEAU PERSONNEL ==========
    st.subheader("👨‍⚕️ Suivi du Personnel")

    staff_data = etat.get("staff", [])

    medecins = [s for s in staff_data if s.get("type") == "médecin"]
    inf_fixes = [s for s in staff_data if s.get("type") == "infirmier(ere)_fixe"]
    inf_mobiles = [s for s in staff_data if s.get("type") == "infirmier(ere)_mobile"]
    aides_soignants = [s for s in staff_data if s.get("type") == "aide_soignant"]
    # Metric
    patients = etat.get("patients", {})
    nb_total = len([p for p in patients.values() if p.get("statut") != "sorti"])
    nb_attente = len([p for p in patients.values() if p.get("statut") == "salle_attente"])

    # Définition de la variable manquante
    nb_consultation = 1 if etat.get("consultation", {}).get("patient_id") else 0

    nb_en_transport = len([p for p in patients.values() if "transport" in p.get("statut", "")])
    col_med, col_if, col_im, col_as = st.columns(4)

    with col_med:
        st.markdown("**👨‍⚕️ Médecins**")
        medecin_data = next((s for s in staff_data if s.get("type") == "médecin"), None)
        patient_en_consultation = etat.get("consultation", {}).get("patient_id")
        if medecin_data:
            if patient_en_consultation:
                st.caption(
                    f"🔴 {medecin_data.get('id')} — en consultation avec "
                    f"`{patient_en_consultation}`")
            else:
                st.caption(f"🟢 {medecin_data.get('id')} — libre")

    with col_if:
        st.markdown("**💉 Inf. Fixes**")
        for staff in inf_fixes:
            loc = staff.get("localisation", "Triage")
            st.caption(f"📍 {staff.get('id')}: {loc}")

    with col_im:
        st.markdown("**🏃 Inf. Mobiles**")
        for staff in inf_mobiles:
            if staff.get("en_transport"):
                status_text = f"🚑 Transport {staff.get('patient_transporte_id')}"
            elif staff.get("salle_surveillee"):
                status_text = f"📋 Surveillance {staff.get('salle_surveillee')}"
            else:
                status_text = "⏳ En attente de mission"
            dispo = "🟢" if staff.get("disponible") else "🔴"
            st.caption(f"{dispo} {staff.get('id')}: {status_text}")

    with col_as:
        st.markdown("**🤝 Aides-Soignants**")
        for staff in aides_soignants:
            if staff.get("en_transport"):
                status_text = f"🚑 Transport {staff.get('patient_transporte_id')}"
            elif staff.get("salle_surveillee"):
                status_text = f"📋 Surveillance {staff.get('salle_surveillee')}"
            else:
                status_text = "⏳ En attente de mission"
            temps_restant = staff.get("temps_disponible_restant")
            timer = f" ⏱️ {temps_restant}min" if temps_restant and temps_restant > 0 else ""
            dispo = "🟢" if staff.get("disponible") else "🔴"
            st.caption(f"{dispo} {staff.get('id')}: {status_text}{timer}")

    st.divider()

    # Métriques
    col1, col2, col3, col4, col5 = st.columns(5)

    patients = etat.get("patients", {})
    nb_total = len([p for p in patients.values() if p.get("statut") != "sorti"])
    nb_attente = len([p for p in patients.values() if p.get("statut") == "salle_attente"])
    nb_consultation = 1 if etat.get("consultation", {}).get("patient_id") else 0
    nb_en_transport = len([p for p in patients.values() if "transport" in p.get("statut", "")])

    col1.metric("👥 Total", nb_total)
    col2.metric("⏳ Attente", nb_attente)
    col3.metric("👨‍⚕️ Consultation", nb_consultation)
    col4.metric("🚑 Transport", nb_en_transport)

    salles = etat.get("salles_attente", [])
    cap = sum(s.get("capacite", 0) for s in salles)
    occ = sum(len(s.get("patients", [])) for s in salles)
    col5.metric("📊 Saturation", f"{int(occ/cap*100) if cap else 0}%")

    st.divider()

    # Layout principal
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Salles
        st.subheader("🏥 Salles d'Attente")
        for salle in salles:
            num = salle.get("id","").split("_")[-1]
            pts = salle.get("patients", [])
            cap_s = salle.get("capacite", 0)

            emojis = []
            for pid in pts:
                p = patients.get(pid, {})
                g = p.get("gravite", "GRIS")
                emojis.append({"ROUGE":"🔴","JAUNE":"🟡","VERT":"🟢","GRIS":"⚪"}.get(g,"❓"))

            emojis += ["◻️"] * (cap_s - len(pts))

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Salle {num}** ({len(pts)}/{cap_s}): {' '.join(emojis)}")
            with col2:
                taux = int(len(pts)/cap_s*100) if cap_s > 0 else 0
                st.progress(taux/100, text=f"{taux}%")

        st.divider()

        # File attente
        st.subheader("📋 File d'Attente Consultation")
        queue = etat.get("queue_consultation", [])
        if queue:
            for i, pid in enumerate(queue[:5], 1):
                p = patients.get(pid, {})
                g = p.get("gravite", "GRIS")
                emoji = {"ROUGE":"🔴","JAUNE":"🟡","VERT":"🟢","GRIS":"⚪"}.get(g,"❓")

                try:
                    arr = datetime.fromisoformat(p.get("arrived_at", ""))
                    now_sim = st.session_state.state.current_time
                    temps = int((now_sim - arr).total_seconds() / 60)
                except:
                    temps = 0

                exc = " ⚠️ **>360min!**" if temps > 360 and g == "VERT" else ""
                st.write(f"{i}. {emoji} **{p.get('prenom')} {p.get('nom')}** (`{pid}`) - {temps}min{exc}")

            if len(queue) > 5:
                st.caption(f"... et {len(queue) - 5} autres")
        else:
            st.success("✅ Aucun patient en attente")

        # File transport
        queue_transport = etat.get("queue_transport", [])
        if queue_transport:
            st.divider()
            st.subheader("🚑 File Attente Transport")
            for i, pid in enumerate(queue_transport[:3], 1):
                p = patients.get(pid, {})
                unite = p.get("unite_cible", "N/A")
                st.write(f"{i}. {p.get('prenom')} {p.get('nom')} → {unite}")

    with col_right:
        st.subheader("📋 Log Événements")
        if st.session_state.events:
            with st.container(height=600):
                for evt in reversed(st.session_state.events[-15:]):
                    st.text(f"[T+{evt['time']:03d}] {evt['emoji']} {evt['msg']}")
        else:
            st.info("Aucun événement")

    with st.sidebar:
        st.divider()
        st.subheader("📊 Métriques IA (Cumulées)")

        # Métriques globales
        col1, col2 = st.columns(2)
        col1.metric("💵 Coût ($)", f"{monitor.total_dollar_cost:.4f}")
        col2.metric("⚡ Énergie (kWh)", f"{monitor.total_energy_kwh:.6f}")

        col3, col4 = st.columns(2)
        col3.metric("🌍 CO2 (kg)", f"{monitor.total_co2_kg:.6f}")
        avg_latency = monitor.get_average_latency()
        col4.metric("⏱️ Latence (ms)", f"{avg_latency:.0f}")

        # Compteur de requêtes
        st.caption(f"📈 Total requêtes: {monitor.request_count}")

        # Bouton reset des métriques
        if st.button("🔄 Reset métriques", use_container_width=True):
            monitor.reset()
            st.success("Métriques réinitialisées")
            time.sleep(0.3)
            st.rerun()

# ========== ONGLET CHATBOT ==========
with tab_chatbot:
    st.subheader("💬 Assistant Urgences")

    if not CHATBOT_AVAILABLE:
        st.error("Module chatbot non disponible. Verifiez l'installation.")
    elif st.session_state.get('chatbot') is None:
        st.warning("Chatbot non initialise. Cle API Mistral manquante?")
    else:
        # Afficher le resume systeme
        chatbot = st.session_state.chatbot
        summary = chatbot.get_system_summary()
        st.caption(f"Etat: {summary}")

        st.divider()

        # Afficher l'historique des messages
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # Afficher les metadonnees pour les messages du bot
                if msg["role"] == "assistant" and msg.get("metadata"):
                    meta = msg["metadata"]

                    # Status guardrail
                    if meta.get("guardrail_status") == "blocked":
                        st.error(f"Bloque: {meta.get('guardrail_details')}")

                    # Contexte RAG
                    if meta.get("rag_context"):
                        with st.expander("📚 Contexte RAG"):
                            ctx = meta["rag_context"]
                            if ctx.get("protocol"):
                                st.write(f"**Protocole:** {ctx['protocol'].get('pathologie')}")
                                st.write(f"**Gravite:** {ctx['protocol'].get('gravite')}")
                            if ctx.get("rules"):
                                st.write(f"**Regles:** {', '.join(ctx['rules'][:3])}")
                            st.write(f"*Score: {ctx.get('relevance_score', 0):.2f}*")

                    # Actions executees
                    if meta.get("actions_executed"):
                        with st.expander("⚡ Actions executees"):
                            for action in meta["actions_executed"]:
                                status = "✅" if action.get("success") else "❌"
                                st.write(f"{status} {action.get('tool')}")

                    # Latence
                    st.caption(f"Latence: {meta.get('latency_ms', 0):.0f}ms")

        # Input utilisateur
        if prompt := st.chat_input("Posez votre question ou donnez une commande..."):
            # Ajouter message utilisateur
            st.session_state.chat_history.append({
                "role": "user",
                "content": prompt
            })

            # Traiter avec le chatbot
            with st.spinner("Traitement en cours..."):
                response = chatbot.process_message(prompt)

            # Ajouter reponse du bot
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response.message,
                "metadata": {
                    "guardrail_status": response.guardrail_status,
                    "guardrail_details": response.guardrail_details,
                    "rag_context": response.rag_context,
                    "actions_executed": response.actions_executed,
                    "latency_ms": response.latency_ms
                }
            })

            st.rerun()

        # Boutons d'actions rapides
        st.divider()
        st.caption("Actions rapides:")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("📊 Etat systeme", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "Quel est l'etat du systeme?"
                })
                st.rerun()

        with col2:
            if st.button("👥 Liste patients", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "Liste les patients"
                })
                st.rerun()

        with col3:
            if st.button("➕ Ajouter patient", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "Ajoute 1 patient jaune avec douleur abdominale"
                })
                st.rerun()

        with col4:
            if st.button("🤖 Derniere decision", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": "Explique la derniere decision de l'agent"
                })
                st.rerun()

        # Bouton effacer conversation
        if st.button("🗑️ Effacer conversation"):
            st.session_state.chat_history = []
            if chatbot:
                chatbot.clear_conversation()
            st.rerun()

# ========== ONGLET MONITORING ==========
with tab_monitoring:
    st.subheader("📈 Monitoring des Métriques IA")
    st.caption("Suivi en temps réel du coût, de la latence et de l'impact écologique")

    # Métriques globales en cartes
    st.markdown("### 📋 Métriques Globales")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="💵 Coût Total",
            value=f"${monitor.total_dollar_cost:.4f}",
            help="Coût simulé basé sur les tarifs Mistral AI"
        )
    with col2:
        st.metric(
            label="⚡ Énergie Consommée",
            value=f"{monitor.total_energy_kwh:.6f} kWh",
            help="Consommation énergétique estimée pour l'inférence GPU"
        )
    with col3:
        st.metric(
            label="🌍 Empreinte CO2",
            value=f"{monitor.total_co2_kg:.6f} kg",
            help="Potentiel de réchauffement global (kgCO2eq) - Mix France"
        )
    with col4:
        avg_latency = monitor.get_average_latency()
        st.metric(
            label="⏱️ Latence Moyenne",
            value=f"{avg_latency:.0f} ms",
            help="Temps de réponse moyen des requêtes LLM"
        )

    st.divider()

    # Breakdown par composant
    st.markdown("### 📊 Détail par Composant")

    col_agent, col_chatbot, col_rag = st.columns(3)

    with col_agent:
        st.markdown("#### 🤖 Agent")
        agent_stats = monitor.by_source.get("agent", {})
        agent_count = agent_stats.get("count", 0)
        st.metric("Requêtes", agent_count)
        if agent_count > 0:
            st.caption(f"💵 ${agent_stats.get('cost', 0):.4f}")
            st.caption(f"⚡ {agent_stats.get('energy', 0):.6f} kWh")
            st.caption(f"🌍 {agent_stats.get('co2', 0):.6f} kg CO2")
            avg_lat = agent_stats.get('latency', 0) / max(1, agent_count)
            st.caption(f"⏱️ {avg_lat:.0f} ms (moy)")
        else:
            st.caption("Aucune requête")

    with col_chatbot:
        st.markdown("#### 💬 Chatbot")
        chat_stats = monitor.by_source.get("chatbot", {})
        chat_count = chat_stats.get("count", 0)
        st.metric("Requêtes", chat_count)
        if chat_count > 0:
            st.caption(f"💵 ${chat_stats.get('cost', 0):.4f}")
            st.caption(f"⚡ {chat_stats.get('energy', 0):.6f} kWh")
            st.caption(f"🌍 {chat_stats.get('co2', 0):.6f} kg CO2")
            avg_lat = chat_stats.get('latency', 0) / max(1, chat_count)
            st.caption(f"⏱️ {avg_lat:.0f} ms (moy)")
        else:
            st.caption("Aucune requête")

    st.divider()

    # Historique des requêtes
    st.markdown("### 📜 Historique des Requêtes")

    recent = monitor.get_recent_history(10)
    if recent:
        for req in reversed(recent):
            source_emoji = {"agent": "🤖", "chatbot": "💬"}.get(req.source, "❓")
            time_str = req.timestamp.strftime("%H:%M:%S")
            st.markdown(
                f"**{source_emoji} {req.source.upper()}** | "
                f"`{time_str}` | "
                f"💵 ${req.dollar_cost:.5f} | "
                f"⏱️ {req.latency_ms:.0f}ms | "
                f"📝 {req.input_tokens}→{req.output_tokens} tokens"
            )
    else:
        st.info("Aucune requête enregistrée. Utilisez le chatbot ou activez l'agent pour générer des métriques.")

    st.divider()

    # Informations sur les tarifs
    with st.expander("💰 Tarification des modèles ($/1M tokens)"):
        st.markdown("""
        | Modèle | Input | Output |
        |--------|-------|--------|
        | ministral-3b-2512 | $0.10 | $0.10 |
        | ministral-8b-latest | $0.10 | $0.10 | 
        | mistral-small-latest | $0.20 | $0.60 |
        | mistral-large-latest | $0.50 | $1.50 |

        *Source: [Mistral AI](https://mistral.ai/fr/technology/)*
        """)

    with st.expander("🌱 Méthodologie Impact Écologique"):
        st.markdown("""
        **Énergie (kWh):**
        - Estimation basée sur la consommation GPU pour l'inférence
        - Approximation: ~0.0002 kWh par 1000 tokens

        **CO2 (kgCO2eq):**
        - Basé sur le mix électrique français (RTE)
        - Facteur: ~0.052 kgCO2eq/kWh

        *Méthodologie: [EcoLogits](https://ecologits.ai/latest/methodology/llm_inference/)*
        """)

    # Actions
    col_action1, col_action2 = st.columns(2)
    with col_action1:
        if st.button("🔄 Réinitialiser toutes les métriques", use_container_width=True):
            monitor.reset()
            st.success("✅ Métriques réinitialisées")
            time.sleep(0.5)
            st.rerun()

    with col_action2:
        summary = monitor.get_summary()
        st.download_button(
            label="📥 Exporter le résumé (JSON)",
            data=str(summary),
            file_name="monitoring_summary.json",
            mime="application/json",
            use_container_width=True
        )

# ========== CYCLE AGENT ==========

if st.session_state.running and st.session_state.agent_enabled:
    
    # ÉTAPE A : Créer l'agent s'il n'existe pas ENCORE
    if st.session_state.agent is None:
        st.session_state.agent = EmergencyAgent( st.session_state.state, st.session_state.controller)
        st.session_state.agent_loaded = True

    # ÉTAPE B : Faire avancer le temps
    st.session_state.temps += 1
    st.session_state.controller.tick(1)

    # ÉTAPE C : Donner l'état à l'agent (Maintenant il n'est plus None)
    st.session_state.agent.state = st.session_state.state
    
    # ÉTAPE D : Lancer les décisions
    actions = st.session_state.agent.cycle_orchestration()

    # ÉTAPE E : Enregistrer dans l'historique des décisions (pour le chatbot)
    if actions:
        decision_record = {
            "timestamp": datetime.now(),
            "actions": actions,
            "raisonnement": f"{len(actions)} action(s) executee(s)",
            "temps_simulation": st.session_state.temps
        }
        st.session_state.decision_history.append(decision_record)
        # Garder les 50 dernieres decisions
        if len(st.session_state.decision_history) > 50:
            st.session_state.decision_history = st.session_state.decision_history[-50:]

        # Mettre a jour la reference dans le chatbot
        if st.session_state.get('chatbot'):
            st.session_state.chatbot.set_decision_history(st.session_state.decision_history)

    for action in actions:
        if action:
            # Choix de l'emoji selon l'action
            emoji = "🚑" if "transport" in action.lower() else "✅"
            if "📋" in action: emoji = "📋"
            add_event(action, emoji)

    time.sleep(st.session_state.agent_speed)
    st.rerun()