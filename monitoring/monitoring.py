from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Tentative d'initialisation d'EcoLogits
try:
    from ecologits import EcoLogits

    EcoLogits.init(providers="litellm", electricity_mix_zone="FRA")
    ECOLOGITS_AVAILABLE = True
except ImportError:
    ECOLOGITS_AVAILABLE = False
except Exception:
    ECOLOGITS_AVAILABLE = False


@dataclass
class RequestMetrics:
    """Métriques d'une requête individuelle."""

    timestamp: datetime
    source: str  # "agent", "chatbot", "rag"
    model_name: str
    input_tokens: int
    output_tokens: int
    dollar_cost: float
    energy_kwh: float
    co2_kg: float
    latency_ms: float


class MetricsTracker:
    """
    Tracker de métriques pour le monitoring LLM.

    Fonctionnalités:
    - Calcul du coût par requête (_get_price_query)
    - Impact écologique via EcoLogits (énergie kWh, CO2 kgCO2eq)
    - Suivi par composant (Agent, RAG, Chatbot)
    - Historique des requêtes pour visualisation
    """

    def __init__(self):
        # Dictionnaire des prix ($ / 1 Million de tokens)
        # Source: https://mistral.ai/fr/technology/
        self.prices = {
            "ministral-14b-2512": {"input": 0.2, "output": 0.2},
            "ministral-3b-2512": {"input": 0.1, "output": 0.1},
            "magistral-small-2509": {"input": 0.5, "output": 1.5},
            "codestral-latest": {"input": 0.3, "output": 0.9},
            "mistral-large-latest": {"input": 0.5, "output": 1.5},
            "ministral-8b-latest": {"input": 0.1, "output": 0.1},
            "mistral-small-latest": {"input": 0.2, "output": 0.6},
        }

        # Accumulateurs globaux pour le dashboard
        self.total_dollar_cost = 0.0
        self.total_energy_kwh = 0.0
        self.total_co2_kg = 0.0
        self.total_latency_ms = 0.0
        self.request_count = 0

        # Accumulateurs par composant
        self.by_source: Dict[str, Dict[str, float]] = {
            "agent": {
                "cost": 0.0,
                "energy": 0.0,
                "co2": 0.0,
                "latency": 0.0,
                "count": 0,
            },
            "chatbot": {
                "cost": 0.0,
                "energy": 0.0,
                "co2": 0.0,
                "latency": 0.0,
                "count": 0,
            },
            "rag": {"cost": 0.0, "energy": 0.0, "co2": 0.0, "latency": 0.0, "count": 0},
        }

        # Historique des requêtes (pour graphiques)
        self.request_history: List[RequestMetrics] = []
        self.max_history_size = 100

    def _get_price_query(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calcule le coût d'une requête en dollars.

        Args:
            model_name: Nom du modèle LLM utilisé
            input_tokens: Nombre de tokens en entrée
            output_tokens: Nombre de tokens en sortie

        Returns:
            Coût total en dollars
        """
        # Nettoyage du nom du modèle (enlever préfixe mistral/ si présent)
        model_key = model_name.split("/")[-1]
        config = self.prices.get(model_key, self.prices["mistral-large-latest"])

        input_cost = (input_tokens / 1_000_000) * config["input"]
        output_cost = (output_tokens / 1_000_000) * config["output"]

        return input_cost + output_cost

    def log_metrics(
        self, response, latency_ms: float, model_name: str, source: str = "rag"
    ) -> Dict[str, Any]:
        """
        Extrait et enregistre les métriques d'une réponse LiteLLM.

        Args:
            response: Réponse LiteLLM (avec usage et impacts EcoLogits)
            latency_ms: Latence de la requête en millisecondes
            model_name: Nom du modèle utilisé
            source: Origine de la requête ("agent", "chatbot", "rag")

        Returns:
            Dictionnaire avec les métriques de cette requête
        """
        # 1. Extraction des tokens
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # 2. Calcul du coût
        dollar_cost = self._get_price_query(model_name, input_tokens, output_tokens)

        # 3. Impact écologique via EcoLogits
        if ECOLOGITS_AVAILABLE and hasattr(response, "impacts") and response.impacts:
            energy_value = response.impacts.energy.value
            energy_usage = getattr(energy_value, "min", energy_value)
            co2_value = response.impacts.gwp.value
            co2_impact = getattr(co2_value, "min", co2_value)
        else:
            # Estimation si EcoLogits non disponible
            # Approximation: ~0.0002 kWh par 1000 tokens (GPU inference)
            total_tokens = input_tokens + output_tokens
            energy_usage = (total_tokens / 1000) * 0.0002
            # Mix électrique France: ~0.052 kgCO2eq/kWh (source: RTE)
            co2_impact = energy_usage * 0.052

        # 4. Mise à jour des totaux globaux
        self.total_dollar_cost += dollar_cost
        self.total_energy_kwh += energy_usage
        self.total_co2_kg += co2_impact
        self.total_latency_ms += latency_ms
        self.request_count += 1

        # 5. Mise à jour par source
        if source in self.by_source:
            self.by_source[source]["cost"] += dollar_cost
            self.by_source[source]["energy"] += energy_usage
            self.by_source[source]["co2"] += co2_impact
            self.by_source[source]["latency"] += latency_ms
            self.by_source[source]["count"] += 1

        # 6. Ajout à l'historique
        metrics = RequestMetrics(
            timestamp=datetime.now(),
            source=source,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            dollar_cost=dollar_cost,
            energy_kwh=energy_usage,
            co2_kg=co2_impact,
            latency_ms=latency_ms,
        )
        self.request_history.append(metrics)

        # Limiter la taille de l'historique
        if len(self.request_history) > self.max_history_size:
            self.request_history = self.request_history[-self.max_history_size :]

        return {
            "dollar_cost": dollar_cost,
            "energy_kwh": energy_usage,
            "co2_kg": co2_impact,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "source": source,
        }

    def log_metrics_simple(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        model_name: str,
        source: str = "rag",
    ) -> Dict[str, Any]:
        """
        Enregistre les métriques sans réponse LiteLLM (pour appels directs).

        Utile quand on n'a pas accès à l'objet response complet.
        """
        dollar_cost = self._get_price_query(model_name, input_tokens, output_tokens)

        # Estimation de l'impact écologique
        total_tokens = input_tokens + output_tokens
        energy_usage = (total_tokens / 1000) * 0.0002
        # Mix électrique France: ~0.052 kgCO2eq/kWh (source: RTE)
        co2_impact = energy_usage * 0.052

        # Mise à jour des totaux
        self.total_dollar_cost += dollar_cost
        self.total_energy_kwh += energy_usage
        self.total_co2_kg += co2_impact
        self.total_latency_ms += latency_ms
        self.request_count += 1

        if source in self.by_source:
            self.by_source[source]["cost"] += dollar_cost
            self.by_source[source]["energy"] += energy_usage
            self.by_source[source]["co2"] += co2_impact
            self.by_source[source]["latency"] += latency_ms
            self.by_source[source]["count"] += 1

        metrics = RequestMetrics(
            timestamp=datetime.now(),
            source=source,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            dollar_cost=dollar_cost,
            energy_kwh=energy_usage,
            co2_kg=co2_impact,
            latency_ms=latency_ms,
        )
        self.request_history.append(metrics)

        if len(self.request_history) > self.max_history_size:
            self.request_history = self.request_history[-self.max_history_size :]

        return {
            "dollar_cost": dollar_cost,
            "energy_kwh": energy_usage,
            "co2_kg": co2_impact,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "source": source,
        }

    def get_stats_by_source(self, source: str) -> Dict[str, float]:
        """Retourne les statistiques pour une source donnée."""
        return self.by_source.get(source, {})

    def get_average_latency(self, source: Optional[str] = None) -> float:
        """Retourne la latence moyenne (globale ou par source)."""
        if source and source in self.by_source:
            count = self.by_source[source]["count"]
            return self.by_source[source]["latency"] / max(1, count)
        return self.total_latency_ms / max(1, self.request_count)

    def get_recent_history(self, n: int = 10) -> List[RequestMetrics]:
        """Retourne les n dernières requêtes."""
        return self.request_history[-n:]

    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé complet des métriques."""
        return {
            "global": {
                "total_cost": self.total_dollar_cost,
                "total_energy_kwh": self.total_energy_kwh,
                "total_co2_kg": self.total_co2_kg,
                "avg_latency_ms": self.get_average_latency(),
                "total_requests": self.request_count,
            },
            "by_source": self.by_source,
            "recent_requests": len(self.request_history),
        }

    def reset(self):
        """Réinitialise toutes les métriques."""
        self.total_dollar_cost = 0.0
        self.total_energy_kwh = 0.0
        self.total_co2_kg = 0.0
        self.total_latency_ms = 0.0
        self.request_count = 0

        for source in self.by_source:
            self.by_source[source] = {
                "cost": 0.0,
                "energy": 0.0,
                "co2": 0.0,
                "latency": 0.0,
                "count": 0,
            }

        self.request_history = []


# Instance globale à importer dans les autres fichiers
monitor = MetricsTracker()
