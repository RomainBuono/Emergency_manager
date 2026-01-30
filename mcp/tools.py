"""Outils MCP pour gérer le service des urgences."""

import sys
import os
from pathlib import Path
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

# --- BLOC 2 : CONFIGURATION DU SYSTEME ---
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

# --- BLOC 3 : IMPORTS APPLICATIFS ---
try:
    from state import (
        EmergencyState,
        Patient,
        Staff,
        SalleAttente,
        Gravite,
        UniteCible,
        StatutPatient,
        TypeStaff,
    )
except ImportError as e:
    print(f"Erreur d'import dans tools.py : {e}", file=sys.stderr)
    sys.exit(1)

# Configuration des durées
DUREES_CONSULTATION = {
    Gravite.ROUGE: (1, 5),
    Gravite.JAUNE: (20, 40),
    Gravite.VERT: (10, 25),
    Gravite.GRIS: (5, 15),
}

# ==================== 1. ARRIVÉE ET TRIAGE ====================

def ajouter_patient(state: EmergencyState, patient: Patient) -> Dict[str, Any]:
    """Ajoute un patient au système (étape triage)."""
    if patient.id in state.patients:
        return {"success": False, "error": "Patient ID déjà existant"}

    patient.arrived_at = state.current_time
    patient.statut = StatutPatient.ATTENTE_TRIAGE
    state.patients[patient.id] = patient

    return {
        "success": True,
        "patient_id": patient.id,
        "gravite": patient.gravite,
        "message": f"Patient {patient.prenom} {patient.nom} ajouté",
    }

def assigner_salle_attente(state: EmergencyState, patient_id: str, salle_id: Optional[str] = None) -> Dict[str, Any]:
    """Assigne un patient à une salle d'attente."""
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}
    
    if not salle_id:
        salles_dispo = [s for s in state.salles_attente if not s.est_pleine()]
        if not salles_dispo:
            return {"success": False, "error": "Toutes les salles sont pleines"}
        salle = max(salles_dispo, key=lambda s: s.places_disponibles())
        salle_id = salle.id

    salle = next((s for s in state.salles_attente if s.id == salle_id), None)
    if not salle or salle.est_pleine():
        return {"success": False, "error": "Salle pleine ou invalide"}

    salle.patients.append(patient_id)
    patient.statut = StatutPatient.SALLE_ATTENTE
    patient.salle_attente_id = salle_id
    return {"success": True, "salle_id": salle_id}

# ==================== 2. SURVEILLANCE ====================

def assigner_surveillance(state: EmergencyState, staff_id: str, salle_id: str) -> Dict[str, Any]:
    """Assigne un membre du staff à la surveillance d'une salle."""
    staff = next((s for s in state.staff if s.id == staff_id), None)
    if not staff or staff.type not in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT]:
        return {"success": False, "error": "Staff invalide pour surveillance"}

    if not staff.peut_partir(state.current_time):
        return {"success": False, "error": "Staff non disponible"}

    salle = next((s for s in state.salles_attente if s.id == salle_id), None)
    if not salle:
        return {"success": False, "error": "Salle introuvable"}
    
    if staff.salle_surveillee:
        ancienne = next((s for s in state.salles_attente if s.id == staff.salle_surveillee), None)
        if ancienne:
            ancienne.surveillee_par = None

    staff.localisation = salle_id
    staff.salle_surveillee = salle_id 
    staff.occupe_depuis = state.current_time
    salle.surveillee_par = staff_id
    salle.derniere_surveillance = state.current_time
    return {"success": True, "staff_id": staff_id, "salle_id": salle_id}

def verifier_et_gerer_surveillance(state: EmergencyState) -> List[str]:
    """Automatisation de l'agent pour couvrir les salles vides."""
    actions = []
    for salle in state.salles_attente:
        if len(salle.patients) > 0 and not salle.surveillee_par:
            staff_dispo = [s for s in state.staff if s.type in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT] 
                          and s.disponible and not s.en_transport and s.localisation == "repos"]
            if staff_dispo:
                assigner_surveillance(state, staff_dispo[0].id, salle.id)
                actions.append(f"📋 Surveillance auto : {staff_dispo[0].id} -> {salle.id}")
    return actions

# ==================== 3. CYCLE CONSULTATION ====================

