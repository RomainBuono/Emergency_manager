"""Serveur MCP FastAPI pour gestion des urgences."""

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

# --- BLOC 3 : IMPORTS APPLICATIFS (Standard & Tiers) ---
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- BLOC 4 : IMPORTS LOCAUX (Modules Métier) ---
try:
    # Comme on a fixé le sys.path, Python peut trouver les modules voisins
    # Note : Si 'tools' et 'state' sont dans le même dossier que server.py,
    # l'import direct fonctionne. S'ils étaient ailleurs, on ferait 'from mcp import tools'
    from controllers.emergency_controller import EmergencyController
    from state import EmergencyState, Patient, Gravite, UniteCible
except ImportError as e:
    print(f"Erreur critique d'import local : {e}", file=sys.stderr)
    print(f"   Vérifiez que 'tools.py' et 'state.py' sont bien dans : {CURRENT_FILE.parent}", file=sys.stderr)
    sys.exit(1)



# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmergencyMCP")

app = FastAPI(
    title="Emergency MCP Server",
    description="Serveur MCP pour gestion intelligente des urgences",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

state = EmergencyState()
controller = EmergencyController(state)

# model pydantic
class PatientRequest(BaseModel):
    """Requête pour ajouter un patient."""
    id: str
    prenom: str
    nom: str
    gravite: Gravite
    symptomes: str
    age: int
    antecedents: list[str] = []


class AssignerSalleRequest(BaseModel):
    """Requête pour assigner une salle d'attente."""
    patient_id: str
    salle_id: Optional[str] = None


class SurveillanceRequest(BaseModel):
    """Requête pour assigner la surveillance."""
    staff_id: str
    salle_id: str


class TransportConsultationRequest(BaseModel):
    """Requête pour démarrer transport vers consultation."""
    patient_id: str
    staff_id: str


class TerminerConsultationRequest(BaseModel):
    """Requête pour terminer une consultation."""
    patient_id: str
    unite_cible: UniteCible


class RetourSalleRequest(BaseModel):
    """Requête pour retourner patient en salle."""
    patient_id: str
    staff_id: str
    salle_id: Optional[str] = None


class TransportUniteRequest(BaseModel):
    """Requête pour transport vers unité."""
    patient_id: str
    staff_id: str


# ==================== ENDPOINTS PRINCIPAUX ====================
@app.get("/")
def root() -> Dict[str, Any]:
    """Page d'accueil."""
    return {
        "service": "Emergency MCP Server",
        "version": "2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }

# --- ARRIVEE ET TRIAGE ---

@app.post("/controller/ajouter_patient")
def endpoint_ajouter_patient(req: PatientRequest) -> Dict[str, Any]:
    """Ajoute un nouveau patient au système."""
    patient = Patient(**req.model_dump())
    return controller.ajouter_patient(state, patient)


@app.post("/controller/assigner_salle_attente")
def endpoint_assigner_salle(req: AssignerSalleRequest) -> Dict[str, Any]:
    """Assigne un patient à une salle d'attente."""
    return controller.assigner_salle_attente(state, req.patient_id, req.salle_id)


@app.post("/contreoller/assigner_surveillance")
def endpoint_assigner_surveillance(req: SurveillanceRequest) -> Dict[str, Any]:
    """Assigne la surveillance d'une salle à un staff."""
    return controller.assigner_surveillance(state, req.staff_id, req.salle_id)


# --- TRANSPORTS EN CONSULTATION ---

@app.post("/controller/demarrer_transport_consultation")
def endpoint_transport_consultation(req: TransportConsultationRequest) -> Dict[str, Any]:
    """Démarre le transport d'un patient vers la consultation."""
    return controller.demarrer_transport_consultation(state, req.patient_id, req.staff_id)


@app.post("/controller/finaliser_transport_consultation")
def endpoint_finaliser_transport_consultation(patient_id: str) -> Dict[str, Any]:
    """Finalise l'arrivée en consultation (après 5 min)."""
    return controller.finaliser_transport_consultation(state, patient_id)

@app.post("/controller/terminer_consultation")
def endpoint_terminer_consultation(req: TerminerConsultationRequest) -> Dict[str, Any]:
    """Termine la consultation et définit la destination."""
    return controller.terminer_consultation(state, req.patient_id, req.unite_cible)


# --- RETOUR SALLE ---

@app.post("/controller/retourner_salle_attente")
def endpoint_retour_salle(req: RetourSalleRequest) -> Dict[str, Any]:
    """Retourne un patient en salle d'attente (si pas de transport dispo)."""
    return controller.retourner_patient_salle_attente(
        state, req.patient_id, req.staff_id, req.salle_id
    )

# --- TRANSPORT UNITÉ ---

@app.post("/controller/demarrer_transport_unite")
def endpoint_transport_unite(req: TransportUniteRequest) -> Dict[str, Any]:
    """Démarre le transport d'un patient vers une unité."""
    return controller.demarrer_transport_unite(state, req.patient_id, req.staff_id)


@app.post("/controller/finaliser_transport_unite")
def endpoint_finaliser_transport_unite(patient_id: str):
    """Finalise l'arrivée dans une unité."""
    return controller.finaliser_transport_unite(state, patient_id)

# --- INFORMATIONS ---

@app.get("/controller/get_etat_systeme")
def endpoint_get_etat() -> Dict[str, Any]:
    """Retourne l'état complet du système."""
    return controller.get_etat_systeme(state)


@app.get("/controller/get_prochain_patient_consultation")
def endpoint_prochain_consultation() -> Dict[str, Any]:
    """Retourne le prochain patient à appeler en consultation."""
    result = controller.get_prochain_patient_consultation(state)
    return result if result else {"message": "Aucun patient en attente"}


@app.get("/controller/get_prochain_patient_transport")
def endpoint_prochain_transport():
    """Retourne le prochain patient à transporter."""
    result = controller.get_prochain_patient_transport(state)
    return result if result else {"message": "Aucun patient en attente de transport"}

@app.get("/controller/get_alertes")
def endpoint_alertes():
    """Retourne les alertes du système."""
    return controller.get_alertes(state)

# ==================== ENDPOINT POUR RESET ====================

@app.post("/admin/reset")
def reset_system():
    """Réinitialise complètement le système (pour tests)."""
    global state
    state = EmergencyState()
    return {"success": True, "message": "Système réinitialisé"}


# ==================== DÉMARRAGE ====================

if __name__ == "__main__":
    logger.info(" Démarrage du serveur MCP Emergency Manager...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")