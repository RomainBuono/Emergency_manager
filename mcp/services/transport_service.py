"""Service de gestion des transports"""

import logging
from datetime import timedelta
from typing import Tuple

from ..state import EmergencyState, StatutPatient, Gravite, UniteCible, TypeStaff


logger = logging.getLogger(__name__)


class TransportService:
    """Service métier pour la gestion des transports de patients."""
    
    DUREE_TRANSPORT_CONSULTATION = 5
    DUREE_TRANSPORT_UNITE_ROUGE = 5
    DUREE_TRANSPORT_UNITE_AUTRES = 45
    
    def __init__(self, state: EmergencyState, patient_service, staff_service) -> None:
        self._state = state
        self._patient_service = patient_service
        self._staff_service = staff_service
    
    def demarrer_transport_consultation(
        self,
        patient_id: str,
        staff_id: str
    ) -> Tuple[bool, str]:
        """Démarre transport vers consultation."""
        patient = self._patient_service.get_patient(patient_id)
        staff = next((s for s in self._state.staff if s.id == staff_id), None)
        
        if not patient or not staff:
            return False, "Patient ou Staff introuvable"
        
        if not self._state.consultation.est_libre():
            return False, "Consultation occupée"
        
        if not staff.peut_partir(self._state.current_time):
            return False, "Staff non disponible"
        
        # Libérer salle d'attente
        if patient.salle_attente_id:
            salle = next(
                (s for s in self._state.salles_attente if s.id == patient.salle_attente_id),
                None
            )
            if salle and patient_id in salle.patients:
                salle.patients.remove(patient_id)
        
        # Mise à jour patient
        patient.statut = StatutPatient.EN_TRANSPORT_CONSULTATION
        patient.salle_attente_id = None
        self._state.consultation.patient_id = patient_id
        
        # Mise à jour staff
        staff.en_transport = True
        staff.patient_transporte_id = patient_id
        staff.destination_transport = "consultation"
        staff.fin_transport_prevue = (
            self._state.current_time + timedelta(minutes=self.DUREE_TRANSPORT_CONSULTATION)
        )
        staff.disponible = False
        
        logger.info(f"🚑 Transport {patient_id} → consultation")
        
        return True, f"Arrivée : {staff.fin_transport_prevue.isoformat()}"
    
    def finaliser_transport_consultation(self, patient_id: str) -> Tuple[bool, str]:
        """Finalise arrivée en consultation (remplace tools.finaliser_transport_consultation)."""
        patient = self._patient_service.get_patient(patient_id)
        if not patient or patient.statut != StatutPatient.EN_TRANSPORT_CONSULTATION:
            return False, "Patient pas en transport"
        
        # Libérer transporteur
        transporteur = next(
            (s for s in self._state.staff if s.patient_transporte_id == patient_id),
            None
        )
        if transporteur:
            self._staff_service.release_staff(transporteur.id)
        
        patient.statut = StatutPatient.EN_CONSULTATION
        self._state.consultation.patient_id = patient_id
        self._state.consultation.debut_consultation = self._state.current_time
        
        logger.info(f"✅ Patient {patient_id} en consultation")
        
        return True, "Consultation démarrée"
    
    def terminer_consultation(
        self,
        patient_id: str,
        unite_cible: UniteCible
    ) -> Tuple[bool, str]:
        """Termine consultation."""
        patient = self._patient_service.get_patient(patient_id)
        if not patient or patient.statut != StatutPatient.EN_CONSULTATION:
            return False, "Patient pas en consultation"
        
        if patient.gravite == Gravite.ROUGE and unite_cible == UniteCible.MAISON:
            return False, "Incohérence : ROUGE ne peut pas sortir"
        
        patient.unite_cible = unite_cible
        patient.consultation_end_at = self._state.current_time
        self._state.consultation.patient_id = None
        
        if unite_cible == UniteCible.MAISON:
            patient.statut = StatutPatient.SORTI
        else:
            patient.statut = StatutPatient.ATTENTE_TRANSPORT_SORTIE
        
        return True, f"Destination : {unite_cible}"
    
    def retourner_patient_salle_attente(
        self,
        patient_id: str,
        staff_id: str,
        room_id: str = None
    ) -> Tuple[bool, str]:
        """Retourne en salle."""
        patient = self._patient_service.get_patient(patient_id)
        if not patient or patient.statut != StatutPatient.ATTENTE_TRANSPORT_SORTIE:
            return False, "Patient non prêt pour retour"
        
        if not room_id:
            salles_dispo = [s for s in self._state.salles_attente if not s.est_pleine()]
            if not salles_dispo:
                return False, "Aucune salle disponible"
            salle = max(salles_dispo, key=lambda s: s.places_disponibles())
            room_id = salle.id
        
        salle = next((s for s in self._state.salles_attente if s.id == room_id), None)
        if not salle:
            return False, "Salle introuvable"
        
        patient.statut = StatutPatient.SALLE_ATTENTE
        patient.salle_attente_id = room_id
        salle.patients.append(patient_id)
        
        return True, f"Retourné en {room_id}"
    
    def demarrer_transport_unite(
        self,
        patient_id: str,
        staff_id: str
    ) -> Tuple[bool, str]:
        """Démarre transport vers unité."""
        patient = self._patient_service.get_patient(patient_id)
        staff = next((s for s in self._state.staff if s.id == staff_id), None)
        
        if not patient or not staff:
            return False, "Patient ou Staff introuvable"
        
        if not patient.unite_cible:
            return False, "Aucune unité cible"
        
        unite = self._state.get_unite(patient.unite_cible)
        if not unite or not unite.a_de_la_place():
            return False, f"Unité {patient.unite_cible} saturée"
        
        if staff.type not in [TypeStaff.AIDE_SOIGNANT, TypeStaff.INFIRMIERE_MOBILE]:
            return False, "Type personnel non autorisé"
        
        if not staff.peut_partir(self._state.current_time):
            return False, "Staff non disponible"
        
        # Calcul durée (5 min ROUGE, 45 min autres)
        duree = (
            self.DUREE_TRANSPORT_UNITE_ROUGE
            if patient.gravite == Gravite.ROUGE
            else self.DUREE_TRANSPORT_UNITE_AUTRES
        )
        
        # Libérer salle
        if patient.salle_attente_id:
            salle = next(
                (s for s in self._state.salles_attente if s.id == patient.salle_attente_id),
                None
            )
            if salle and patient_id in salle.patients:
                salle.patients.remove(patient_id)
            patient.salle_attente_id = None
        
        patient.statut = StatutPatient.EN_TRANSPORT_SORTIE
        
        staff.en_transport = True
        staff.disponible = False
        staff.patient_transporte_id = patient_id
        staff.destination_transport = patient.unite_cible
        staff.fin_transport_prevue = self._state.current_time + timedelta(minutes=duree)
        
        # Libérer surveillance
        if staff.salle_surveillee:
            salle_prec = next(
                (s for s in self._state.salles_attente if s.id == staff.salle_surveillee),
                None
            )
            if salle_prec:
                salle_prec.surveillee_par = None
            staff.salle_surveillee = None
        
        logger.info(f"🚑 Transport {patient_id} → {patient.unite_cible} ({duree} min)")
        
        return True, f"Arrivée : {staff.fin_transport_prevue.isoformat()} ({duree} min)"
    
    def finaliser_transport_unite(self, patient_id: str) -> Tuple[bool, str]:
        """Finalise arrivée en unité."""
        patient = self._patient_service.get_patient(patient_id)
        if not patient or patient.statut != StatutPatient.EN_TRANSPORT_SORTIE:
            return False, "Patient pas en transport"
        
        unite = self._state.get_unite(patient.unite_cible)
        if unite:
            unite.patients.append(patient_id)
        
        transporteur = next(
            (s for s in self._state.staff if s.patient_transporte_id == patient_id),
            None
        )
        if transporteur:
            self._staff_service.release_staff(transporteur.id)
        
        patient.statut = StatutPatient.SORTI
        
        logger.info(f"✅ Patient {patient_id} en {patient.unite_cible}")
        
        return True, f"Transféré en {patient.unite_cible}"