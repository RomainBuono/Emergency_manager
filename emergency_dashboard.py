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
    """Agent IA orchestrant les flux en respectant la sécurité et les priorités."""
    
    def __init__(self, state: EmergencyState):
        self.state = state
<<<<<<< HEAD
=======
        # Mode simulation : rapide, sans ML, avec cache embeddings
>>>>>>> 24a8c08d3addbf99c449b5533ab8c54d28ebea65
        self.rag_engine = HospitalRAGEngine(mode="simulation")
    
    def cycle_orchestration(self) -> list[str]:
        """Exécute le cycle complet des opérations urgences."""
        actions = []
        
        # 1. FINALISATION (Correction de l'AttributeError)
        actions.extend(self._finaliser_transports())
        
        # 2. SURVEILLANCE (Priorité sécurité 15 min)
        actions.extend(self._gerer_surveillance())
    
        # 3. SORTIE DE CONSULTATION (Décision RAG)
        action_sortie = self._gerer_sortie_consultation()
        if action_sortie:
            actions.append(action_sortie)
    
        # 4. TRANSPORT VERS UNITÉS (Règle 45 min + Règle de Secours)
        action_trans_unite = self._gerer_transport_unite()
        if action_trans_unite:
            actions.append(action_trans_unite)

        # 5. ENTRÉE EN CONSULTATION
        action_entree = self._gerer_consultation()
        if action_entree:
            actions.append(action_entree)
    
        return [a for a in actions if a is not None]

    def _finaliser_transports(self) -> list[str]:
        """Vérifie si les transports sont arrivés et libère le personnel."""
        actions = []
        for staff in self.state.staff:
            if staff.en_transport and staff.fin_transport_prevue:
                if self.state.current_time >= staff.fin_transport_prevue:
                    pid = staff.patient_transporte_id
                    if staff.destination_transport == "consultation":
                        tools.finaliser_transport_consultation(self.state, pid)
                        actions.append(f"✅ Arrivée en consultation : {pid}")
                    else:
                        tools.finaliser_transport_unite(self.state, pid)
                        p = self.state.patients.get(pid)
                        actions.append(f"🏁 {p.prenom if p else pid} arrivé en unité")
        return actions

    def _gerer_transport_unite(self) -> Optional[str]:
        """Gère le transport vers les unités avec gestion du quorum de sécurité."""
        queue = self.state.get_queue_transport_sortie()
        if not queue: return None
    
        p = queue[0]
    
        # 1. Identifier le personnel mobile libre (Infirmières B/C + AS 1/2)
        staff_mobiles = [s for s in self.state.staff if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]
    
        # Aide-soignants pour transport long (45 min)
        as_dispo = [s for s in staff_dispo if s.type == TypeStaff.AIDE_SOIGNANT]

        # CAS NORMAL : Transport direct par AS (45 min)
        # Sécurité : On ne lance un 45 min que s'il reste au moins 2 personnes pour la surveillance
        if as_dispo and len(staff_dispo) >= 3:
            res = tools.demarrer_transport_unite(self.state, p.id, as_dispo[0].id)
            if res.get("success"):
                return f"🚑 {p.prenom} -> {p.unite_cible} (AS, 45 min)"

        # CAS DE SECOURS : Retour en salle d'attente (5 min)
        # Si AS occupés ou risque pour la surveillance, on libère la consultation
        if staff_dispo:
            agent = staff_dispo[0]
            # On utilise l'outil de secours (5 min de trajet)
            res = tools.retourner_patient_salle_attente(self.state, p.id, agent.id)
            if res.get("success"):
                return f"🔄 {p.prenom} replacé en salle (Secours, 5 min) : AS occupés"
            
        return None
    
    def _gerer_consultation(self) -> Optional[str]:
        """Gère l'entrée en consultation si au moins 1 soignant reste en surveillance."""
        if not self.state.consultation.est_libre(): return None
        
        staff_mobiles = [s for s in self.state.staff if s.type.value in ["infirmier(ere)_mobile", "aide_soignant"]]
        staff_dispo = [s for s in staff_mobiles if s.disponible and not s.en_transport]

        if len(staff_dispo) < 2:
            return "⏳ Sécurité : Personnel retenu pour surveillance"

        queue = self.state.get_queue_consultation()
        if queue and staff_dispo:
            res = tools.demarrer_transport_consultation(self.state, queue[0].id, staff_dispo[0].id)
            if res.get("success"):
                return f"🚑 {queue[0].prenom} vers consultation"
        return None

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
                    res = tools.assigner_surveillance(self.state, agent.id, salle.id)
                    if res.get("success"):
                        actions.append(f"📋 {agent.id} affecté à {salle.id}")
        return actions

    def _gerer_sortie_consultation(self) -> Optional[str]:
        """Détermine si la consultation est finie et décide de la suite."""
        if self.state.consultation.est_libre(): 
            return None
        
        pid = self.state.consultation.patient_id
        patient = self.state.patients.get(pid)
    
        # Calcul de la durée écoulée
        debut = self.state.consultation.debut_consultation
        if not debut: return None
        duree_ecoulee = (self.state.current_time - debut).total_seconds() / 60
    
        # Durée minimale selon les règles (ex: VERT 10-25min)
        duree_min = 10 if patient.gravite == Gravite.VERT else 20
    
        if duree_ecoulee >= duree_min:
            # Logique de décision simplifiée
            # Si VERT ou GRIS -> Maison, sinon -> Une unité au hasard
            destination = UniteCible.MAISON if patient.gravite in [Gravite.VERT, Gravite.GRIS] else UniteCible.CARDIO
        
            res = tools.terminer_consultation(self.state, pid, destination)
            if res.get("success"):
                return f"✅ Consultation terminée : {patient.prenom} orienté vers {destination}"
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
    """Ajoute un patient et l'assigne à une salle."""
    p = Patient(**data)
    r = tools.ajouter_patient(st.session_state.state, p)
    
    if r.get("success"):
        # ✅ Assigner à une salle d'attente
        # Vérifier que la fonction existe
        if hasattr(tools, 'assigner_salle_attente'):
            salle_result = tools.assigner_salle_attente(st.session_state.state, p.id)
            
            if salle_result.get("success"):
                salle_id = salle_result.get("salle_id")
                add_event(f"Patient {p.prenom} assigné à {salle_id}", "🏥")
            else:
                add_event(f"⚠️ {p.prenom} : {salle_result.get('error')}", "⚠️")
        else:
            # Fallback : assigner manuellement
            for salle in st.session_state.state.salles_attente:
                if not salle.est_pleine():
                    salle.patients.append(p.id)
                    p.statut = StatutPatient.SALLE_ATTENTE
                    p.salle_attente_id = salle.id
                    add_event(f"Patient {p.prenom} assigné à {salle.id}", "🏥")
                    break
    
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

