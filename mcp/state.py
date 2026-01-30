"""Modèles de données Pydantic pour l'état du système d'urgences."""
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
from enum import Enum
from datetime import datetime
from typing import List, Dict, Optional,Tuple

# Pydantic est le standard industriel pour la validation de données en Python
from pydantic import BaseModel, Field


class Gravite(str, Enum):
    """Niveaux de gravité des patients."""
    ROUGE = "ROUGE"  # Vital + urgent
    JAUNE = "JAUNE"  # Non vital mais urgent
    VERT = "VERT"  # Non vital, non urgent
    GRIS = "GRIS"  # Ne nécessite pas les urgences


class UniteCible(str, Enum):
    """Unités de destination possibles."""
    CARDIO = "Cardiologie"
    PNEUMO = "Pneumologie"
    NEURO = "Neurologie"
    ORTHO = "Orthopédie"
    SOINS_CRITIQUES = "Soins Critiques"
    MAISON = "Maison"


class StatutPatient(str, Enum):
    """États possibles d'un patient."""
    ATTENTE_TRIAGE = "attente_triage"
    SALLE_ATTENTE = "salle_attente"
    EN_TRANSPORT_CONSULTATION = "en_transport_consultation"
    EN_CONSULTATION = "en_consultation"
    ATTENTE_TRANSPORT_SORTIE = "attente_transport_sortie"
    EN_TRANSPORT_SORTIE = "en_transport_sortie"
    SORTI = "sorti"


class TypeStaff(str, Enum):
    """Types de personnel."""
    MEDECIN = "médecin"
    INFIRMIERE_FIXE = "infirmier(ere)_fixe"
    INFIRMIERE_MOBILE = "infirmier(ere)_mobile"
    AIDE_SOIGNANT = "aide_soignant"


class Patient(BaseModel):
    """Patient aux urgences."""
    id: str
    prenom: str
    nom: str
    gravite: Gravite
    symptomes: str
    age: int
    antecedents: list[str] = Field(default_factory=list)
    # Timestamps
    arrived_at: datetime = Field(default_factory=datetime.now)
    consultation_end_at: Optional[datetime] = None

    # État actuel
    statut: StatutPatient = StatutPatient.ATTENTE_TRIAGE
    salle_attente_id: Optional[str] = None # "salle_attente_1", "salle_attente_2", "salle_attente_3"

    # Décision médicale (après consultation)
    unite_cible: Optional[UniteCible] = None

    class Config:
        use_enum_values = True

    def temps_attente_minutes(self, now: datetime) -> int:
        """Retourne le temps d'attente en minutes."""
        return int((now  - self.arrived_at).total_seconds() / 60)

    def priorite_queue(self, now: datetime) -> Tuple[int, datetime]:
        """Calcule la priorité dans la queue selon les règles."""
        temps_attente = self.temps_attente_minutes(now)
        # ROUGE toujours en premier
        if self.gravite == Gravite.ROUGE:
            return (0, self.arrived_at)
        # VERT >360 min passe avant JAUNE
        if self.gravite == Gravite.VERT and temps_attente > 360:
            return (1, self.arrived_at)
        # JAUNE normal
        if self.gravite == Gravite.JAUNE:
            return (2, self.arrived_at)
        # VERT <360 min
        if self.gravite == Gravite.VERT:
            return (3, self.arrived_at)
        # GRIS en dernier
        return (4, self.arrived_at)


class SalleAttente(BaseModel):
    """Salle d'attente avec capacité."""
    id: str  # "salle_attente_1", "salle_attente_2", "salle_attente_3"
    capacite: int  # 5, 10, ou 5
    patients: list[str] = Field(default_factory=list)  # IDs des patients
    surveillee_par: Optional[str] = None  # ID du staff
    derniere_surveillance: datetime = Field(default_factory=datetime.now)

    def places_disponibles(self) -> int:
        """Nombre de places libres."""
        return self.capacite - len(self.patients)

    def est_pleine(self) -> bool:
        """Vérifie si la salle est pleine."""
        return len(self.patients) >= self.capacite

    def temps_sans_surveillance(self, now: datetime) -> int:
        """Minutes sans surveillance."""
        return int((now - self.derniere_surveillance).total_seconds() / 60)


class Consultation(BaseModel):
    """Salle de consultation (1 seule place)."""
    patient_id: Optional[str] = None
    debut_consultation: Optional[datetime] = None

    def est_libre(self) -> bool:
        """Vérifie si libre."""
        return self.patient_id is None


class Unite(BaseModel):
    """Unité de destination (Cardio, Pneumo, etc.)."""
    nom: UniteCible
    capacite: int
    patients: list[str] = Field(default_factory=list)

    def a_de_la_place(self) -> bool:
        """Vérifie si l'unité peut accueillir un patient."""
        return len(self.patients) < self.capacite


class Staff(BaseModel):
    """Personnel médical."""
    id: str
    type: TypeStaff
    disponible: bool = True
    localisation: str = "repos"  # "triage", "salle_attente_X", "consultation", etc.
    salle_surveillee: Optional[str] = None
    # Pour contraintes temporelles
    occupe_depuis: Optional[datetime] = None
    doit_revenir_avant: Optional[datetime] = None  # Pour aides-soignants (60 min max)
    # Pour transport en cours
    en_transport: bool = False
    patient_transporte_id: Optional[str] = None
    destination_transport: Optional[str] = None
    fin_transport_prevue: Optional[datetime] = None

    # Dans state.py, modifiez la méthode peut_partir
    def peut_partir(self, now: datetime) -> bool:
        """Vérifie si le staff peut quitter sa position."""
        # L'infirmière de triage est statique par définition
        if self.type == TypeStaff.INFIRMIERE_FIXE:
            return False
    
        # Un staff en plein transport ne peut pas être réassigné
        if not self.disponible or self.en_transport:
            return False

        # Réduction de la contrainte temporelle de 15 min à 5 min pour la simulation
        if self.occupe_depuis:
            temps_occupe = (now - self.occupe_depuis).total_seconds() / 60
            if temps_occupe < 5: 
                return False
            
        return True

    def temps_disponible_restant(self, now: datetime) -> Optional[int]:
        """Minutes restantes avant de devoir revenir (pour aides-soignants)."""
        if self.type != TypeStaff.AIDE_SOIGNANT or not self.doit_revenir_avant:
            return None
    
        delta = (self.doit_revenir_avant - now).total_seconds() / 60
        return max(0, int(delta))

