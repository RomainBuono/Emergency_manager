import pickle
import numpy as np
from pathlib import Path
from typing import Final, List, Dict, Optional, Any

# Librairies tierces
from datasets import load_dataset, concatenate_datasets, Dataset
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

class GuardrailTrainer:
    """
    Entraîne un classifieur de sécurité robuste pour RAG Hospitalier.
    Intègre désormais des attaques multilingues (MultiJail) et un contexte médical.
    """
    
    # Constantes
    MODEL_NAME: Final[str] = 'paraphrase-multilingual-MiniLM-L12-v2'
    STORAGE_DIR: Final[str] = "storage"

    def __init__(self):
        """Initialise le formateur et l'encodeur."""
        self.storage_path: Final[Path] = Path(__file__).parent / self.STORAGE_DIR
        print(f"[INFO] Initialisation de l'encodeur {self.MODEL_NAME}...")
        self.encoder: Final[SentenceTransformer] = SentenceTransformer(self.MODEL_NAME)
        self.model: Optional[HistGradientBoostingClassifier] = None

    def _normalize_dataset(self, dataset: Dataset, text_col: str, label_val: int) -> Dataset:
        """
        Normalise n'importe quel dataset vers le format standard:
        {'text': str, 'label': int}
        """
        # On renomme la colonne texte en 'text' et on force le label
        return dataset.map(
            lambda x: {"text": x[text_col], "label": label_val},
            remove_columns=dataset.column_names
        )

    def _get_medical_safe_queries(self) -> Dataset:
        """Génère des requêtes médicales légitimes pour éviter les faux positifs."""
        queries = [
            "Patient douleur thoracique dyspnée", "Fièvre élevée enfant 5 ans",
            "Fracture ouverte bras droit", "Suspicion AVC paralysie faciale",
            "Crise asthme sévère SpO2 88%", "Douleur abdominale aiguë",
            "Trauma crânien perte conscience", "Hémorragie digestive vomissements",
            "Convulsions généralisées", "Détresse respiratoire nourrisson",
            "Vertiges nausées persistants", "Confusion mentale personne âgée",
            "Brûlure deuxième degré", "Réaction allergique urticaire",
            "Douleur lombaire irradiant", "Céphalée intense photophobie",
            "Palpitations essoufflement", "Plaie profonde sutures",
            "Intoxication déshydratation", "Douleur thoracique effort",
            "Symptômes infarctus?", "Comment reconnaître AVC?",
            "Que faire brûlure grave?", "Quand appeler urgences?",
            "Comment administrer garrot?", "Signes déshydratation enfant",
            "Différence ROUGE JAUNE", "Protocole accueil urgences",
            "Temps attente VERT", "Unités soins disponibles",
            "Chest pain and difficulty breathing", # EN
            "Dolor torácico y dificultad para respirar", # ES
            "Brustschmerzen und Atembeschwerden", # DE
        ]
        # On amplifie x100 pour donner du poids face aux milliers d'attaques
        return Dataset.from_dict({"text": queries * 100, "label": [0] * (len(queries) * 100)})

    def prepare_data(self) -> Dataset:
        """Charge et fusionne les sources: Deepset, MultiJail, Medical, Wikitext."""
        print("[INFO] Chargement des datasets...")
        
        datasets_list = []

        # 1. ATTACK: Deepset Prompt Injections (Anglais standard)
        print("  - [Charge] deepset/prompt-injections...")
        ds_deepset = load_dataset("deepset/prompt-injections", split="train")
        # On ne garde que les labels 1 (injections) de ce dataset pour être pur
        ds_deepset = ds_deepset.filter(lambda x: x['label'] == 1)
        datasets_list.append(self._normalize_dataset(ds_deepset, "text", 1))

        # 2. ATTACK: MultiJail (Multilingue - Le nouveau dataset clé)
        print("  - [Charge] DAMO-NLP-SG/MultiJail (Multilingue)...")
        try:
            ds_multijail = load_dataset("DAMO-NLP-SG/MultiJail", split="train")
            datasets_list.append(self._normalize_dataset(ds_multijail, "prompt", 1))
        except Exception as e:
            print(f"  [WARN] MultiJail indisponible ({e}), on continue sans.")

        # 3. SAFE: Requêtes Médicales (Domain Specific)
        print("  - [Génère] Données Médicales (Safe)...")
        datasets_list.append(self._get_medical_safe_queries())

        # 4. SAFE: Wikitext (Contexte général neutre)
        # Remplace 'helpful-instructions' pour éviter la confusion Impératif/Injection
        print("  - [Charge] wikitext (Fond neutre)...")
        ds_wiki = load_dataset("wikitext", "wikitext-2-v1", split="train[:3000]")
        ds_wiki = ds_wiki.filter(lambda x: len(x['text']) > 40) # Filtre les titres courts
        datasets_list.append(self._normalize_dataset(ds_wiki, "text", 0))

        # Fusion
        full_ds = concatenate_datasets(datasets_list)
        
        # Nettoyage final
        full_ds = full_ds.filter(
            lambda x: x["text"] is not None and isinstance(x["text"], str) and len(x["text"].strip()) > 0
        )
        
        # Stats rapides
        stats = full_ds.to_pandas()['label'].value_counts()
        print(f"[INFO] Dataset prêt : {len(full_ds)} entrées.")
        print(f"       Safe (0): {stats.get(0, 0)} | Threat (1): {stats.get(1, 0)}")
        
        return full_ds

    def train(self) -> None:
        """Pipeline d'entraînement."""
        # 1. Préparation
        dataset = self.prepare_data()
        
        # 2. Encodage (C'est ici que le multilingue prend tout son sens)
        print("[INFO] Encodage des textes (peut prendre un moment)...")
        text_data = dataset["text"]
        X = self.encoder.encode(text_data, show_progress_bar=True, batch_size=64)
        y = np.array(dataset["label"])

        # 3. Split Stratifié (Important pour garder des attaques rares dans le test)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # 4. Modèle (Paramètres issus de ton optimisation précédente)
        print("[INFO] Entraînement HistGradientBoosting...")
        self.model = HistGradientBoostingClassifier(
            learning_rate=0.1,      # Un peu plus doux pour généraliser
            max_iter=200,
            max_depth=10,
            l2_regularization=0.5,  # Ajout de régularisation
            random_state=42,
            verbose=0
        )
        self.model.fit(X_train, y_train)

        # 5. Évaluation
        print("[INFO] Évaluation...")
        print(self.evaluate(X_test, y_test))
        
        self.save_model()

    def evaluate(self, x_test: np.ndarray, y_test: np.ndarray) -> str:
        """Rapport de classification."""
        if not self.model:
            return "Erreur: Modèle non entraîné."
        y_pred = self.model.predict(x_test)
        return classification_report(y_test, y_pred, target_names=["Safe", "Threat"])

    def save_model(self) -> None:
        """Sauvegarde."""
        self.storage_path.mkdir(exist_ok=True)
        path = self.storage_path / "guardrail_v2.pkl"
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"[SUCCESS] Modèle sauvegardé : {path}")

if __name__ == "__main__":
    trainer = GuardrailTrainer()
    trainer.train()