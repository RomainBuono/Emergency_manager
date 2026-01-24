"""
Data Models
~~~~~~~~~~~
Modèles Pydantic pour les protocoles médicaux, les règles hospitalières et les réponses RAG.
Rétrocompatible avec le code existant.
"""

from typing import Optional
from pydantic import BaseModel, Field


class MedicalProtocol(BaseModel):
    """ Modèle pour les protocoles médicaux. """
    
    id: str
    pathologie: str
    symptomes: list[str]
    gravite: str = Field(pattern="^(ROUGE|JAUNE|VERT|GRIS)$")
    unite_cible: str
    examens_urgents: Optional[list[str]] = None  # Ajouté pour guardrail
    
    class Config:
        """Prévoir des champs supplémentaires pour plus de flexibilité."""
        extra = "allow"


class HospitalRule(BaseModel):
    """Modèle flexible pour les règles logistiques hospitalières."""
    
    id: str
    type: str
    titre: str
    texte_complet: str
    regle: Optional[str] = None
    conditions: Optional[list[str]] = None
    ordre_traitement: int = 0
    gravite: Optional[str] = None
    exception: Optional[str] = None
    
    # Additional fields from JSON
    nombre: Optional[int] = None
    noms: Optional[list[str]] = None
    localisation: Optional[str] = None
    role: Optional[list[str]] = None
    
    class Config:
        """Prévoir des champs supplémentaires pour plus de flexibilité."""
        extra = "allow"


class RAGResponse(BaseModel):
    """Contrat d'interface pour l'Agent et le Dashboard."""
    
    is_safe: bool
    threat_probability: float = 0.0
    latency_ms: float = 0.0
    relevance_score: float = 0.0  # NOUVEAU champ requis
    status: str = ""
    protocol: Optional[MedicalProtocol] = None
    
    applicable_rules: list[HospitalRule] = Field(default_factory=list)
    
    @property
    def rules(self) -> list[HospitalRule]:
        """
        Alias ​​pour applicable_rules.
        Assure la compatibilité ascendante tout en permettant au nouveau code d'utiliser le nom plus simple « rules ».
        """
        return self.applicable_rules
    
    class Config:
        """Prévoir des champs supplémentaires pour plus de flexibilité."""
        extra = "allow"