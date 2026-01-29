"""
Package MCP - Emergency Management
"""

# Permettre l'import direct depuis mcp
from .state import (
    EmergencyState,
    Patient,
    Gravite,
    UniteCible,
    StatutPatient,
    TypeStaff,
    SalleAttente,
    Consultation,
    Unite,
    Staff
)

__all__ = [
    'EmergencyState',
    'Patient',
    'Gravite',
    'UniteCible',
    'StatutPatient',
    'TypeStaff',
    'SalleAttente',
    'Consultation',
    'Unite',
    'Staff'
]