def demarrer_transport_consultation(state: EmergencyState, patient_id: str, staff_id: str) -> Dict[str, Any]:
    """Démarre le trajet vers la salle de consultation."""
    patient = state.patients.get(patient_id)
    staff = next((s for s in state.staff if s.id == staff_id), None)
    
    if not patient or not staff or not state.consultation.est_libre():
        return {"success": False, "error": "Conditions de transport non remplies"}

    if patient.salle_attente_id:
        salle = next((s for s in state.salles_attente if s.id == patient.salle_attente_id), None)
        if salle and patient_id in salle.patients:
            salle.patients.remove(patient_id)

    patient.statut = StatutPatient.EN_TRANSPORT_CONSULTATION
    patient.salle_attente_id = None
    state.consultation.patient_id = patient_id

    staff.en_transport = True
    staff.patient_transporte_id = patient_id
    staff.destination_transport = "consultation"
    staff.fin_transport_prevue = state.current_time + timedelta(minutes=5)
    staff.disponible = False
    return {"success": True, "arrivee_prevue": staff.fin_transport_prevue.isoformat()}

def finaliser_transport_consultation(state: EmergencyState, patient_id: str) -> Dict[str, Any]:
    """Arrivée effective en consultation et libération du staff."""
    patient = state.patients.get(patient_id)
    if not patient or patient.statut != StatutPatient.EN_TRANSPORT_CONSULTATION:
        return {"success": False, "error": "Patient pas en transport"}

    transporteur = next((s for s in state.staff if s.patient_transporte_id == patient_id), None)
    if transporteur:
        transporteur.en_transport = False
        transporteur.patient_transporte_id = None
        transporteur.disponible = True
        transporteur.localisation = transporteur.salle_surveillee if transporteur.salle_surveillee else "repos"

    patient.statut = StatutPatient.EN_CONSULTATION
    state.consultation.patient_id = patient_id
    state.consultation.debut_consultation = state.current_time
    return {"success": True, "debut": state.current_time.isoformat()}

def terminer_consultation(state: EmergencyState, patient_id: str, unite_cible: UniteCible) -> Dict[str, Any]:
    """Validation médicale et destination finale du patient."""
    patient = state.patients.get(patient_id)
    if not patient or patient.statut != StatutPatient.EN_CONSULTATION:
        return {"success": False, "error": "Patient pas en consultation"}

    # Vérification de cohérence (ex: ROUGE)
    if patient.gravite == Gravite.ROUGE and unite_cible == UniteCible.MAISON:
         return {"success": False, "error": "Incohérence : ROUGE ne peut pas sortir"}

    patient.unite_cible = unite_cible
    patient.consultation_end_at = state.current_time
    state.consultation.patient_id = None

    if unite_cible == UniteCible.MAISON:
        patient.statut = StatutPatient.SORTI
    else:
        patient.statut = StatutPatient.ATTENTE_TRANSPORT_SORTIE
    return {"success": True, "destination": unite_cible}

# ==================== 4. CYCLE SORTIE ET UNITÉS ====================

def retourner_patient_salle_attente(state: EmergencyState, patient_id: str, staff_id: str, salle_id: Optional[str] = None) -> Dict[str, Any]:
    """Retour en salle si l'unité cible est pleine ou le transport indisponible."""
    patient = state.patients.get(patient_id)
    if not patient or patient.statut != StatutPatient.ATTENTE_TRANSPORT_SORTIE:
        return {"success": False, "error": "Patient non prêt pour retour salle"}

    if not salle_id:
        salles_dispo = [s for s in state.salles_attente if not s.est_pleine()]
        salle = max(salles_dispo, key=lambda s: s.places_disponibles()) if salles_dispo else None
        salle_id = salle.id if salle else None

    if not salle_id: return {"success": False, "error": "Pas de salle libre"}

    patient.statut = StatutPatient.SALLE_ATTENTE
    patient.salle_attente_id = salle_id
    next((s for s in state.salles_attente if s.id == salle_id)).patients.append(patient_id)
    return {"success": True, "message": "Patient retourné en attente"}

