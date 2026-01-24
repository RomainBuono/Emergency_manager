"""Serveur MCP FastAPI pour gestion des urgences."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import tools
from state import EmergencyState, Patient, Gravite, UniteCible


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

@app.post("/tools/ajouter_patient")
def endpoint_ajouter_patient(req: PatientRequest) -> Dict[str, Any]:
    """Ajoute un nouveau patient au système."""
    patient = Patient(**req.model_dump())
    return tools.ajouter_patient(state, patient)


@app.post("/tools/assigner_salle_attente")
def endpoint_assigner_salle(req: AssignerSalleRequest) -> Dict[str, Any]:
    """Assigne un patient à une salle d'attente."""
    return tools.assigner_salle_attente(state, req.patient_id, req.salle_id)


@app.post("/tools/assigner_surveillance")
def endpoint_assigner_surveillance(req: SurveillanceRequest) -> Dict[str, Any]:
    """Assigne la surveillance d'une salle à un staff."""
    return tools.assigner_surveillance(state, req.staff_id, req.salle_id)


# --- TRANSPORTS EN CONSULTATION ---

@app.post("/tools/demarrer_transport_consultation")
def endpoint_transport_consultation(req: TransportConsultationRequest) -> Dict[str, Any]:
    """Démarre le transport d'un patient vers la consultation."""
    return tools.demarrer_transport_consultation(state, req.patient_id, req.staff_id)


@app.post("/tools/finaliser_transport_consultation")
def endpoint_finaliser_transport_consultation(patient_id: str) -> Dict[str, Any]:
    """Finalise l'arrivée en consultation (après 5 min)."""
    return tools.finaliser_transport_consultation(state, patient_id)

@app.post("/tools/terminer_consultation")
def endpoint_terminer_consultation(req: TerminerConsultationRequest) -> Dict[str, Any]:
    """Termine la consultation et définit la destination."""
    return tools.terminer_consultation(state, req.patient_id, req.unite_cible)


# --- RETOUR SALLE ---

@app.post("/tools/retourner_salle_attente")
def endpoint_retour_salle(req: RetourSalleRequest) -> Dict[str, Any]:
    """Retourne un patient en salle d'attente (si pas de transport dispo)."""
    return tools.retourner_patient_salle_attente(
        state, req.patient_id, req.staff_id, req.salle_id
    )

# --- TRANSPORT UNITÉ ---

@app.post("/tools/demarrer_transport_unite")
def endpoint_transport_unite(req: TransportUniteRequest) -> Dict[str, Any]:
    """Démarre le transport d'un patient vers une unité."""
    return tools.demarrer_transport_unite(state, req.patient_id, req.staff_id)


@app.post("/tools/finaliser_transport_unite")
def endpoint_finaliser_transport_unite(patient_id: str):
    """Finalise l'arrivée dans une unité."""
    return tools.finaliser_transport_unite(state, patient_id)

# --- INFORMATIONS ---

@app.get("/tools/get_etat_systeme")
def endpoint_get_etat() -> Dict[str, Any]:
    """Retourne l'état complet du système."""
    return tools.get_etat_systeme(state)


@app.get("/tools/get_prochain_patient_consultation")
def endpoint_prochain_consultation() -> Dict[str, Any]:
    """Retourne le prochain patient à appeler en consultation."""
    result = tools.get_prochain_patient_consultation(state)
    return result if result else {"message": "Aucun patient en attente"}


@app.get("/tools/get_prochain_patient_transport")
def endpoint_prochain_transport():
    """Retourne le prochain patient à transporter."""
    result = tools.get_prochain_patient_transport(state)
    return result if result else {"message": "Aucun patient en attente de transport"}

@app.get("/tools/get_alertes")
def endpoint_alertes():
    """Retourne les alertes du système."""
    return tools.get_alertes(state)

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