"""Outils MCP pour gérer le service des urgences."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
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


# ==================== ARRIVÉE DES PATIENTS ====================


def ajouter_patient(state: EmergencyState, patient: Patient) -> Dict[str, Any]:
    """
    Ajoute un nouveau patient au système (étape triage).
    Args:
        state: État du système
        patient: Nouveau patient
    Returns:
        Résultat de l'opération avec détails
    """
    # Vérifier que l'ID n'existe pas déjà
    if patient.id in state.patients:
        return {"success": False, "error": "Patient ID déjà existant"}

    # Ajouter le patient
    patient.statut = StatutPatient.ATTENTE_TRIAGE
    state.patients[patient.id] = patient

    return {
        "success": True,
        "patient_id": patient.id,
        "gravite": patient.gravite.value,
        "message": f"Patient {patient.prenom} {patient.nom} ajouté (gravité: {patient.gravite.value})",
    }


def assigner_salle_attente(
    state: EmergencyState, patient_id: str, salle_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assigne un patient à une salle d'attente (après triage).
    Si salle_id non spécifié, choisit automatiquement une salle disponible.

    Args:
        state: État du système
        patient_id: ID du patient
        salle_id: ID de la salle (optionnel, auto si None)

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.ATTENTE_TRIAGE:
        return {
            "success": False,
            "error": f"Patient pas en attente de triage (statut: {patient.statut})",
        }

    # Si pas de salle spécifiée, choisir automatiquement
    if not salle_id:
        salles_dispo = [s for s in state.salles_attente if not s.est_pleine()]
        if not salles_dispo:
            return {"success": False, "error": "Aucune salle d'attente disponible"}
        # Prendre la salle avec le plus de places
        salle = max(salles_dispo, key=lambda s: s.places_disponibles())
        salle_id = salle.id
    else:
        salle = next((s for s in state.salles_attente if s.id == salle_id), None)
        if not salle:
            return {"success": False, "error": "Salle introuvable"}
        if salle.est_pleine():
            return {"success": False, "error": "Salle pleine"}

    # Assigner
    salle.patients.append(patient_id)
    patient.statut = StatutPatient.SALLE_ATTENTE
    patient.salle_attente_id = salle_id

    return {
        "success": True,
        "patient_id": patient_id,
        "salle_id": salle_id,
        "places_restantes": salle.places_disponibles(),
    }


# ==================== SURVEILLANCE DES SALLES ====================


def assigner_surveillance(state: EmergencyState, staff_id: str, salle_id: str) -> Dict[str, Any]:
    """
    Assigne un membre du personnel à la surveillance d'une salle.

    Args:
        state: État du système
        staff_id: ID du staff
        salle_id: ID de la salle

    Returns:
        Résultat de l'opération
    """
    staff = next((s for s in state.staff if s.id == staff_id), None)
    if not staff:
        return {"success": False, "error": "Staff introuvable"}

    # Vérifier que c'est une infirmière mobile ou aide-soignant
    if staff.type not in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT]:
        return {
            "success": False,
            "error": "Seules infirmières mobiles et aides-soignants peuvent surveiller",
        }

    if not staff.peut_partir():
        return {"success": False, "error": "Staff pas disponible (contrainte 15 min)"}

    salle = next((s for s in state.salles_attente if s.id == salle_id), None)
    if not salle:
        return {"success": False, "error": "Salle introuvable"}

    # Assigner
    staff.localisation = salle_id
    staff.occupe_depuis = datetime.now()
    salle.surveillee_par = staff_id
    salle.derniere_surveillance = datetime.now()

    return {"success": True, "staff_id": staff_id, "salle_id": salle_id}


# ==================== TRANSPORT VERS CONSULTATION ====================


def demarrer_transport_consultation(
    state: EmergencyState, patient_id: str, staff_id: str
) -> Dict[str, Any]:
    """
    Démarre le transport d'un patient vers la consultation (5 min).

    Args:
        state: État du système
        patient_id: ID du patient
        staff_id: ID de l'infirmière mobile ou aide-soignant

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.SALLE_ATTENTE:
        return {"success": False, "error": "Patient pas en salle d'attente"}

    # Vérifier que la consultation est libre
    if not state.consultation.est_libre():
        return {"success": False, "error": "Consultation occupée"}

    # Vérifier le staff
    staff = next((s for s in state.staff if s.id == staff_id), None)
    if not staff:
        return {"success": False, "error": "Staff introuvable"}

    if staff.type not in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT]:
        return {
            "success": False,
            "error": "Seules infirmières mobiles et aides-soignants peuvent transporter",
        }

    if not staff.peut_partir():
        return {"success": False, "error": "Staff pas disponible"}

    # Retirer patient de la salle d'attente
    if patient.salle_attente_id:
        salle = next(
            (s for s in state.salles_attente if s.id == patient.salle_attente_id), None
        )
        if salle and patient_id in salle.patients:
            salle.patients.remove(patient_id)

    # Démarrer transport (5 min)
    patient.statut = StatutPatient.EN_TRANSPORT_CONSULTATION
    patient.salle_attente_id = None

    staff.en_transport = True
    staff.patient_transporte_id = patient_id
    staff.destination_transport = "consultation"
    staff.fin_transport_prevue = datetime.now() + timedelta(minutes=5)
    staff.disponible = False

    return {
        "success": True,
        "patient_id": patient_id,
        "staff_id": staff_id,
        "arrivee_prevue": staff.fin_transport_prevue.isoformat(),
        "duree_min": 5,
    }


