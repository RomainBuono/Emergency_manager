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
import time
import random

# Imports
from mcp.state import EmergencyState, Patient, Gravite, UniteCible, StatutPatient, TypeStaff
import mcp.tools as tools
from rag.engine import HospitalRAGEngine

st.set_page_config(page_title="🏥 Emergency Dashboard + Agent", layout="wide")

# ========== SESSION STATE ==========

if 'state' not in st.session_state:
    st.session_state.state = EmergencyState()
    st.session_state.temps = 0
    st.session_state.running = False
    st.session_state.events = []
    st.session_state.agent_enabled = True  # Agent activé par défaut
    st.session_state.agent_speed = 1.0  # Vitesse agent
    st.session_state.agent = None  # Agent sera chargé avec le RAG

# Charger l'agent une seule fois au démarrage
if 'agent_loaded' not in st.session_state:
    st.session_state.agent_loaded = False

def add_event(msg, emoji="ℹ️"):
    st.session_state.events.append({
        "time": st.session_state.temps,
        "msg": msg,
        "emoji": emoji
    })
    if len(st.session_state.events) > 30:
        st.session_state.events = st.session_state.events[-30:]

# ========== AGENT DE DÉCISION ==========

class EmergencyAgent:
    """Agent qui orchestre automatiquement les patients"""
    
    def __init__(self, state: EmergencyState):
        self.state = state
        # Mode simulation : rapide, sans ML, avec cache embeddings
        self.rag_engine = HospitalRAGEngine(mode="simulation")
    
    def cycle_orchestration(self) -> list[str]:
        """Exécute un cycle complet d'orchestration"""
        actions = []
        
        actions.extend(self._finaliser_transports())
        # 1. Vérifier si un patient peut aller en consultation
        action = self._gerer_consultation()
        if action:
            actions.append(action)
        
        # 2. Vérifier si un patient en consultation peut sortir
        action = self._gerer_sortie_consultation()
        if action:
            actions.append(action)
        
        # 3. Vérifier si un patient peut être transporté vers une unité
        action = self._gerer_transport_unite()
        if action:
            actions.append(action)
        
        # 4. Vérifier surveillance des salles
        alertes = self._verifier_surveillance()
        actions.extend(alertes)
        
        return actions
    
    def _gerer_consultation(self) -> str:
        """Gère l'entrée en consultation"""
        # Si consultation occupée, rien à faire
        if not self.state.consultation.est_libre():
            return None
        
        # Récupérer le prochain patient
        queue = self.state.get_queue_consultation()
        if not queue:
            return None
        
        prochain = queue[0]
        
        # Vérifier si un aide-soignant est disponible
        aides_dispo = self.state.get_staff_disponible(TypeStaff.AIDE_SOIGNANT)
        if not aides_dispo:
            return None
        
        aide = aides_dispo[0]
        
        # Démarrer le transport
        result = tools.demarrer_transport_consultation(
            self.state, 
            prochain.id, 
            aide.id
        )
        
        if result.get("success"):
            return f"🚑 {prochain.prenom} {prochain.nom} transporté en consultation"
        
        return None
    
    def _gerer_sortie_consultation(self) -> str:
        """Gère la fin de consultation (décision via la RAG)."""
        if self.state.consultation.est_libre():
            return None

        patient_id = self.state.consultation.patient_id
        patient = self.state.patients.get(patient_id)
        if not patient:
            return None

        # Marquer la fin de consultation (simulation instantanée)
        if not patient.consultation_end_at:
            patient.consultation_end_at = self.state.current_time
            return None

        # Décision via la RAG
        try:
            wait_time = patient.temps_attente_minutes(self.state.current_time)
        except Exception:
            wait_time = 0

        try:
            rag_result = self.rag_engine.query(
                patient.symptomes,
                wait_time=wait_time
            )
        except Exception:
            rag_result = None

        unite_cible = UniteCible.MAISON

        if rag_result and getattr(rag_result, "is_safe", False) and getattr(rag_result, "protocol", None):
            protocol = rag_result.protocol

            try:
                unite_cible = UniteCible(protocol.unite_cible)
            except Exception:
                unite_cible = UniteCible.MAISON

            try:
                patient.gravite = Gravite(protocol.gravite)
            except Exception:
                pass

        result = tools.terminer_consultation(
            self.state,
            patient.id,
            unite_cible
        )

        if result.get("success"):
            return f"Consultation en cours: {patient.prenom} {patient.nom}"

        return None


    
    def _gerer_transport_unite(self) -> str:
        """Gère le transport vers les unités"""
        queue_transport = self.state.get_queue_transport_sortie()
        if not queue_transport:
            return None
        
        prochain = queue_transport[0]
        
        # Vérifier si l'unité a de la place
        unite = self.state.get_unite(prochain.unite_cible)
        if not unite or not unite.a_de_la_place():
            return f"⚠️ Unité {prochain.unite_cible} saturée"
        
        # Vérifier si un aide-soignant est disponible
        aides_dispo = self.state.get_staff_disponible(TypeStaff.AIDE_SOIGNANT)
        if not aides_dispo:
            return None
        
        aide = aides_dispo[0]
        
        # Démarrer le transport
        result = tools.demarrer_transport_unite(
            self.state,
            prochain.id,
            aide.id
        )
        
        if result.get("success"):
            # Simuler l'arrivée
            return f"🏥 {prochain.prenom} transporté vers {prochain.unite_cible}"
        
        return None
    def _finaliser_transports(self) -> list[str]:
        # ✅ déléguer au moteur temps unique
        r = tools.tick(self.state, minutes=0)  # minutes=0 si tu avances le temps ailleurs
        return r.get("events", [])

    def _verifier_surveillance(self) -> list[str]:
        """Vérifie la surveillance des salles"""
        alertes = []
        surveillance_alerts = self.state.verifier_surveillance_salles()
        
        for alert in surveillance_alerts:
            alertes.append(f"⚠️ {alert}")
        
        return alertes

