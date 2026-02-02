"""Contrôleur principal pour orchestrer les services d'urgences."""

import logging
from datetime import timedelta
from typing import Dict, Any

from ..state import EmergencyState, Patient, UniteCible

# Import des services
from ..services.patient_service import PatientService
from ..services.staff_service import StaffService
from ..services.transport_service import TransportService

logger = logging.getLogger(__name__)


class EmergencyController:
    """
    Contrôleur principal pour l'orchestration des urgences.

    C'est le point d'entrée unique pour :
    - Dashboard (accès direct Python)
    - API FastAPI (pour l'agent externe)

    Responsabilités :
    - Orchestrer les 3 services (Patient, Staff, Transport)
    - Gérer le cycle de vie complet d'un patient
    - Faire progresser le temps (tick)
    - Fournir l'état global du système
    - Gérer les alertes

    Examples:
        >>> state = EmergencyState()
        >>> controller = EmergencyController(state)
        >>>
        >>> # Ajouter un patient
        >>> result = controller.add_patient(patient)
        >>> if result["success"]:
        ...     print("Patient ajouté !")
        >>>
        >>> # Faire progresser le temps
        >>> tick_result = controller.tick(minutes=5)
        >>> print(f"Événements : {tick_result['events']}")
    """

    def __init__(self, state: EmergencyState) -> None:
        """
        Initialise le contrôleur avec injection de dépendances.

        Args:
            state: État global du système d'urgences
        """
        self._state = state

        # Injection de dépendances - Création des services
        self._patient_service = PatientService(state)
        self._staff_service = StaffService(state)
        self._transport_service = TransportService(
            state, self._patient_service, self._staff_service
        )

        logger.info("EmergencyController initialisé")

    # ==================== GESTION DES PATIENTS ====================

    def ajouter_patient(self, patient: Patient) -> Dict[str, Any]:
        try:
            self._patient_service.ajouter_patient(patient)
            return {
                "success": True,
                "patient_id": patient.id,
                "gravite": patient.gravite,
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

    def ajouter_patient_avec_nom(
        self,
        prenom: str,
        nom: str,
        gravite: str = "VERT",
        age: int = None,
        symptomes: str = None,
    ) -> Dict[str, Any]:
        """Ajoute un patient avec nom spécifique (pour chatbot)."""
        import random, time

        patient_id = f"P{int(time.time()*1000) % 100000}-{random.randint(0, 999):03d}"

        if age is None:
            age = random.randint(18, 85)

        if symptomes is None:
            symptomes_map = {
                "ROUGE": ["Douleur thoracique", "AVC suspecté"],
                "JAUNE": ["Fracture", "Fièvre élevée"],
                "VERT": ["Consultation", "Contrôle"],
            }
            symptomes = random.choice(
                symptomes_map.get(gravite.upper(), ["Consultation"])
            )

        patient = Patient(
            id=patient_id,
            nom=nom,
            prenom=prenom,
            age=age,
            gravite=gravite.upper(),
            symptomes=symptomes,
            arrived_at=self._state.current_time.isoformat(),
        )

        try:
            self._patient_service.ajouter_patient(patient)
            assigned_room = self._patient_service.assigner_salle_attente(
                patient_id, None
            )

            return {
                "success": True,
                "patient_id": patient_id,
                "prenom": prenom,
                "nom": nom,
                "gravite": gravite,
                "salle": assigned_room,
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

    def assigner_salle_attente(
        self, patient_id: str, room_id: str = None
    ) -> Dict[str, Any]:
        """
        Assigne un patient à une salle d'attente.

        Args:
            patient_id: ID du patient
            room_id: ID de la salle (None pour auto-sélection)

        Returns:
            {"success": bool, "salle_id": str, "error": str}
        """
        try:
            assigned_room = self._patient_service.assigner_salle_attente(
                patient_id, room_id
            )
            return {"success": True, "salle_id": assigned_room}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # ==================== GESTION DU PERSONNEL ====================

    def assigner_surveillance(self, staff_id: str, room_id: str) -> Dict[str, Any]:
        """
        Assigne un membre du personnel à la surveillance d'une salle.

        Args:
            staff_id: ID du staff
            room_id: ID de la salle

        Returns:
            {"success": bool, "staff_id": str, "salle_id": str, "error": str}
        """
        try:
            self._staff_service.assigner_surveillance(staff_id, room_id)
            return {"success": True, "staff_id": staff_id, "salle_id": room_id}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    def verifier_et_gerer_surveillance(self) -> Dict[str, Any]:
        """
        Auto-assignation de la surveillance pour toutes les salles.

        Returns:
            {"success": bool, "actions": list[str]}
        """
        actions = self._staff_service.verifier_et_gerer_surveillance()
        return {"success": True, "actions": actions, "count": len(actions)}

    # ==================== TRANSPORTS VERS CONSULTATION ====================

    def demarrer_transport_consultation(
        self, patient_id: str, staff_id: str
    ) -> Dict[str, Any]:
        """
        Démarre le transport d'un patient vers la consultation.

        Args:
            patient_id: ID du patient
            staff_id: ID du transporteur

        Returns:
            {"success": bool, "arrivee_prevue": str, "error": str}
        """
        success, message = self._transport_service.demarrer_transport_consultation(
            patient_id, staff_id
        )

        if success:
            return {"success": True, "arrivee_prevue": message}
        else:
            return {"success": False, "error": message}

    def finaliser_transport_consultation(self, patient_id: str) -> Dict[str, Any]:
        """
        Finalise l'arrivée d'un patient en consultation.

        Args:
            patient_id: ID du patient

        Returns:
            {"success": bool, "debut": str, "error": str}
        """
        success, message = self._transport_service.finaliser_transport_consultation(
            patient_id
        )

        if success:
            return {"success": True, "debut": message}
        else:
            return {"success": False, "error": message}

    def terminer_consultation(
        self, patient_id: str, unite_cible: UniteCible
    ) -> Dict[str, Any]:
        """
        Termine une consultation et définit la destination.

        Args:
            patient_id: ID du patient
            unite_cible: Destination (unité ou maison)

        Returns:
            {"success": bool, "destination": str, "error": str}
        """
        success, message = self._transport_service.terminer_consultation(
            patient_id, unite_cible
        )

        if success:
            return {"success": True, "destination": unite_cible}
        else:
            return {"success": False, "error": message}

    # ==================== TRANSPORTS VERS UNITÉS ====================

    def retourner_patient_salle_attente(
        self, patient_id: str, staff_id: str, room_id: str = None
    ) -> Dict[str, Any]:
        """
        Retourne un patient en salle d'attente (si unité saturée).

        Args:
            patient_id: ID du patient
            staff_id: ID du staff (non utilisé actuellement)
            room_id: ID de la salle (None pour auto-sélection)

        Returns:
            {"success": bool, "message": str, "error": str}
        """
        success, message = self._transport_service.retourner_patient_salle_attente(
            patient_id, staff_id, room_id
        )

        if success:
            return {"success": True, "message": message}
        else:
            return {"success": False, "error": message}

    def demarrer_transport_unite(
        self, patient_id: str, staff_id: str
    ) -> Dict[str, Any]:
        """
        Démarre le transport d'un patient vers son unité cible.

        Args:
            patient_id: ID du patient
            staff_id: ID du transporteur

        Returns:
            {"success": bool, "duree_min": int, "arrivee_prevue": str, "error": str}
        """
        success, message = self._transport_service.demarrer_transport_unite(
            patient_id, staff_id
        )

        if success:
            # Extraire la durée du message si nécessaire
            return {"success": True, "arrivee_prevue": message}
        else:
            return {"success": False, "error": message}

    def finaliser_transport_unite(self, patient_id: str) -> Dict[str, Any]:
        """
        Finalise l'arrivée d'un patient dans son unité cible.

        Args:
            patient_id: ID du patient

        Returns:
            {"success": bool, "message": str, "error": str}
        """
        success, message = self._transport_service.finaliser_transport_unite(patient_id)

        if success:
            return {"success": True, "message": message}
        else:
            return {"success": False, "error": message}

    # ==================== MOTEUR ET ÉTAT (MIGRÉ DEPUIS tools.py) ====================

    def tick(self, minutes: int = 1) -> Dict[str, Any]:
        """
        Fait progresser le temps et gère les événements automatiques.
        """
        # 1. Avancement du temps global
        self._state.current_time += timedelta(minutes=minutes)
        events = []

        # 2. Vérification automatique des transports arrivés
        # On parcourt le staff pour voir qui a terminé son trajet
        for staff in self._state.staff:
            if staff.en_transport and staff.fin_transport_prevue:
                if self._state.current_time >= staff.fin_transport_prevue:
                    pid = staff.patient_transporte_id

                    if staff.destination_transport == "consultation":
                        # Utilise le service de transport pour finaliser
                        success, msg = (
                            self._transport_service.finaliser_transport_consultation(
                                pid
                            )
                        )
                        if success:
                            events.append(f"🚑 Patient {pid} arrivé en consultation")

                    else:
                        # Finalisation vers une unité (Cardio, Neuro, etc.)
                        success, msg = (
                            self._transport_service.finaliser_transport_unite(pid)
                        )
                        if success:
                            events.append(
                                f"🏥 Patient {pid} arrivé en unité spécialisée"
                            )

        # 3. Surveillance automatique des salles (optionnel, selon StaffService)
        # Vous pouvez ajouter ici un appel à staff_service pour réassigner le personnel
        # si une salle n'est plus surveillée.

        return {
            "success": True,
            "events": events,
            "now": self._state.current_time.isoformat(),
        }

    def get_etat_systeme(self) -> Dict[str, Any]:
        """
        Retourne l'état complet du système.

        Remplace tools.get_etat_systeme().

        Returns:
            État complet avec :
            - salles_attente
            - consultation
            - unites
            - staff
            - patients
            - queue_consultation
            - queue_transport
            - alertes_surveillance
            - current_time

        Examples:
            >>> state = controller.get_system_state()
            >>> print(f"Patients totaux : {len(state['patients'])}")
            >>> print(f"En consultation : {state['consultation']}")
        """
        return self._state.to_dict()

    def get_alertes(self) -> Dict[str, Any]:
        """
        Retourne toutes les alertes du système.

        Remplace tools.get_alertes().

        Alertes incluses :
        - Surveillance : salles sans surveillance > 15 min
        - Longue attente : patients en salle > 360 min (6h)

        Returns:
            {
                "surveillance": list[str],
                "longue_attente": list[str]
            }

        Examples:
            >>> alerts = controller.get_alerts()
            >>> for alert in alerts['surveillance']:
            ...     print(f"⚠️ {alert}")
            >>> for patient_id in alerts['longue_attente']:
            ...     print(f"⏰ Patient {patient_id} en attente > 6h")
        """
        # Alertes de surveillance (déjà implémenté dans state.py)
        surveillance_alerts = self._state.verifier_surveillance_salles()

        # Alertes de longue attente (> 360 minutes = 6 heures)
        longue_attente = [
            p.id
            for p in self._state.patients.values()
            if p.statut == "salle_attente"
            and p.temps_attente_minutes(self._state.current_time) > 360
        ]

        return {"surveillance": surveillance_alerts, "longue_attente": longue_attente}

    # ==================== MÉTHODES UTILITAIRES ====================

    def get_queue_consultation(self) -> Dict[str, Any]:
        """
        Retourne la file d'attente pour consultation (triée par priorité).

        Returns:
            {
                "patients": list[dict],
                "count": int
            }
        """
        queue = self._state.get_queue_consultation()

        return {
            "patients": [
                {
                    "id": p.id,
                    "nom": f"{p.prenom} {p.nom}",
                    "gravite": p.gravite,
                    "temps_attente": p.temps_attente_minutes(self._state.current_time),
                }
                for p in queue
            ],
            "count": len(queue),
        }

    def get_queue_transport_sortie(self) -> Dict[str, Any]:
        """
        Retourne la file d'attente pour transport vers unités.

        Returns:
            {
                "patients": list[dict],
                "count": int
            }
        """
        queue = self._state.get_queue_transport_sortie()

        return {
            "patients": [
                {
                    "id": p.id,
                    "nom": f"{p.prenom} {p.nom}",
                    "gravite": p.gravite,
                    "unite_cible": p.unite_cible,
                }
                for p in queue
            ],
            "count": len(queue),
        }
