"""
RAG Package for Emergency Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Système RAG (Retrieval-Augmented Generation) avec guardrails de sécurité.
"""

from .engine import HospitalRAGEngine
from .models import RAGResponse, MedicalProtocol, HospitalRule
from .guardrails import RAGGuardrail, GuardrailConfig, GuardrailResult, BlockReason

__all__ = [
    "HospitalRAGEngine",
    "RAGResponse",
    "MedicalProtocol",
    "HospitalRule",
    "RAGGuardrail",
    "GuardrailConfig",
    "GuardrailResult",
    "BlockReason",
]

__version__ = "1.0.0"