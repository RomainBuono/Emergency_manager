"""
Monitoring Package
~~~~~~~~~~~~~~~~~~
Suivi des métriques LLM : coût, latence, impact écologique.
"""

from .monitoring import monitor, MetricsTracker, RequestMetrics
from .rag_augmented import call_model, call_model_with_messages

__all__ = [
    "monitor",
    "MetricsTracker",
    "RequestMetrics",
    "call_model",
    "call_model_with_messages"
]