def demarrer_transport_unite(state: EmergencyState, patient_id: str, staff_id: str) -> Dict[str, Any]:
    """
    Démarre le transport d'un patient vers son unité cible.
    Respecte la règle des 45 minutes pour les cas non critiques.
    """
    patient = state.patients.get(patient_id)
    staff = next((s for s in state.staff if s.id == staff_id), None)
    
    # 1. Vérifications de base (Existence et Destination)
    if not patient or not staff:
        return {"success": False, "error": "Patient ou Staff introuvable"}

    if not patient.unite_cible:
        return {"success": False, "error": "Aucune unité cible définie pour ce patient"}

    # 2. Vérification de la capacité de l'unité cible
    unite = state.get_unite(patient.unite_cible)
    if not unite or not unite.a_de_la_place():
        return {"success": False, "error": f"L'unité {patient.unite_cible} est saturée"}

    # 3. Vérification de la disponibilité et du type de staff
    # Seuls les aides-soignants (prioritaires) ou infirmières mobiles peuvent effectuer ce transport
    if staff.type not in [TypeStaff.AIDE_SOIGNANT, TypeStaff.INFIRMIERE_MOBILE]:
        return {"success": False, "error": "Type de personnel non autorisé pour ce transport"}
    
    if not staff.peut_partir(state.current_time):
        return {"success": False, "error": "Le personnel n'est pas disponible (contrainte de temps ou déjà occupé)"}

    # 4. Application de la règle de durée (Source: regles.json)
    # CAS PRIORITAIRE ROUGE : 5 minutes
    # AUTRES CAS : 45 minutes
    duree = 5 if patient.gravite == Gravite.ROUGE else 45
    
    # 5. Libération de la salle d'attente (si le patient y était retourné)
    if patient.salle_attente_id:
        salle = next((s for s in state.salles_attente if s.id == patient.salle_attente_id), None)
        if salle and patient_id in salle.patients:
            salle.patients.remove(patient_id)
        patient.salle_attente_id = None

    # 6. Mise à jour des états (Patient et Staff)
    patient.statut = StatutPatient.EN_TRANSPORT_SORTIE
    
    staff.en_transport = True
    staff.disponible = False
    staff.patient_transporte_id = patient_id
    staff.destination_transport = patient.unite_cible
    staff.fin_transport_prevue = state.current_time + timedelta(minutes=duree)
    
    # Gestion spécifique de la surveillance si le staff surveillait une salle
    if staff.salle_surveillee:
        salle_prec = next((s for s in state.salles_attente if s.id == staff.salle_surveillee), None)
        if salle_prec:
            salle_prec.surveillee_par = None
        staff.salle_surveillee = None

    return {
        "success": True, 
        "duree_min": duree, 
        "arrivee_prevue": staff.fin_transport_prevue.isoformat(),
        "staff_id": staff.id
    }

def finaliser_transport_unite(state: EmergencyState, patient_id: str) -> Dict[str, Any]:
    """Arrivée finale en unité."""
    patient = state.patients.get(patient_id)
    if not patient or patient.statut != StatutPatient.EN_TRANSPORT_SORTIE:
        return {"success": False, "error": "Patient pas en transport de sortie"}

    unite = state.get_unite(patient.unite_cible)
    if unite: unite.patients.append(patient_id)
    
    patient.statut = StatutPatient.SORTI
    transporteur = next((s for s in state.staff if s.patient_transporte_id == patient_id), None)
    if transporteur:
        transporteur.en_transport = False
        transporteur.disponible = True
        transporteur.patient_transporte_id = None
    return {"success": True}

def sortir_patient(state: EmergencyState, patient_id: str) -> Dict[str, Any]:
    """Sortie manuelle ou vers domicile."""
    patient = state.patients.get(patient_id)
    if patient:
        patient.statut = StatutPatient.SORTI
        return {"success": True}
    return {"success": False, "error": "Patient introuvable"}

# ==================== 5. MOTEUR ET ÉTAT ====================

def tick(state: EmergencyState, minutes: int = 1) -> dict:
    """Fait progresser le temps simulé et traite les événements automatiques."""
    state.current_time += timedelta(minutes=minutes)
    events = []

    # Finalisation auto des transports arrivés
    for s in state.staff:
        if s.en_transport and s.fin_transport_prevue and state.current_time >= s.fin_transport_prevue:
            pid = s.patient_transporte_id
            if s.destination_transport == "consultation":
                finaliser_transport_consultation(state, pid)
                events.append(f"🚑 {pid} arrivé en consultation")
            else:
                finaliser_transport_unite(state, pid)
                events.append(f"🏥 {pid} arrivé en unité")

    return {"success": True, "events": events, "now": state.current_time.isoformat()}

def get_etat_systeme(state: EmergencyState) -> Dict[str, Any]:
    return state.to_dict()

def get_alertes(state: EmergencyState) -> Dict[str, Any]:
    """Compilation des alertes de sécurité."""
    return {
        "surveillance": state.verifier_surveillance_salles(),
        "longue_attente": [p.id for p in state.patients.values() 
                          if p.statut == StatutPatient.SALLE_ATTENTE 
                          and p.temps_attente_minutes(state.current_time) > 360]
    }