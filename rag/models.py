from pydantic import BaseModel, Field
from typing import List, Optional


class MedicalProtocol(BaseModel):
    """Modèle pour les protocoles médicaux."""
    id: str
    pathologie: str
    symptomes: List[str]
    gravite: str = Field(pattern="^(ROUGE|JAUNE|VERT|GRIS)$")
    unite_cible: str


class HospitalRule(BaseModel):
    """Modèle flexible pour les règles logistiques hospitalières."""
    id: str
    type: str
    titre: str
    texte_complet: str
    regle: Optional[str] = None
    # On rend conditions optionnel car certaines règles n'en ont pas (ex: FIFO)
    conditions: Optional[List[str]] = [] 
    # Valeurs par défaut pour les champs numériques et optionnels
    ordre_traitement: int = 0
    gravite: Optional[str] = None
    exception: Optional[str] = None
    
    # Champs additionnels détectés dans votre JSON pour éviter d'autres erreurs
    nombre: Optional[int] = None
    noms: Optional[List[str]] = None
    localisation: Optional[str] = None
    role: Optional[List[str]] = None

# A remodifier si besion
class RAGResponse(BaseModel): 
    """Contrat d'interface pour l'Agent et le Dashboard."""
    is_safe: bool
    protocol: Optional[MedicalProtocol] = None
    applicable_rules: List[HospitalRule] = []
    threat_probability: float = 0.0
    latency_ms: float
    status: str