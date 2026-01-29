"""
Package RAG - Retrieval Augmented Generation
"""

# Permettre l'import direct depuis rag
from .engine import HospitalRAGEngine
from .guardrails import RAGGuardrail, GuardrailConfig
from .models import RAGResponse, MedicalProtocol, HospitalRule

__all__ = [
    'HospitalRAGEngine',
    'RAGGuardrail',
    'GuardrailConfig',
    'RAGResponse',
    'MedicalProtocol',
    'HospitalRule'
]