# Charger l'agent UNE SEULE FOIS avec indicateur de progression
if not st.session_state.agent_loaded:
    with st.spinner("🔄 Chargement du moteur RAG et de l'agent (première fois seulement)..."):
        st.session_state.agent = EmergencyAgent(st.session_state.state)
        st.session_state.agent_loaded = True
        st.success("✅ Agent et RAG chargés avec succès !")
        time.sleep(1)
        st.rerun()

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
    p = Patient(**data)
    r = tools.ajouter_patient(st.session_state.state, p)
    if r.get("success"):
        tools.assigner_salle_attente(st.session_state.state, p.id)
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
            add_event(f"{p['prenom']} {p['nom']} ajouté", emoji_map.get(p['gravite'], "👤"))
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

st.title("🏥 Emergency Management avec Agent IA")

etat = get_state()

# Alertes
alertes = etat.get("alertes_surveillance", [])
if alertes:
    for alerte in alertes:
        st.error(alerte)

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
            st.write(f"{i}. {emoji} **{p.get('prenom')} {p.get('nom')}** - {temps}min{exc}")
        
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
    # Personnel
    st.subheader("👥 Personnel")
    staff = etat.get("staff", [])
    
    med_dispo = sum(1 for s in staff if s.get("type") == "médecin" and s.get("disponible"))
    inf_dispo = sum(1 for s in staff if s.get("type") == "infirmière_mobile" and s.get("disponible"))
    aide_dispo = sum(1 for s in staff if s.get("type") == "aide_soignant" and s.get("disponible"))
    
    st.markdown(f"**👨‍⚕️ Médecins:** {med_dispo} dispo")
    st.markdown(f"**🩺 Infirmières:** {inf_dispo} dispo")
    st.markdown(f"**🚑 Aides soignantes:** {aide_dispo} dispo")
    
    st.divider()
    
    # Log événements
    st.subheader("📋 Log Événements")
    if st.session_state.events:
        with st.container(height=300):
            for evt in reversed(st.session_state.events[-15:]):
                st.text(f"[T+{evt['time']:03d}] {evt['emoji']} {evt['msg']}")
    else:
        st.info("Aucun événement")

# ========== CYCLE AGENT ==========

if st.session_state.running and st.session_state.agent_enabled:
    st.session_state.temps += 1
    tools.tick(st.session_state.state, 1)
    
    # ✅ L'agent est déjà chargé, juste mettre à jour son state
    st.session_state.agent.state = st.session_state.state
    actions = st.session_state.agent.cycle_orchestration()
    
    for action in actions:
        if action:
            # Déterminer l'emoji
            if "transporté en consultation" in action:
                emoji = "🚑"
            elif "Consultation terminée" in action:
                emoji = "✅"
            elif "transporté vers" in action:
                emoji = "🏥"
            elif "saturée" in action or "surveillance" in action:
                emoji = "⚠️"
            else:
                emoji = "ℹ️"
            
            add_event(action, emoji)
    
    time.sleep(st.session_state.agent_speed)
    st.rerun()

elif st.session_state.running and not st.session_state.agent_enabled:
    # Simulation sans agent (juste incrémente le temps)
    st.session_state.temps += 1
    tools.tick(st.session_state.state, 1)  # ✅ Faire avancer le temps simulé
    time.sleep(1)
    st.rerun()