# ========== BANDEAU PERSONNEL ==========
st.subheader("👨‍⚕️ Suivi du Personnel en Temps Réel")

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
    # Utilisation de staff_data pour être cohérent avec le reste du bloc
    medecin_data = next((s for s in staff_data if s.get("type") == "médecin"), None)
    
    if medecin_data:
        # Vérification via l'état de la consultation
        est_occupe = nb_consultation > 0
        couleur = "🔴" if est_occupe else "🟢"
        label = "en consultation" if est_occupe else "libre"
        st.caption(f"{couleur} {medecin_data.get('id')}: {label}")

with col_if:
    st.markdown("**💉 Inf. Fixes**")
    for staff in inf_fixes:
        loc = staff.get("localisation", "repos")
        st.caption(f"📍 {staff.get('id')}: {loc}")

with col_im:
    st.markdown("**🏃 Inf. Mobiles**")
    for staff in inf_mobiles:
        # Priorité d'affichage : Transport > Surveillance > Attente
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
        # Les aides-soignants ont maintenant les mêmes capacités d'affichage
        if staff.get("en_transport"):
            status_text = f"🚑 Transport {staff.get('patient_transporte_id')}"
        elif staff.get("salle_surveillee"):
            status_text = f"📋 Surveillance {staff.get('salle_surveillee')}"
        else:
            status_text = "⏳ En attente de mission"
            
        # On garde le timer de sécurité (60 min max hors service)
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
    inf_dispo = sum(1 for s in staff if s.get("type") == "infirmier(ere)_mobile" and s.get("disponible"))
    aide_dispo = sum(1 for s in staff if s.get("type") == "aide_soignant" and s.get("disponible"))
    
    st.markdown(f"**👨‍⚕️ Médecins:** {med_dispo} dispo")
<<<<<<< HEAD
    st.markdown(f"**🩺 infirmier(ère):** {inf_dispo} dispo")
    st.markdown(f"**🚑 Aides-soignant(e):** {aide_dispo} dispo")
=======
    st.markdown(f"**🩺 Infirmières:** {inf_dispo} dispo")
    st.markdown(f"**🚑 Aides soignantes:** {aide_dispo} dispo")
>>>>>>> 24a8c08d3addbf99c449b5533ab8c54d28ebea65
    
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
# ========== CYCLE AGENT ==========

if st.session_state.running and st.session_state.agent_enabled:
    
    # ÉTAPE A : Créer l'agent s'il n'existe pas ENCORE
    if st.session_state.agent is None:
        st.session_state.agent = EmergencyAgent(st.session_state.state)
        st.session_state.agent_loaded = True

    # ÉTAPE B : Faire avancer le temps
    st.session_state.temps += 1
    tools.tick(st.session_state.state, 1)
    
    # ÉTAPE C : Donner l'état à l'agent (Maintenant il n'est plus None)
    st.session_state.agent.state = st.session_state.state
    
    # ÉTAPE D : Lancer les décisions
    actions = st.session_state.agent.cycle_orchestration()
    
    for action in actions:
        if action:
            # Choix de l'emoji selon l'action
            emoji = "🚑" if "transport" in action.lower() else "✅"
            if "📋" in action: emoji = "📋"
            add_event(action, emoji)
    
    time.sleep(st.session_state.agent_speed)
    st.rerun()