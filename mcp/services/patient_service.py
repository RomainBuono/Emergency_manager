"""
Service de gestion des patients
"""
import logging
from typing import Optional
from datetime import datetime

# Import depuis le module parent (mcp/)
from ..state import EmergencyState, Patient, StatutPatient, UniteCible

logger = logging.getLogger(__name__)


class PatientService:
    """
    Service métier pour toutes les opérations sur les patients.
    
    Responsabilités :
    - Ajout de patients avec validation
    - Assignation aux salles d'attente
    - Mise à jour de statut avec machine à états
    - Calculs de priorité et temps d'attente
    """
    
    def __init__(self, state: EmergencyState) -> None:
        """
        Initialise le service avec l'état global.
        
        Args:
            state: État global du système d'urgences
        """
        self._state = state
    
    def ajouter_patient(self, patient: Patient) -> None:
        """
        Ajoute un nouveau patient au système.
        
        Équivalent à tools.ajouter_patient() mais avec exceptions
        au lieu de dict de retour.
        
        Le patient est automatiquement mis en statut ATTENTE_TRIAGE
        avec le timestamp actuel.
        
        Args:
            patient: Patient à ajouter
            
        Raises:
            ValueError: Si l'ID patient existe déjà
        """
        if patient.id in self._state.patients:
            raise ValueError(f"Patient ID {patient.id} déjà existant")
        
        # Initialisation des timestamps et statut
        patient.arrived_at = self._state.current_time
        patient.statut = StatutPatient.ATTENTE_TRIAGE
        
        # Ajout à l'état global
        self._state.patients[patient.id] = patient
        
        logger.info(
            "✅ Patient %s %s ajouté (ID: %s, gravité : %s)",
            patient.prenom,
            patient.nom,
            patient.id,
            patient.gravite
            )
    
    def assigner_salle_attente(
        self,
        patient_id: str,
        room_id: Optional[str] = None
    ) -> str:
        """
        Assigne un patient à une salle d'attente.
        
        Équivalent à tools.assigner_salle_attente() mais retourne
        l'ID de la salle au lieu d'un dict.
        
        Sélectionne automatiquement
        la salle avec le plus de places disponibles.
        """
        # Validation patient
        patient = self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")
        
        # Auto-sélection de la salle si non spécifiée
        if not room_id:
            salles_dispo = [
                s for s in self._state.salles_attente 
                if not s.est_pleine()
            ]
            
            if not salles_dispo:
                raise ValueError("Toutes les salles d'attente sont pleines")
            
            # Choisir la salle avec le plus de places disponibles
            salle = max(salles_dispo, key=lambda s: s.places_disponibles())
            room_id = salle.id
        
        # Validation de la salle
        salle = next(
            (s for s in self._state.salles_attente if s.id == room_id),
            None
        )
        
        if not salle:
            raise ValueError(f"Salle {room_id} introuvable")
        
        if salle.est_pleine():
            raise ValueError(
                f"Salle {room_id} pleine "
                f"(capacité : {salle.capacite}, patients : {len(salle.patients)})"
            )
        
        # Assignation
        salle.patients.append(patient_id)
        patient.statut = StatutPatient.SALLE_ATTENTE
        patient.salle_attente_id = room_id
        
        logger.info(
            "Patient %s assigné à %s (%d/%d places occupées)",
            patient_id,
            room_id,
            len(salle.patients),
            salle.capacite
        )
        
        return room_id
    
    def sortir_patient(self, patient_id: str) -> None:
        """Sortie manuelle."""
        patient = self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")
        
        patient.statut = StatutPatient.SORTI
        logger.info("Patient %s sorti", patient_id)
    
    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """
        Récupère un patient par son ID.
        
        Méthode utilitaire pour accéder aux patients de manière sûre.
        
        Args:
            patient_id: Identifiant unique du patient
            
        Returns:
            Patient si trouvé, None sinon
            
        """
        return self._state.patients.get(patient_id)
    
    def remove_from_waiting_room(self, patient_id: str) -> None:
        """
        Retire un patient de sa salle d'attente.
        
        Utile avant un transport vers consultation.
        
        Args:
            patient_id: ID du patient
        """
        patient = self.get_patient(patient_id)
        if not patient or not patient.salle_attente_id:
            return
        
        # Trouver la salle
        salle = next(
            (s for s in self._state.salles_attente 
             if s.id == patient.salle_attente_id),
            None
        )
        
        if salle and patient_id in salle.patients:
            salle.patients.remove(patient_id)
            logger.info("Patient %s retiré de %s", patient_id, salle.id)
        
        # Réinitialiser la référence
        patient.salle_attente_id = None
    
    def update_status(
        self,
        patient_id: str,
        new_status: StatutPatient
    ) -> None:
        """
        Met à jour le statut d'un patient avec validation de transition.
        
        NOUVEAU : Implémente une machine à états stricte pour garantir
        que seules les transitions valides sont autorisées.
        
        Transitions valides :
        - ATTENTE_TRIAGE → SALLE_ATTENTE
        - SALLE_ATTENTE → EN_TRANSPORT_CONSULTATION
        - EN_TRANSPORT_CONSULTATION → EN_CONSULTATION
        - EN_CONSULTATION → ATTENTE_TRANSPORT_SORTIE | SORTI
        - ATTENTE_TRANSPORT_SORTIE → EN_TRANSPORT_SORTIE | SALLE_ATTENTE
        - EN_TRANSPORT_SORTIE → SORTI
        
        Args:
            patient_id: ID du patient
            new_status: Nouveau statut souhaité
            
        Raises:
            ValueError: Si patient introuvable ou transition invalide
        """
        patient = self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")
        
        # Validation de la transition
        if not self._is_valid_transition(patient.statut, new_status):
            raise ValueError(
                f"Transition invalide : {patient.statut} → {new_status}"
            )
        
        # Mise à jour
        old_status = patient.statut
        patient.statut = new_status
        
        logger.info("Patient %s : %s → %s", patient_id, old_status, new_status)
    
    def get_wait_time_minutes(self, patient_id: str) -> int:
        """
        Calcule le temps d'attente d'un patient depuis son arrivée.
        
        Args:
            patient_id: ID du patient
            
        Returns:
            Temps d'attente en minutes (0 si patient introuvable)
        """
        patient = self.get_patient(patient_id)
        if not patient:
            return 0
        
        return patient.temps_attente_minutes(self._state.current_time)
    
    def demarrer_consultation(self, patient_id: str) -> None:
        """
        Marque le début officiel de la consultation médicale.
        
        Args:
            patient_id: L'identifiant unique du patient.
        """
        patient = self._state.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable.")
            
        patient.statut = StatutPatient.EN_CONSULTATION
        self._state.consultation.patient_id = patient_id
        self._state.consultation.debut_consultation = self._state.current_time

    def finaliser_consultation(self, patient_id: str, unite_cible: "UniteCible") -> None:

        """
        Termine la consultation et définit l'orientation du patient.
        
        Args:
            patient_id: ID du patient.
            unite_cible: Destination (Unité spécialisée ou Maison).
        """
        patient = self._state.patients.get(patient_id)
        if not patient or self._state.consultation.patient_id != patient_id:
            raise ValueError(f"Erreur de cohérence pour la consultation de {patient_id}.")

        patient.unite_cible = unite_cible
        self._state.consultation.patient_id = None
        self._state.consultation.debut_consultation = None
        
        if unite_cible == UniteCible.MAISON:
            patient.statut = StatutPatient.SORTI
        else:
            patient.statut = StatutPatient.ATTENTE_TRANSPORT_SORTIE
    # ==================== MÉTHODES PRIVÉES ====================
    
    def _is_valid_transition(
        self,
        current: StatutPatient,
        target: StatutPatient
    ) -> bool:
        """
        Vérifie si une transition de statut est valide.
        
        Implémente la machine à états du parcours patient.
        
        Args:
            current: Statut actuel
            target: Statut cible
            
        Returns:
            True si la transition est autorisée
        """
        valid_transitions = {
            StatutPatient.ATTENTE_TRIAGE: {
                StatutPatient.SALLE_ATTENTE
            },
            StatutPatient.SALLE_ATTENTE: {
                StatutPatient.EN_TRANSPORT_CONSULTATION
            },
            StatutPatient.EN_TRANSPORT_CONSULTATION: {
                StatutPatient.EN_CONSULTATION
            },
            StatutPatient.EN_CONSULTATION: {
                StatutPatient.ATTENTE_TRANSPORT_SORTIE,
                StatutPatient.SORTI
            },
            StatutPatient.ATTENTE_TRANSPORT_SORTIE: {
                StatutPatient.EN_TRANSPORT_SORTIE,
                StatutPatient.SALLE_ATTENTE  # Retour possible si unité saturée
            },
            StatutPatient.EN_TRANSPORT_SORTIE: {
                StatutPatient.SORTI
            },
        }
        
        return target in valid_transitions.get(current, set())