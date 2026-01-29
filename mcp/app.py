"""
Simulateur Complet de Gestion des Urgences
Implémente le flux complet selon le cahier des charges
"""
# --- BLOC 1 : BOOTLOADER (Infrastructure) ---
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

# --- BLOC 3 : IMPORTS APPLICATIFS ---
# Standards
import time
import json
import random
from datetime import datetime, timedelta

# Data Science & Web
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Emergency Simulator", page_icon="🏥", layout="wide")

# CSS
st.markdown(
    """
<style>
    .main { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); }
    h1, h2, h3 { color: white !important; }
    .stMetric { background: white; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    
    .flow-step {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .patient-card {
        background: #f9fafb;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .patient-rouge { border-left-color: #ef4444; }
    .patient-jaune { border-left-color: #f59e0b; }
    .patient-vert { border-left-color: #10b981; }
    
    .staff-card {
        background: white;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
    }
    
    .transport-active {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
    }
    
    .action-success {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .action-error {
        background: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .timeline {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .timeline-item {
        border-left: 2px solid #3b82f6;
        padding-left: 1rem;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

API_BASE_URL = "http://localhost:8000"

# Import agent
try:
    from agent import EmergencyAgent

    AGENT_OK = True
except:
    AGENT_OK = False

# Session
if "last_decision" not in st.session_state:
    st.session_state.last_decision = None
if "show_details" not in st.session_state:
    st.session_state.show_details = False
if "timeline" not in st.session_state:
    st.session_state.timeline = []
if "auto_mode" not in st.session_state:
    st.session_state.auto_mode = False


# API Functions
def get_data():
    try:
        r = requests.get(f"{API_BASE_URL}/tools/get_etat_systeme", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def get_alertes():
    try:
        r = requests.get(f"{API_BASE_URL}/tools/get_alertes", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def add_patient(data):
    try:
        r = requests.post(f"{API_BASE_URL}/tools/ajouter_patient", json=data, timeout=5)
        return r.json()
    except:
        return {"success": False}


def assign_room(pid):
    try:
        r = requests.post(
            f"{API_BASE_URL}/tools/assigner_salle_attente",
            json={"patient_id": pid},
            timeout=5,
        )
        return r.json()
    except:
        return {"success": False}


def reset():
    try:
        r = requests.post(f"{API_BASE_URL}/admin/reset", timeout=5)
        st.session_state.timeline = []
        return r.json()
    except:
        return {"success": False}


def gen_patient():
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hugo"]
    surnames = ["Martin", "Durand", "Bernard", "Dubois", "Thomas", "Robert"]
    symptoms = {
        "ROUGE": [
            "Douleur thoracique intense",
            "Difficulté respiratoire sévère",
            "AVC suspecté",
            "Hémorragie importante",
        ],
        "JAUNE": [
            "Fracture du bras",
            "Douleur abdominale aiguë",
            "Migraine intense",
            "Plaie profonde",
        ],
        "VERT": ["Fièvre modérée", "Entorse cheville", "Toux persistante"],
        "GRIS": ["Renouvellement ordonnance", "Consultation de routine"],
    }

    severity = random.choices(
        ["ROUGE", "JAUNE", "VERT", "GRIS"], weights=[25, 35, 30, 10]
    )[0]

    return {
        "id": f"P_{int(time.time())}_{random.randint(1000, 9999)}",
        "prenom": random.choice(names),
        "nom": random.choice(surnames),
        "gravite": severity,
        "symptomes": random.choice(symptoms[severity]),
        "age": random.randint(18, 90),
        "antecedents": [],
    }


def add_timeline(message, type="info"):
    st.session_state.timeline.insert(
        0,
        {"time": datetime.now().strftime("%H:%M:%S"), "message": message, "type": type},
    )
    if len(st.session_state.timeline) > 50:
        st.session_state.timeline.pop()


def calc_wait_time(arrived_at):
    try:
        arrival = datetime.fromisoformat(arrived_at.replace("Z", "+00:00"))
        delta = datetime.now() - arrival.replace(tzinfo=None)
        return int(delta.total_seconds() / 60)
    except:
        return 0


# ========== HEADER ==========
st.title("🏥 Simulateur de Gestion des Urgences")
st.caption("Simulation complète du flux patient avec Agent IA")

data = get_data()
if not data:
    st.error("❌ Serveur MCP déconnecté")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.success("✅ Serveur connecté")
with col2:
    if AGENT_OK and os.getenv("MISTRAL_API_KEY"):
        st.success("🤖 Agent IA actif")
    else:
        st.warning("⚠️ Agent IA inactif")
with col3:
    if st.button("🔄 Refresh"):
        st.rerun()
with col4:
    if st.button("🔄 Reset"):
        reset()
        st.rerun()

st.divider()

# ========== SIDEBAR - SIMULATION ==========
with st.sidebar:
    st.header("🎮 Simulation")

    st.subheader("Mode Manuel")
    if st.button("➕ Ajouter 1 Patient", use_container_width=True):
        p = gen_patient()
        if add_patient(p).get("success"):
            assign_room(p["id"])
            add_timeline(
                f"Nouveau patient: {p['prenom']} {p['nom']} ({p['gravite']})", "success"
            )
            st.rerun()

    col_a, col_b = st.columns(2)
    with col_a:
        nb = st.number_input("Nb patients", 1, 20, 5)
    with col_b:
        if st.button("🚀 Ajouter"):
            for _ in range(nb):
                p = gen_patient()
                add_patient(p)
                assign_room(p["id"])
            add_timeline(f"{nb} patients ajoutés", "success")
            st.rerun()

    st.divider()

    st.subheader("🤖 Agent IA")

    if AGENT_OK and os.getenv("MISTRAL_API_KEY"):
        if st.button("▶️ Lancer Cycle", use_container_width=True, type="primary"):
            # Container pour afficher le processus en temps réel
            status_container = st.empty()
            progress_bar = st.progress(0)
            log_container = st.empty()

            with status_container:
                st.info("🔄 Analyse de la situation...")
            progress_bar.progress(0.2)

            try:
                agent = EmergencyAgent()

                with status_container:
                    st.info("🧠 Agent en réflexion...")
                progress_bar.progress(0.4)

                result = agent.cycle_decision()

                with status_container:
                    st.info("⚙️ Exécution des actions...")
                progress_bar.progress(0.6)

                # Afficher le résumé
                exec_data = result.get("execution", {})
                nb_actions = exec_data.get("nb_actions", 0)
                resultats = exec_data.get("resultats", [])
                nb_success = sum(
                    1 for r in resultats if r.get("resultat", {}).get("success")
                )

                with log_container:
                    st.write("**Résultats:**")
                    for i, res in enumerate(resultats, 1):
                        outil = res.get("outil", "N/A")
                        ok = res.get("resultat", {}).get("success", False)
                        icon = "✅" if ok else "❌"
                        st.caption(f"{icon} Action {i}: {outil}")

                progress_bar.progress(1.0)

                st.session_state.last_decision = result
                st.session_state.show_details = True

                add_timeline(
                    f"Cycle terminé: {nb_success}/{nb_actions} actions réussies",
                    "success" if nb_success == nb_actions else "warning",
                )

                with status_container:
                    if nb_success == nb_actions:
                        st.success(f"✅ Cycle terminé! {nb_actions} actions réussies")
                    else:
                        st.warning(
                            f"⚠️ Cycle terminé: {nb_success}/{nb_actions} réussies"
                        )

                time.sleep(2)
                st.rerun()

            except Exception as e:
                progress_bar.progress(0)
                with status_container:
                    st.error(f"❌ Erreur: {str(e)}")
                add_timeline(f"Erreur: {str(e)}", "error")

        if st.session_state.last_decision:
            if st.button("📋 Voir Décision"):
                st.session_state.show_details = not st.session_state.show_details
                st.rerun()
    else:
        st.warning("Agent non disponible")

    st.divider()

    st.subheader("📊 Statistiques")
    patients = data.get("patients", {})
    total = len([p for p in patients.values() if p["statut"] != "sorti"])
    sortis = len([p for p in patients.values() if p["statut"] == "sorti"])

    st.metric("Patients actifs", total)
    st.metric("Patients sortis", sortis)
    st.metric("Total traités", len(patients))

# ========== DÉCISION AGENT ==========
if st.session_state.show_details and st.session_state.last_decision:
    st.header("🤖 Dernière Décision de l'Agent")

    dec = st.session_state.last_decision

    try:
        dec_data = json.loads(dec.get("decision", "{}"))
        exec_data = dec.get("execution", {})

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(
                f"""
            <div class="flow-step">
                <h3>💭 Raisonnement</h3>
                <p style="color: #374151; line-height: 1.6;">
                    {dec_data.get("raisonnement", "Non disponible")}
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            results = exec_data.get("resultats", [])
            total = len(results)
            success = sum(1 for r in results if r.get("resultat", {}).get("success"))

            st.metric("Actions", total)
            st.metric("Réussies", success)
            st.metric("Échouées", total - success)

        st.subheader("⚡ Détail des Actions")

        for i, action in enumerate(results, 1):
            tool = action.get("outil", "N/A")
            params = action.get("params", {})
            just = action.get("justification", "N/A")
            res = action.get("resultat", {})
            ok = res.get("success", False)

            css = "action-success" if ok else "action-error"
            icon = "✅" if ok else "❌"

            st.markdown(
                f"""
            <div class="{css}">
                <strong>{icon} {tool}</strong><br>
                <small><strong>Params:</strong> {json.dumps(params, ensure_ascii=False)}</small><br>
                <small><strong>Raison:</strong> {just}</small><br>
                <small><strong>Status:</strong> {res.get('error', 'OK') if not ok else 'OK'}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if st.button("❌ Fermer"):
            st.session_state.show_details = False
            st.rerun()

    except Exception as e:
        st.error(f"Erreur: {e}")

    st.divider()

# ========== FLUX PATIENT ==========
st.header("🔄 Flux des Patients")

patients = data.get("patients", {})
rouge = sum(
    1 for p in patients.values() if p["gravite"] == "ROUGE" and p["statut"] != "sorti"
)
jaune = sum(
    1 for p in patients.values() if p["gravite"] == "JAUNE" and p["statut"] != "sorti"
)
vert = sum(
    1 for p in patients.values() if p["gravite"] == "VERT" and p["statut"] != "sorti"
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🔴 ROUGE", rouge)
col2.metric("🟡 JAUNE", jaune)
col3.metric("🟢 VERT", vert)

# Statuts
en_attente = sum(1 for p in patients.values() if p["statut"] == "salle_attente")
en_transport_consult = sum(
    1 for p in patients.values() if p["statut"] == "transport_consultation"
)
en_consultation = sum(1 for p in patients.values() if p["statut"] == "consultation")
en_transport_unite = sum(
    1 for p in patients.values() if p["statut"] == "transport_unite"
)

col4.metric("⏳ En attente", en_attente)
col5.metric("🚑 En transport", en_transport_consult + en_transport_unite)

# Graphique flux
if rouge + jaune + vert > 0:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["ROUGE", "JAUNE", "VERT"],
                values=[rouge, jaune, vert],
                marker=dict(colors=["#ef4444", "#f59e0b", "#10b981"]),
                hole=0.6,
            )
        ]
    )
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ========== ALERTES ==========
alertes = get_alertes()
if alertes:
    alerts_list = []
    if alertes.get("surveillance"):
        alerts_list.extend(alertes["surveillance"])
    if alertes.get("patients_longue_attente"):
        alerts_list.extend(alertes["patients_longue_attente"])

    if alerts_list:
        st.error("⚠️ ALERTES CRITIQUES")
        for alert in alerts_list:
            st.warning(alert)
        st.divider()

# ========== PATIENTS PAR ÉTAPE ==========
st.header("👥 Patients par Étape du Parcours")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏥 Salle d'Attente")
    attente = [p for p in patients.values() if p["statut"] == "salle_attente"]
    if attente:
        for p in attente[:10]:
            colors = {
                "ROUGE": "patient-rouge",
                "JAUNE": "patient-jaune",
                "VERT": "patient-vert",
            }
            css = colors.get(p["gravite"], "")
            wait = calc_wait_time(p.get("arrived_at", ""))
            st.markdown(
                f"""
            <div class="patient-card {css}">
                <strong>{p['prenom']} {p['nom']}</strong><br>
                <small>{p['symptomes'][:40]}...</small><br>
                <small>⏱️ {wait} min</small>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun patient")

with col2:
    st.subheader("💼 En Consultation")
    consult = [p for p in patients.values() if p["statut"] == "consultation"]
    transport_c = [
        p for p in patients.values() if p["statut"] == "transport_consultation"
    ]

    if transport_c:
        st.caption("🚑 En transport vers consultation:")
        for p in transport_c:
            st.markdown(
                f"""
            <div class="patient-card transport-active">
                <strong>{p['prenom']} {p['nom']}</strong><br>
                <small>Transport en cours...</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

    if consult:
        for p in consult:
            st.markdown(
                f"""
            <div class="patient-card">
                <strong>{p['prenom']} {p['nom']}</strong><br>
                <small>{p['symptomes'][:40]}...</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

    if not consult and not transport_c:
        st.info("Consultation libre")

with col3:
    st.subheader("🏨 Transport Unités")
    transport_u = [p for p in patients.values() if p["statut"] == "transport_unite"]
    if transport_u:
        for p in transport_u:
            unite = p.get("unite_cible", "N/A")
            st.markdown(
                f"""
            <div class="patient-card transport-active">
                <strong>{p['prenom']} {p['nom']}</strong><br>
                <small>→ {unite}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun transport")

st.divider()

# ========== PERSONNEL ==========
st.header("👨‍⚕️ État du Personnel")

staff = data.get("staff", [])

col1, col2 = st.columns(2)

with col1:
    st.subheader("Infirmières")
    infirmieres = [s for s in staff if "infirmière" in s.get("type", "").lower()]
    for s in infirmieres:
        status = "✅ Disponible"
        if s.get("en_transport"):
            status = f"🚑 Transport ({s.get('destination_transport', 'N/A')})"
        elif not s.get("disponible"):
            status = f"🔴 {s.get('localisation', 'Occupé')}"

        st.markdown(
            f"""
        <div class="staff-card">
            <strong>{s['id']}</strong> - {s['type']}<br>
            <small>{status}</small>
        </div>
        """,
            unsafe_allow_html=True,
        )

with col2:
    st.subheader("Aides-Soignants & Médecin")
    autres = [s for s in staff if "infirmière" not in s.get("type", "").lower()]
    for s in autres:
        status = "✅ Disponible"
        if s.get("en_transport"):
            status = f"🚑 Transport ({s.get('destination_transport', 'N/A')})"
        elif not s.get("disponible"):
            status = f"🔴 {s.get('localisation', 'Occupé')}"

        st.markdown(
            f"""
        <div class="staff-card">
            <strong>{s['id']}</strong> - {s['type']}<br>
            <small>{status}</small>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.divider()

# ========== SALLES ==========
st.header("🏥 Salles d'Attente")

salles = data.get("salles_attente", [])
cols = st.columns(3)

for idx, salle in enumerate(salles):
    with cols[idx]:
        nom = salle["id"].replace("salle_attente_", "Salle ")
        occ = len(salle["patients"])
        cap = salle["capacite"]
        rate = (occ / cap * 100) if cap > 0 else 0

        color = "🔴" if rate >= 90 else "🟡" if rate >= 70 else "🟢"

        st.markdown(f"### {color} {nom}")
        st.progress(rate / 100)
        st.caption(f"{occ}/{cap} ({rate:.0f}%)")

        if salle.get("surveillee_par"):
            st.success(f"👀 {salle['surveillee_par']}")
        else:
            st.warning("⚠️ Non surveillée")

st.divider()

# ========== TIMELINE ==========
st.header("📜 Historique des Événements")

if st.session_state.timeline:
    st.markdown('<div class="timeline">', unsafe_allow_html=True)
    for event in st.session_state.timeline[:20]:
        icon = (
            "✅"
            if event["type"] == "success"
            else "ℹ️" if event["type"] == "info" else "❌"
        )
        st.markdown(
            f"""
        <div class="timeline-item">
            <small><strong>[{event['time']}]</strong> {icon} {event['message']}</small>
        </div>
        """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Aucun événement")

st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏥 Emergency Simulator v5.0")
