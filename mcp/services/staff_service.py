"""Service de gestion du personnel - Migré depuis tools.py"""

import logging
from datetime import timedelta
from typing import List, Optional

from ..state import EmergencyState, Staff, TypeStaff

logger = logging.getLogger(__name__)


class StaffService:
    """Service métier pour la gestion du personnel."""
    
    def __init__(self, state: EmergencyState) -> None:
        self._state = state
    
    def find_available_staff(
        self,
        staff_type: TypeStaff,
        exclude_in_transport: bool = True
    ) -> List[Staff]:
        """Trouve le personnel disponible d'un type donné."""
        available = []
        for staff in self._state.staff:
            if staff.type != staff_type:
                continue
            if exclude_in_transport and staff.en_transport:
                continue
            if not staff.peut_partir(self._state.current_time):
                continue
            available.append(staff)
        return available
    
    def assigner_surveillance(self, staff_id: str, room_id: str) -> None:
        """Assigne surveillance"""
        staff = self._get_staff_by_id(staff_id)
        if not staff:
            raise ValueError(f"Staff {staff_id} introuvable")
        
        if staff.type not in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT]:
            raise ValueError("Staff invalide pour surveillance")
        
        if not staff.peut_partir(self._state.current_time):
            raise ValueError("Staff non disponible")
        
        salle = next((s for s in self._state.salles_attente if s.id == room_id), None)
        if not salle:
            raise ValueError("Salle introuvable")
        
        # Libérer ancienne salle
        if staff.salle_surveillee:
            ancienne = next(
                (s for s in self._state.salles_attente if s.id == staff.salle_surveillee),
                None
            )
            if ancienne:
                ancienne.surveillee_par = None
        
        staff.localisation = room_id
        staff.salle_surveillee = room_id
        staff.occupe_depuis = self._state.current_time
        salle.surveillee_par = staff_id
        salle.derniere_surveillance = self._state.current_time
    
    def verifier_et_gerer_surveillance(self) -> List[str]:
        """Auto-assignation"""
        actions = []
        for salle in self._state.salles_attente:
            if len(salle.patients) > 0 and not salle.surveillee_par:
                staff_dispo = [
                    s for s in self._state.staff
                    if s.type in [TypeStaff.INFIRMIERE_MOBILE, TypeStaff.AIDE_SOIGNANT]
                    and s.disponible
                    and not s.en_transport
                    and s.localisation == "repos"
                ]
                if staff_dispo:
                    try:
                        self.assign_room_surveillance(staff_dispo[0].id, salle.id)
                        actions.append(f"📋 Surveillance auto : {staff_dispo[0].id} → {salle.id}")
                    except ValueError:
                        pass
        return actions
    
    def release_staff(self, staff_id: str) -> None:
        """Libère un membre du personnel."""
        staff = self._get_staff_by_id(staff_id)
        if not staff:
            return
        
        staff.disponible = True
        staff.en_transport = False
        staff.patient_transporte_id = None
        staff.destination_transport = None
        staff.fin_transport_prevue = None
        staff.occupe_depuis = None
        staff.doit_revenir_avant = None
        
        if staff.salle_surveillee:
            staff.localisation = staff.salle_surveillee
        else:
            staff.localisation = "repos"
    
    def _get_staff_by_id(self, staff_id: str) -> Optional[Staff]:
        return next((s for s in self._state.staff if s.id == staff_id), None)