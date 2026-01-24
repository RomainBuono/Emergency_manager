import pickle
import numpy as np
from pathlib import Path
from typing import Final, List, Dict, Optional, Any

# Librairies tierces conformes aux standards de sécurité
from datasets import load_dataset, concatenate_datasets, Dataset
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report

class GuardrailTrainer:
    """
    Classe responsable de la préparation des données et de l'entraînement 
    du modèle HistGradientBoosting pour la sécurité du RAG hospitalier.
    """
    
    # Constantes typées selon PEP 484 [cite: 4, 22]
    MODEL_NAME: Final[str] = 'paraphrase-multilingual-MiniLM-L12-v2'
    SAFE_SAMPLE_SIZE: Final[int] = 3000

    def __init__(self, storage_dir: str = "storage"):
        """Initialise le formateur avec un répertoire de stockage sécurisé."""
        self.storage_path: Final[Path] = Path(__file__).parent / storage_dir
        self.encoder: Final[SentenceTransformer] = SentenceTransformer(self.MODEL_NAME)
        self.model: Optional[HistGradientBoostingClassifier] = None

    def _normalize_dataset(self, dataset: Dataset, label_map: Dict[int, int], query_col: str) -> Dataset:
        """Normalise les colonnes pour assurer la compatibilité lors de la fusion."""
        return dataset.map(
            lambda x: {"query": x[query_col], "label": label_map.get(x.get("label", 0), 0)},
            remove_columns=dataset.column_names
        )

    def prepare_data(self) -> Dataset:
        """Télécharge, normalise et fusionne les datasets de sécurité."""
        print("Chargement des datasets (Injections & Safe)...")
        
        # Injections : deepset & jackhhao
        ds_inj = load_dataset("deepset/prompt-injections", split="train+test")
        ds_inj_norm = self._normalize_dataset(ds_inj, {0: 0, 1: 1}, "text")
        
        # Requêtes saines : HuggingFaceH4
        ds_safe = load_dataset("HuggingFaceH4/helpful-instructions", split="train")
        ds_safe_sample = ds_safe.shuffle(seed=42).select(range(self.SAFE_SAMPLE_SIZE))
        
        ds_safe_norm = ds_safe_sample.map(
            lambda x: {"query": x.get("prompt") or x.get("text") or x.get("instruction"), "label": 0},
            remove_columns=ds_safe_sample.column_names
        )
        
        # Fusion des sources
        full_ds = concatenate_datasets([ds_inj_norm, ds_safe_norm])
        
        # NETTOYAGE CRITIQUE : Supprime les NoneType pour éviter le crash de l'encodeur
        return full_ds.filter(
            lambda x: x["query"] is not None and isinstance(x["query"], str) and len(x["query"].strip()) > 0
        )

    def train(self) -> None:
        """Exécute le pipeline complet : Nettoyage -> Embedding -> Entraînement -> Évaluation."""
        dataset = self.prepare_data()
        print(f"Données nettoyées : {len(dataset)} échantillons prêts.")

        split = dataset.train_test_split(test_size=0.2, seed=42)
        
        # 1. Génération des embeddings avec typage strict [cite: 24]
        print("Génération des embeddings (Inférence)...")
        train_queries: List[str] = [str(q) for q in split["train"]["query"]]
        x_train = self.encoder.encode(train_queries, show_progress_bar=True)
        y_train = np.array(split["train"]["label"])
        
        # 2. Modèle HistGradientBoosting avec paramètres optimisés
        self.model = HistGradientBoostingClassifier(
            learning_rate=0.2,     # Optimisé
            max_iter=250,          # Optimisé
            max_depth=10,          # Optimisé
            min_samples_leaf=20,   # Optimisé
            random_state=42,
            verbose=1
        )
        print("Entraînement du classifieur de sécurité...")
        self.model.fit(x_train, y_train)
        
        # 3. Évaluation finale
        print("Évaluation des performances...")
        test_queries: List[str] = [str(q) for q in split["test"]["query"]]
        x_test = self.encoder.encode(test_queries, show_progress_bar=False)
        y_test = np.array(split["test"]["label"])
        report = self.evaluate(x_test, y_test)
        print("\nClassification Report (Guardrail):\n", report)
        
        self.save_model()

    def evaluate(self, x_test: np.ndarray, y_test: np.ndarray) -> str:
        """Génère le rapport de performance Precision/Recall/F1."""
        if self.model is None:
            raise ValueError("Le modèle doit être entraîné avant l'évaluation.")
        
        y_pred = self.model.predict(x_test)
        return classification_report(y_test, y_pred, target_names=["Safe", "Threat"])

    def save_model(self) -> None:
        """Sauvegarde le modèle optimisé au format Pickle."""
        self.storage_path.mkdir(exist_ok=True)
        file_path = self.storage_path / "guardrail.pkl"
       
        with open(file_path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"✅ Modèle sauvegardé avec succès : {file_path}")

if __name__ == "__main__":
    trainer = GuardrailTrainer()
    trainer.train()