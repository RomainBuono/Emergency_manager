"""
Action Executor for Emergency Chatbot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Execute les actions MCP parsees via le Controller.
"""

import random
import logging
from typing import List, Dict, Any
from datetime import datetime

from mcp.state import EmergencyState, Patient, Gravite, StatutPatient

logger = logging.getLogger("ActionExecutor")


class ActionExecutor:
    """
    Execute les actions MCP via l'EmergencyController.
    Le chatbot execute directement via le controller partage
    pour une latence reduite.
    """

    # Noms et prenoms pour generation aleatoire
    NOMS = [
        "Martin",
        "Bernard",
        "Dubois",
        "Thomas",
        "Robert",
        "Petit",
        "Durand",
        "Leroy",
        "Moreau",
        "Simon",
        "Laurent",
        "Lefebvre",
        "Besson",
        "Dumas",
        "Renaud",
        "Roux",
        "Dupont",
        "Lebrun",
        "Weber",
        "Payet",
        "Germain",
        "Müller",
        "Silva",
        "Nguyen",
        "García",
        "Smith",
        "Diallo",
        "Rossi",
        "Hassan",
        "Chen",
        "Kumar",
        "Ivanov",
        "Yılmaz",
        "Abubakar",
        "Kwon",
        "Sato",
        "Cohen",
        "Janssen",
        "Kamau",
        "O'Sullivan",
        "Petrov",
        "Fernandez",
        "Ben Saïd",
        "Traoré",
        "Sokolov",
        "Wang",
        "Novak",
        "Santos",
        "Singh",
        "Ibrahim",
    ]
    PRENOMS = [
        "Sophie",
        "Lucas",
        "Emma",
        "Thomas",
        "Lea",
        "Hugo",
        "Chloe",
        "Nathan",
        "Julie",
        "Mathis",
        "Marie",
        "Antoine",
        "Yasmine",
        "Kenji",
        "Aïcha",
        "Mateo",
        "Inès",
        "Liam",
        "Fatima",
        "Sasha",
        "Hiroshi",
        "Elena",
        "Amine",
        "Ji-woo",
        "Diego",
        "Zahra",
        "Lars",
        "Priya",
        "Samuel",
        "Mei",
        "Omar",
        "Svetlana",
        "Ravi",
        "Camille",
        "Malik",
        "Ananya",
        "Stefan",
        "Leila",
        "Dimitri",
        "Noa",
        "Kwame",
        "Ayumi",
        "Vladimir",
        "Chantal",
        "Rajesh",
        "Océane",
        "Tariq",
        "Sven",
        "Zeynep",
        "Moussa",
        "Aiko",
        "Matteo",
        "Jin",
        "Saliou",
        "Anya",
        "Isha",
        "Zayd",
        "Théo",
        "Linh",
        "Dante",
    ]

    def __init__(self, controller, state: EmergencyState):
        """
        Initialise l'executor.

        Args:
            controller: EmergencyController instance
            state: EmergencyState instance
        """
        self.controller = controller
        self.state = state

    def execute(self, action_plan) -> List[Dict[str, Any]]:
        """
        Execute toutes les actions du plan.
        Ex: "Ajoute 3 patients rouges avec une détresse respiratoire"
        -> Elle appelle _execute_ dans une boucle a 3 itérations.

        Args:
            action_plan: ActionPlan avec liste d'actions
        Returns:
            Liste des resultats pour chaque action

        """

        results = []

        for action in action_plan.actions:
            tool_name = action.get("tool", "")
            params = action.get("params", {})

            try:
                result = self._execute_single(tool_name, params)
                results.append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "success": result.get("success", False),
                        "result": result,
                    }
                )

            except Exception as e:
                logger.error(f"Action echouee: {tool_name} - {e}")
                results.append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def _execute_single(self, tool: str, params: Dict) -> Dict[str, Any]:
        """Execute une seule action MCP."""

        # Mapping des outils vers les methodes
        if tool == "ajouter_patient":
            return self._add_patient(**params)
        elif tool == "assigner_salle_attente":
            return self.controller.assigner_salle_attente(**params)
        elif tool == "demarrer_transport_consultation":
            return self._transport_consultation(**params)
        elif tool == "demarrer_transport_unite":
            return self._transport_unite(**params)
        elif tool == "assigner_surveillance":
            return self.controller.assigner_surveillance(**params)
        elif tool == "get_status":
            return self._get_status()
        elif tool == "list_patients":
            return self._list_patients()
        else:
            return {"success": False, "error": f"Outil inconnu: {tool}"}

    def _add_patient(
        self,
        gravite: str = "JAUNE",
        symptomes: str = "Symptomes non precises",
        prenom: str = None,
        nom: str = None,
        age: int = None,
        count: int = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Ajoute un ou plusieurs patients.
        Version v2.2 : Ne génère PAS de nom/prénom aléatoire si manquant.

        Args:
            gravite: Niveau de gravite (ROUGE, JAUNE, VERT, GRIS)
            symptomes: Description des symptomes
            prenom: Prénom du patient (si None et count=1 → "", sinon aléatoire)
            nom: Nom du patient (si None et count=1 → "", sinon aléatoire)
            age: Âge du patient (optionnel, aléatoire si None)
            count: Nombre de patients a ajouter (défaut 1)

        Returns:
            Resultat avec liste des patients ajoutes
        """
        # ✅ Gestion robuste de count
        if count is None:
            count = 1

        try:
            count = int(count)
            if count < 1:
                count = 1
        except (TypeError, ValueError):
            logger.warning(
                f"Valeur invalide pour count: {count}, utilisation de 1 par défaut"
            )
            count = 1

        # === DEBUG ===
        print(f"🔍 _add_patient appelé avec:")
        print(f"   - prenom: {prenom}")
        print(f"   - nom: {nom}")
        print(f"   - gravite: {gravite}")
        print(f"   - count: {count} (type: {type(count)})")
        # === FIN DEBUG ===

        added = []
        errors = []

        # Normaliser la gravite
        gravite_upper = gravite.upper()
        if gravite_upper not in ["ROUGE", "JAUNE", "VERT", "GRIS"]:
            gravite_upper = "JAUNE"

        # ✅ v2.2 : Si prenom OU nom fourni (mais pas les deux) et count=1
        # → Utiliser la méthode avec nom personnalisé (avec chaîne vide pour le manquant)
        if count == 1 and (prenom or nom):
            # Si on a au moins un des deux, on utilise la méthode personnalisée
            prenom_final = prenom if prenom else ""
            nom_final = nom if nom else ""

            try:
                result = self.controller.ajouter_patient_avec_nom(
                    prenom=prenom_final,
                    nom=nom_final,
                    gravite=gravite_upper,
                    age=age,
                    symptomes=symptomes,
                )

                if result.get("success"):
                    # Construire le nom d'affichage
                    nom_affichage = f"{prenom_final} {nom_final}".strip()
                    if not nom_affichage:
                        nom_affichage = "Patient sans nom"

                    added.append(
                        {
                            "patient_id": result["patient_id"],
                            "nom": nom_affichage,
                            "gravite": gravite_upper,
                            "salle": result.get("salle", "Non assigné"),
                        }
                    )
                else:
                    errors.append(result.get("error", "Erreur inconnue"))

                return {
                    "success": len(added) > 0,
                    "added_count": len(added),
                    "patients": added,
                    "errors": errors if errors else None,
                }

            except Exception as e:
                logger.error(f"Erreur ajout patient avec nom: {e}")
                return {"success": False, "error": str(e)}

        # ✅ v2.2 : Génération aléatoire UNIQUEMENT si count > 1 OU (prenom=None ET nom=None)
        for i in range(count):
            patient_id = f"P{random.randint(10000, 99999)}-{random.randint(0, 999):03d}"
            prenom_gen = prenom or random.choice(self.PRENOMS)
            nom_gen = nom or random.choice(self.NOMS)
            age_gen = age or random.randint(18, 85)

            try:
                patient = Patient(
                    id=patient_id,
                    prenom=prenom_gen,
                    nom=nom_gen,
                    gravite=Gravite[gravite_upper],
                    symptomes=symptomes,
                    age=age_gen,
                    antecedents=[],
                    arrived_at=self.state.current_time,
                    statut=StatutPatient.ATTENTE_TRIAGE,
                )

                # Ajouter le patient
                result = self.controller.ajouter_patient(patient)

                if result.get("success"):
                    # Assigner automatiquement a une salle
                    room_result = self.controller.assigner_salle_attente(patient_id)
                    added.append(
                        {
                            "patient_id": patient_id,
                            "nom": f"{prenom_gen} {nom_gen}",
                            "gravite": gravite_upper,
                            "salle": room_result.get("salle_id", "Non assigne"),
                        }
                    )
                else:
                    errors.append(f"{patient_id}: {result.get('error')}")

            except Exception as e:
                errors.append(f"Erreur creation patient: {str(e)}")

        return {
            "success": len(added) > 0,
            "added_count": len(added),
            "patients": added,
            "errors": errors if errors else None,
        }

    def _transport_consultation(self, patient_id: str, **kwargs) -> Dict[str, Any]:
        """
        Demarre le transport vers consultation.

        Trouve automatiquement un staff disponible.
        """
        # Trouver un staff disponible
        staff_dispo = self._find_available_staff()
        if not staff_dispo:
            return {
                "success": False,
                "error": "Aucun personnel disponible pour le transport",
            }

        return self.controller.demarrer_transport_consultation(patient_id, staff_dispo)

    def _transport_unite(self, patient_id: str, **kwargs) -> Dict[str, Any]:
        """
        Demarre le transport vers unite.

        Trouve automatiquement un staff disponible.
        """
        staff_dispo = self._find_available_staff()
        if not staff_dispo:
            return {
                "success": False,
                "error": "Aucun personnel disponible pour le transport",
            }

        return self.controller.demarrer_transport_unite(patient_id, staff_dispo)

    def _find_available_staff(self) -> str:
        """Trouve un membre du personnel disponible pour transport."""
        for staff in self.state.staff:
            if (
                staff.disponible
                and not staff.en_transport
                and staff.type.value in ["infirmier(ere)_mobile", "aide_soignant"]
            ):
                return staff.id
        return None

    def _get_status(self) -> Dict[str, Any]:
        """Recupere l'etat complet du systeme."""
        etat = self.controller.get_etat_systeme()
        patients = etat.get("patients", {})

        nb_total = len([p for p in patients.values() if p.get("statut") != "sorti"])
        nb_attente = len(
            [p for p in patients.values() if p.get("statut") == "salle_attente"]
        )
        nb_rouge = len(
            [
                p
                for p in patients.values()
                if p.get("gravite") == "ROUGE" and p.get("statut") != "sorti"
            ]
        )
        nb_jaune = len(
            [
                p
                for p in patients.values()
                if p.get("gravite") == "JAUNE" and p.get("statut") != "sorti"
            ]
        )
        nb_vert = len(
            [
                p
                for p in patients.values()
                if p.get("gravite") == "VERT" and p.get("statut") != "sorti"
            ]
        )

        # Etat consultation
        consultation = etat.get("consultation", {})
        consultation_libre = consultation.get("patient_id") is None

        # Staff disponible
        staff = etat.get("staff", [])
        staff_dispo = len(
            [s for s in staff if s.get("disponible") and not s.get("en_transport")]
        )

        return {
            "success": True,
            "summary": {
                "total_patients": nb_total,
                "en_attente": nb_attente,
                "rouge": nb_rouge,
                "jaune": nb_jaune,
                "vert": nb_vert,
                "consultation_libre": consultation_libre,
                "staff_disponible": staff_dispo,
                "heure_simulation": etat.get("current_time", ""),
            },
            "queues": {
                "consultation": len(etat.get("queue_consultation", [])),
                "transport": len(etat.get("queue_transport", [])),
            },
        }

    def _list_patients(self) -> Dict[str, Any]:
        """Liste tous les patients actifs."""
        etat = self.controller.get_etat_systeme()
        patients = etat.get("patients", {})

        patients_list = []
        for pid, p in patients.items():
            if p.get("statut") != "sorti":
                patients_list.append(
                    {
                        "id": pid,
                        "nom": f"{p.get('prenom', '')} {p.get('nom', '')}",
                        "gravite": p.get("gravite"),
                        "statut": p.get("statut"),
                        "salle": p.get("salle_attente_id", "N/A"),
                    }
                )

        # Trier par gravite (ROUGE en premier)
        ordre_gravite = {"ROUGE": 0, "JAUNE": 1, "VERT": 2, "GRIS": 3}
        patients_list.sort(key=lambda x: ordre_gravite.get(x["gravite"], 4))

        return {"success": True, "count": len(patients_list), "patients": patients_list}
