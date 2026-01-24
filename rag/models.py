"""
Data Models
~~~~~~~~~~~

Pydantic models for medical protocols, hospital rules, and RAG responses.
Backward compatible with existing codebase.
"""

from typing import Optional
from pydantic import BaseModel, Field


class MedicalProtocol(BaseModel):
    """
    Medical protocol data model.
    
    Attributes:
        id: Unique protocol identifier.
        pathologie: Medical condition name.
        symptomes: List of associated symptoms.
        gravite: Severity level (ROUGE, JAUNE, VERT, GRIS).
        unite_cible: Target hospital unit.
        examens_urgents: Urgent exams required (optional, for guardrail).
    """
    
    id: str
    pathologie: str
    symptomes: list[str]
    gravite: str = Field(pattern="^(ROUGE|JAUNE|VERT|GRIS)$")
    unite_cible: str
    examens_urgents: Optional[list[str]] = None  # Ajouté pour guardrail
    
    class Config:
        """Allow extra fields for flexibility."""
        extra = "allow"


class HospitalRule(BaseModel):
    """
    Hospital operational rule with flexible schema.
    
    Attributes:
        id: Unique rule identifier.
        type: Rule type/category.
        titre: Rule title.
        texte_complet: Complete rule text.
        regle: Short rule description (optional).
        conditions: List of conditions (optional).
        ordre_traitement: Processing order (default 0).
        gravite: Applicable severity level (optional).
        exception: Exception description (optional).
        nombre: Number field (optional).
        noms: Names list (optional).
        localisation: Location field (optional).
        role: Role list (optional).
    """
    
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
        """Allow extra fields for flexibility."""
        extra = "allow"


class RAGResponse(BaseModel):
    """
    Response from RAG engine with security verification.
    
    Compatible with legacy code using 'applicable_rules' field.
    
    Attributes:
        is_safe: Whether query passed all guardrail layers.
        threat_probability: Injection threat score (0.0-1.0).
        latency_ms: Query processing time in milliseconds.
        relevance_score: RAG similarity score (0.0-1.0). NEW FIELD.
        status: Human-readable status message.
        protocol: Retrieved medical protocol (if safe).
        applicable_rules: Applicable hospital rules (LEGACY NAME).
        rules: Alias for applicable_rules (for new code).
    """
    
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
        Alias for applicable_rules.
        
        Provides backward compatibility while allowing new code
        to use the simpler 'rules' name.
        """
        return self.applicable_rules
    
    class Config:
        """Allow extra fields for flexibility."""
        extra = "allow"