class EmergencyState:
    """État global du service des urgences."""
    def __init__(self):

        self.salles_attente = [
            SalleAttente(id="salle_attente_1", capacite=5),
            SalleAttente(id="salle_attente_2", capacite=10),
            SalleAttente(id="salle_attente_3", capacite=5),
        ]

        self.consultation = Consultation()
# A modifier (par une variable locale si besion )
        self.unites = [
            Unite(nom=UniteCible.SOINS_CRITIQUES, capacite=5),
            Unite(nom=UniteCible.CARDIO, capacite=10),
            Unite(nom=UniteCible.PNEUMO, capacite=10),
            Unite(nom=UniteCible.NEURO, capacite=8),
            Unite(nom=UniteCible.ORTHO, capacite=10),
        ]

        self.staff = self._init_staff()
        self.patients: dict[str, Patient] = {}
        self.current_time = datetime.now()


    def _init_staff(self) -> list[Staff]:
        """Initialise le personnel selon les contraintes."""
        return [
            # 1 médecin fixe en consultation
            Staff(id="Medecin", type=TypeStaff.MEDECIN, localisation="consultation"),
            # 1 infirmière fixe au triage (ne bouge JAMAIS)
            Staff(id="Infirmier(ère) Triage", type=TypeStaff.INFIRMIERE_FIXE),
            # 2 infirmières mobiles (B & C)
            Staff(
                id="Infirmier(ère) B",
                type=TypeStaff.INFIRMIERE_MOBILE
            ),
            Staff(
                id="Infirmier(ère) C",
                type=TypeStaff.INFIRMIERE_MOBILE
            ),
            # 2 aides-soignants
            Staff(id="Aide Soignant(e) A", type=TypeStaff.AIDE_SOIGNANT),
            Staff(id="Aide Soignant(e) B", type=TypeStaff.AIDE_SOIGNANT),
        ]

    def get_queue_consultation(self) -> list[Patient]:
        """Retourne la file d'attente pour consultation (triée par priorité)."""
        now = self.current_time
        patients_en_attente = [
            p for p in self.patients.values()
            if p.statut == StatutPatient.SALLE_ATTENTE
        ]
        return sorted(patients_en_attente, key=lambda p: p.priorite_queue(now))

    def get_queue_transport_sortie(self) -> list[Patient]:
        """File d'attente pour transport vers unités (après consultation)."""
        now = self.current_time
        patients_attente_transport = [
            p for p in self.patients.values()
            if p.statut == StatutPatient.ATTENTE_TRANSPORT_SORTIE
        ]
        return sorted(patients_attente_transport, key=lambda p: p.priorite_queue(now))

    def get_staff_disponible(self, type_staff: TypeStaff) -> list[Staff]:
        """Retourne le personnel disponible d'un type donné."""
        now = self.current_time
        return [
            s for s in self.staff
            if s.type == type_staff and s.peut_partir(now) and not s.en_transport
        ]

    def get_unite(self, nom: UniteCible) -> Optional[Unite]:
        """Récupère une unité par son nom."""
        return next((u for u in self.unites if u.nom == nom), None)

    def verifier_surveillance_salles(self) -> list[str]:
        """Vérifie les salles sans surveillance > 15 min."""
        now = self.current_time
        alertes = []
        for salle in self.salles_attente:
            # Une salle est surveillée si un staff a cet ID en 'salle_surveillee' 
            # ET qu'il n'est pas en cours de transport
            surveillee = any(
                s.salle_surveillee == salle.id and not s.en_transport 
                for s in self.staff
            )
        
            if not surveillee:
                mins = salle.temps_sans_surveillance(now)
                # Règle critique des 15 minutes
                if mins > 15 and len(salle.patients) > 0:
                    alertes.append(f"⚠️ {salle.id} sans surveillance depuis {mins} min")
        return alertes

    def to_dict(self) -> dict:
        """Convertit l'état en dict JSON-serializable."""
        return {
            "salles_attente": [s.model_dump() for s in self.salles_attente],
            "consultation": self.consultation.model_dump(),
            "unites": [u.model_dump() for u in self.unites],
            "staff": [self._serialize_staff(s) for s in self.staff],
            "patients": {k: self._serialize_patient(v) for k, v in self.patients.items()},
            "queue_consultation": [p.id for p in self.get_queue_consultation()],
            "queue_transport": [p.id for p in self.get_queue_transport_sortie()],
            "alertes_surveillance": self.verifier_surveillance_salles(),
            "current_time": self.current_time.isoformat(),
        }

    @staticmethod
    def _serialize_patient(p: Patient) -> dict:
        """Sérialise un patient."""
        data = p.model_dump()
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @staticmethod
    def _serialize_staff(s: Staff) -> dict:
        """Sérialise un membre du personnel pour l'API."""
        data = s.model_dump()
        # Ajout dynamique du temps restant pour l'agent
        # Note: 'now' doit être passé ou récupéré du state
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