def finaliser_transport_consultation(state: EmergencyState, patient_id: str) -> Dict[str, Any]:
    """
    Finalise l'arrivée d'un patient en consultation.
    À appeler quand les 5 min de transport sont écoulées.

    Args:
        state: État du système
        patient_id: ID du patient

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.EN_TRANSPORT_CONSULTATION:
        return {"success": False, "error": "Patient pas en transport"}

    # Libérer le transporteur
    transporteur = next(
        (s for s in state.staff if s.patient_transporte_id == patient_id), None
    )
    if transporteur:
        transporteur.en_transport = False
        transporteur.patient_transporte_id = None
        transporteur.destination_transport = None
        transporteur.fin_transport_prevue = None
        transporteur.disponible = True
        transporteur.occupe_depuis = None

    # Placer en consultation
    patient.statut = StatutPatient.EN_CONSULTATION
    state.consultation.patient_id = patient_id
    state.consultation.debut_consultation = datetime.now()

    return {
        "success": True,
        "patient_id": patient_id,
        "debut_consultation": state.consultation.debut_consultation.isoformat(),
    }


# ==================== CONSULTATION MÉDICALE ====================


def terminer_consultation(
    state: EmergencyState, patient_id: str, unite_cible: UniteCible
) -> Dict[str, Any]:
    """
    Termine la consultation et détermine la destination du patient.

    Durées de consultation selon gravité:
    - ROUGE: 1-5 min → Soins critiques
    - JAUNE: 20-40 min → Unité spécialisée
    - VERT: 10-25 min → Unité spécialisée
    - GRIS: 5-15 min → Maison

    Args:
        state: État du système
        patient_id: ID du patient
        unite_cible: Destination (SOINS_CRITIQUES, CARDIO, PNEUMO, NEURO, ORTHO, MAISON)

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.EN_CONSULTATION:
        return {"success": False, "error": "Patient pas en consultation"}

    # Vérifier cohérence gravité / destination
    if patient.gravite == Gravite.GRIS and unite_cible != UniteCible.MAISON:
        return {"success": False, "error": "Patient GRIS doit retourner à la maison"}

    if patient.gravite == Gravite.ROUGE and unite_cible not in [
        UniteCible.SOINS_CRITIQUES,
        UniteCible.CARDIO,
        UniteCible.PNEUMO,
        UniteCible.NEURO,
    ]:
        return {
            "success": False,
            "error": "Patient ROUGE doit aller en soins critiques ou unité spécialisée",
        }

    # Si destination = unité (pas maison), vérifier disponibilité
    if unite_cible != UniteCible.MAISON:
        unite = state.get_unite(unite_cible)
        if not unite:
            return {"success": False, "error": "Unité introuvable"}
        if not unite.a_de_la_place():
            return {"success": False, "error": f"Unité {unite_cible.value} pleine"}

    # Terminer consultation
    patient.unite_cible = unite_cible
    patient.consultation_end_at = datetime.now()

    # Si GRIS (maison), patient sort directement
    if unite_cible == UniteCible.MAISON:
        patient.statut = StatutPatient.SORTI
        state.consultation.patient_id = None
        state.consultation.debut_consultation = None
        return {
            "success": True,
            "patient_id": patient_id,
            "destination": "Maison",
            "statut_final": "SORTI",
        }

    # Sinon, patient attend transport
    patient.statut = StatutPatient.ATTENTE_TRANSPORT_SORTIE
    state.consultation.patient_id = None
    state.consultation.debut_consultation = None

    return {
        "success": True,
        "patient_id": patient_id,
        "destination": unite_cible.value,
        "statut": "Attente transport vers unité",
    }


