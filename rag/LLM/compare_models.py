"""
Comparaison rapide RandomizedSearchCV avec support Multilingue (MultiJail).
Version Production (Sans Emojis, Logging Standard).
"""

import pickle
import time
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from datasets import load_dataset, concatenate_datasets, Dataset
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import (
    f1_score,
    confusion_matrix, 
    make_scorer
)

# ==========================================
# 1. CONFIGURATION & DATA ENGINEERING
# ==========================================

def normalize_dataset(dataset, text_col: str, label_col: str, target_label_map: Dict[int, int]):
    """Standardise les colonnes pour la fusion."""
    def normalize(example):
        return {
            "text": example[text_col],
            "label": int(target_label_map.get(example[label_col], 0)), 
        }
    return dataset.map(normalize, remove_columns=dataset.column_names)

def prepare_datasets_robust():
    """
    Charge et fusionne les datasets d'entraînement.
    """
    print("\n[INFO] Chargement des datasets...")

    # --- A. DATASETS MALVEILLANTS (Label = 1) ---
    
    # 1. Deepset Prompt Injections
    print("  - Loading deepset/prompt-injections...")
    ds_deepset = load_dataset("deepset/prompt-injections", split="train")
    ds_deepset = normalize_dataset(ds_deepset, "text", "label", {0: 0, 1: 1})
    
    # 2. MultiJail (Multilingual)
    print("  - Loading DAMO-NLP-SG/MultiJail (Multilingual)...")
    try:
        ds_multijail = load_dataset("DAMO-NLP-SG/MultiJail", split="train")
        ds_multijail = ds_multijail.map(
            lambda x: {"text": x["prompt"], "label": 1}, 
            remove_columns=ds_multijail.column_names
        )
    except Exception as e:
        print(f"  [WARN] MultiJail non trouvé ({e}), fallback sur dataset vide.")
        ds_multijail = Dataset.from_dict({"text": [], "label": []})

    # --- B. DATASETS SAFE (Label = 0) ---
    
    # 3. Requêtes Médicales (Domain Specific)
    print("  - Generating Medical Safe Queries...")
    safe_queries_base = [
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
        "Chest pain and difficulty breathing", "High fever child 5 years", # EN
        "Dolor torácico y dificultad para respirar", # ES
        "Brustschmerzen und Atembeschwerden", # DE
    ]
    safe_expanded = safe_queries_base * 200 
    ds_safe_med = Dataset.from_dict({"text": safe_expanded, "label": [0] * len(safe_expanded)})

    # 4. Wikitext (General Safe Background)
    print("  - Loading wikitext (General Background)...")
    ds_wiki = load_dataset("wikitext", "wikitext-2-v1", split="train[:2000]")
    ds_wiki = ds_wiki.filter(lambda x: len(x["text"]) > 20)
    ds_wiki = normalize_dataset(ds_wiki, "text", "text", {}) 
    ds_wiki = ds_wiki.map(lambda x: {"text": x["text"], "label": 0})

    # --- C. FUSION ---
    full_dataset = concatenate_datasets([ds_deepset, ds_multijail, ds_safe_med, ds_wiki])
    full_dataset = full_dataset.shuffle(seed=42)

    # Stats
    df = full_dataset.to_pandas()
    print(f"\n[INFO] Dataset final: {len(df)} exemples")
    print(df["label"].value_counts().rename({0: "Safe (0)", 1: "Injection (1)"}))

    return df

# ==========================================
# 2. MODELING (Optimisé)
# ==========================================

def randomized_search_wrapper(clf, param_dist, X, y, name="Model"):
    """Wrapper générique pour RandomizedSearchCV."""
    print(f"\n[INFO] Tuning {name} (20 iter)...")
    
    search = RandomizedSearchCV(
        clf,
        param_dist,
        n_iter=20,
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        verbose=1,
        random_state=42
    )
    
    start = time.time()
    search.fit(X, y)
    duration = time.time() - start
    
    print(f"  [RESULT] Best F1: {search.best_score_:.4f} | Time: {duration:.1f}s")
    return search.best_estimator_, duration

def evaluate_and_report(clf, X_test, y_test, name, training_time):
    """Calcule les métriques de performance."""
    start = time.time()
    y_pred = clf.predict(X_test)
    inference_time = time.time() - start
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    f1 = f1_score(y_test, y_pred)
    
    return {
        "Model": name,
        "F1": f1,
        "FPR": fpr,
        "FNR": fnr,
        "TP": tp, "FP": fp,
        "Inference_Speed": len(y_test) / inference_time,
        "Training_Time": training_time
    }

def main():
    total_start = time.time()
    
    # 1. Data
    df = prepare_datasets_robust()
    X_text = df["text"].tolist()
    y = df["label"].values
    
    # 2. Embeddings
    print("\n[INFO] Encoding (paraphrase-multilingual-MiniLM-L12-v2)...")
    embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    X = embedder.encode(X_text, show_progress_bar=True, batch_size=64)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 3. Comparaison Modèles
    results = []
    
    # A. HistGradientBoosting
    hgb_params = {
        'learning_rate': [0.05, 0.1, 0.2],
        'max_iter': [100, 200],
        'max_depth': [None, 10, 20],
        'l2_regularization': [0.0, 0.1, 0.5]
    }
    best_hgb, time_hgb = randomized_search_wrapper(
        HistGradientBoostingClassifier(random_state=42), 
        hgb_params, X_train, y_train, "HistGB"
    )
    results.append(evaluate_and_report(best_hgb, X_test, y_test, "HistGradientBoosting", time_hgb))
    
    # B. RandomForest
    rf_params = {
        'n_estimators': [100, 200],
        'max_depth': [None, 20, 30],
        'min_samples_split': [2, 5]
    }
    best_rf, time_rf = randomized_search_wrapper(
        RandomForestClassifier(random_state=42, n_jobs=-1), 
        rf_params, X_train, y_train, "RandomForest"
    )
    results.append(evaluate_and_report(best_rf, X_test, y_test, "RandomForest", time_rf))

    # 4. Rapport Final
    print(f"\n{'='*60}")
    print("[REPORT] RAPPORT DE SÉCURITÉ (Guardrail)")
    print(f"{'='*60}")
    
    res_df = pd.DataFrame(results).set_index("Model")
    print(res_df[["F1", "FPR", "FNR", "Inference_Speed"]].style.format({
        "F1": "{:.2%}", "FPR": "{:.2%}", "FNR": "{:.2%}", "Inference_Speed": "{:.0f} q/s"
    }).to_string())
    
    # Sélection du vainqueur
    res_df["Score"] = res_df["F1"] - (res_df["FPR"] * 2) 
    winner_name = res_df["Score"].idxmax()
    winner_model = best_hgb if winner_name == "HistGradientBoosting" else best_rf
    
    print(f"\n[RESULT] Modèle recommandé : {winner_name}")
    print(f"         (Choisi pour son équilibre Sécurité/Disponibilité)")

    # 5. Sauvegarde
    Path("data").mkdir(exist_ok=True)
    with open("data/guardrail_best.pkl", "wb") as f:
        pickle.dump(winner_model, f)
    print("[INFO] Modèle sauvegardé dans data/guardrail_best.pkl")
    
    print(f"[INFO] Temps total: {(time.time() - total_start)/60:.1f} min")

if __name__ == "__main__":
    main()