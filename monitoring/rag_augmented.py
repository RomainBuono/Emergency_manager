"""
RAG Augmented - Module d'appel LLM avec monitoring intégré.
"""

import time
from typing import Tuple, Optional
from .monitoring import monitor

try:
    import litellm

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


def call_model(model_name: str, prompt: str, source: str = "rag") -> Tuple[str, float]:
    """
    Appelle un modèle LLM via LiteLLM avec monitoring intégré.

    Args:
        model_name: Nom du modèle Mistral (ex: "mistral-small-latest")
        prompt: Prompt à envoyer au modèle
        source: Source de l'appel pour le tracking ("agent", "chatbot", "rag")

    Returns:
        Réponse du modèle, coût en dollars
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLM n'est pas installé")

    start_time = time.perf_counter()

    # Appel utilisant LiteLLM wrappé par EcoLogits
    response = litellm.completion(
        model=f"mistral/{model_name}", messages=[{"role": "user", "content": prompt}]
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Enregistrement des métriques avec la source
    metrics = monitor.log_metrics(response, latency_ms, model_name, source=source)
    dollar_cost = metrics["dollar_cost"]

    return response.choices[0].message.content, dollar_cost


def call_model_with_messages(
    model_name: str, messages: list, source: str = "chatbot"
) -> Tuple[str, dict]:
    """
    Appelle un modèle LLM avec un historique de messages.

    Args:
        model_name: Nom du modèle Mistral
        messages: Liste de messages au format OpenAI
        source: Source de l'appel pour le tracking

    Returns:
        Réponse du modèle, dictionnaire des métriques
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLM n'est pas installé")

    start_time = time.perf_counter()

    response = litellm.completion(model=f"mistral/{model_name}", messages=messages)

    latency_ms = (time.perf_counter() - start_time) * 1000

    metrics = monitor.log_metrics(response, latency_ms, model_name, source=source)

    return response.choices[0].message.content, metrics