# ==================== RETOUR EN SALLE D'ATTENTE ====================


def retourner_patient_salle_attente(
    state: EmergencyState,
    patient_id: str,
    staff_id: str,
    salle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retourne un patient en salle d'attente (si pas de transport dispo).
    Transport = 5 min.

    Args:
        state: État du système
        patient_id: ID du patient
        staff_id: ID de l'infirmière mobile
        salle_id: Salle de destination (auto si None)

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.ATTENTE_TRANSPORT_SORTIE:
        return {"success": False, "error": "Patient pas en attente de transport"}

    # Vérifier staff
    staff = next((s for s in state.staff if s.id == staff_id), None)
    if not staff or staff.type != TypeStaff.INFIRMIERE_MOBILE:
        return {
            "success": False,
            "error": "Seule une infirmière mobile peut retourner le patient",
        }

    if not staff.peut_partir():
        return {"success": False, "error": "Infirmière pas disponible"}

    # Choisir salle automatiquement si pas spécifié
    if not salle_id:
        salles_dispo = [s for s in state.salles_attente if not s.est_pleine()]
        if not salles_dispo:
            return {"success": False, "error": "Aucune salle d'attente disponible"}
        salle = max(salles_dispo, key=lambda s: s.places_disponibles())
        salle_id = salle.id

    salle = next((s for s in state.salles_attente if s.id == salle_id), None)
    if not salle or salle.est_pleine():
        return {"success": False, "error": "Salle indisponible"}

    # Placer en salle (directement, pas de simulation transport ici pour simplifier)
    salle.patients.append(patient_id)
    patient.statut = StatutPatient.SALLE_ATTENTE
    patient.salle_attente_id = salle_id

    staff.occupe_depuis = datetime.now()

    return {
        "success": True,
        "patient_id": patient_id,
        "salle_id": salle_id,
        "message": "Patient retourné en salle d'attente, prioritaire pour transport",
    }


# ==================== TRANSPORT VERS UNITÉ ====================


def demarrer_transport_unite(
    state: EmergencyState, patient_id: str, staff_id: str
) -> Dict[str, Any]:
    """
    Démarre le transport d'un patient vers une unité.

    Durées:
    - ROUGE → Soins critiques: 5 min
    - Autres → Unités: 45 min

    Args:
        state: État du système
        patient_id: ID du patient
        staff_id: ID de l'aide-soignant

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut not in [
        StatutPatient.ATTENTE_TRANSPORT_SORTIE,
        StatutPatient.SALLE_ATTENTE,
    ]:
        return {"success": False, "error": "Patient pas prêt pour transport"}

    if not patient.unite_cible:
        return {"success": False, "error": "Pas de destination définie"}

    # Vérifier que c'est un aide-soignant
    staff = next((s for s in state.staff if s.id == staff_id), None)
    if not staff or staff.type != TypeStaff.AIDE_SOIGNANT:
        return {
            "success": False,
            "error": "Seul un aide-soignant peut faire ce transport",
        }

    if not staff.peut_partir():
        return {"success": False, "error": "Aide-soignant pas disponible"}

    # Vérifier disponibilité unité
    unite = state.get_unite(patient.unite_cible)
    if not unite or not unite.a_de_la_place():
        return {"success": False, "error": f"Unité {patient.unite_cible.value} pleine"}

    # Retirer de salle d'attente si nécessaire
    if patient.salle_attente_id:
        salle = next(
            (s for s in state.salles_attente if s.id == patient.salle_attente_id), None
        )
        if salle and patient_id in salle.patients:
            salle.patients.remove(patient_id)
        patient.salle_attente_id = None

    # Déterminer durée transport
    if (
        patient.gravite == Gravite.ROUGE
        and patient.unite_cible == UniteCible.SOINS_CRITIQUES
    ):
        duree_min = 5
    else:
        duree_min = 45

    # Démarrer transport
    patient.statut = StatutPatient.EN_TRANSPORT_SORTIE

    staff.en_transport = True
    staff.patient_transporte_id = patient_id
    staff.destination_transport = patient.unite_cible.value
    staff.fin_transport_prevue = datetime.now() + timedelta(minutes=duree_min)
    staff.doit_revenir_avant = datetime.now() + timedelta(
        minutes=60
    )  # Contrainte 60 min
    staff.disponible = False

    return {
        "success": True,
        "patient_id": patient_id,
        "staff_id": staff_id,
        "destination": patient.unite_cible.value,
        "duree_min": duree_min,
        "arrivee_prevue": staff.fin_transport_prevue.isoformat(),
    }


def finaliser_transport_unite(state: EmergencyState, patient_id: str) -> Dict[str, Any]:
    """
    Finalise l'arrivée d'un patient dans une unité.

    Args:
        state: État du système
        patient_id: ID du patient

    Returns:
        Résultat de l'opération
    """
    patient = state.patients.get(patient_id)
    if not patient:
        return {"success": False, "error": "Patient introuvable"}

    if patient.statut != StatutPatient.EN_TRANSPORT_SORTIE:
        return {"success": False, "error": "Patient pas en transport"}

    # Ajouter à l'unité
    unite = state.get_unite(patient.unite_cible)
    if not unite:
        return {"success": False, "error": "Unité introuvable"}

    unite.patients.append(patient_id)
    patient.statut = StatutPatient.SORTI

    # Libérer l'aide-soignant
    transporteur = next(
        (s for s in state.staff if s.patient_transporte_id == patient_id), None
    )
    if transporteur:
        transporteur.en_transport = False
        transporteur.patient_transporte_id = None
        transporteur.destination_transport = None
        transporteur.fin_transport_prevue = None
        transporteur.disponible = True
        transporteur.occupe_depuis = None

    return {
        "success": True,
        "patient_id": patient_id,
        "unite": patient.unite_cible.value,
        "statut_final": "SORTI (dans unité)",
    }


# ==================== OUTILS INFORMATIFS ====================


def get_etat_systeme(state: EmergencyState) -> Dict[str, Any]:
    """Retourne l'état complet du système."""
    return state.to_dict()


def get_prochain_patient_consultation(state: EmergencyState) -> Optional[dict]:
    """Retourne le prochain patient à appeler en consultation."""
    queue = state.get_queue_consultation()
    if not queue:
        return None

    patient = queue[0]
    return {
        "patient_id": patient.id,
        "nom": f"{patient.prenom} {patient.nom}",
        "gravite": patient.gravite.value,
        "temps_attente_min": patient.temps_attente_minutes(),
        "salle_attente": patient.salle_attente_id,
    }


def get_prochain_patient_transport(state: EmergencyState) -> Optional[dict]:
    """Retourne le prochain patient à transporter vers une unité."""
    queue = state.get_queue_transport_sortie()
    if not queue:
        return None

    patient = queue[0]
    return {
        "patient_id": patient.id,
        "nom": f"{patient.prenom} {patient.nom}",
        "gravite": patient.gravite.value,
        "destination": (
            patient.unite_cible.value if patient.unite_cible else "Non définie"
        ),
    }


def get_alertes(state: EmergencyState) -> Dict[str, Any]:
    """Retourne les alertes du système."""
    alertes = {
        "surveillance": state.verifier_surveillance_salles(),
        "aides_soignants_temps": [],
        "consultation_libre": state.consultation.est_libre(),
        "patients_longue_attente": [],
    }

    # Aides-soignants bientôt hors temps
    for staff in state.staff:
        if staff.type == TypeStaff.AIDE_SOIGNANT:
            temps_restant = staff.temps_disponible_restant()
            if temps_restant is not None and temps_restant < 10:
                alertes["aides_soignants_temps"].append(
                    f" {staff.id} doit revenir dans {temps_restant} min"
                )

    # Patients >360 min
    for patient in state.patients.values():
        if (
            patient.statut == StatutPatient.SALLE_ATTENTE
            and patient.temps_attente_minutes() > 360
        ):
            alertes["patients_longue_attente"].append(
                f" {patient.id} attend depuis {patient.temps_attente_minutes()} min (PRIORITÉ)"
            )

    return alertes
