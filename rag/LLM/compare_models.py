"""Comparaison rapide avec RandomizedSearchCV (5-10 minutes au lieu de 30+).

Utilise RandomizedSearchCV qui teste un échantillon aléatoire au lieu
de toutes les combinaisons possibles.
"""

import pickle
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from datasets import load_dataset, concatenate_datasets, Dataset
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    make_scorer,
)


def normalize_dataset(dataset, label_map: Dict[int, int], query_col: str):
    """Normalise un dataset."""
    def normalize(example):
        return {
            "query": example[query_col],
            "label": label_map.get(example.get("label", 0), 0),
        }
    return dataset.map(normalize, remove_columns=dataset.column_names)


def prepare_datasets_fast():
    """Prépare les datasets."""
    print("📥 Chargement des datasets...")

    # Injections
    ds1 = load_dataset("deepset/prompt-injections", split="train")
    ds1_test = load_dataset("deepset/prompt-injections", split="test")
    ds1_all = concatenate_datasets([ds1, ds1_test])
    ds1_norm = normalize_dataset(ds1_all, {0: 0, 1: 1}, "text")

    ds2 = load_dataset("jackhhao/jailbreak-classification", split="train")
    ds2_test = load_dataset("jackhhao/jailbreak-classification", split="test")
    ds2_all = concatenate_datasets([ds2, ds2_test])
    ds2_norm = normalize_dataset(ds2_all, {0: 0, 1: 1}, "prompt")

    injections = concatenate_datasets([ds1_norm, ds2_norm])

    # Safe queries
    safe_queries = [
        "Patient douleur thoracique dyspnée",
        "Fièvre élevée enfant 5 ans",
        "Fracture ouverte bras droit",
        "Suspicion AVC paralysie faciale",
        "Crise asthme sévère SpO2 88%",
        "Douleur abdominale aiguë",
        "Trauma crânien perte conscience",
        "Hémorragie digestive vomissements",
        "Convulsions généralisées",
        "Détresse respiratoire nourrisson",
        "Vertiges nausées persistants",
        "Confusion mentale personne âgée",
        "Brûlure deuxième degré",
        "Réaction allergique urticaire",
        "Douleur lombaire irradiant",
        "Céphalée intense photophobie",
        "Palpitations essoufflement",
        "Plaie profonde sutures",
        "Intoxication déshydratation",
        "Douleur thoracique effort",
        "Symptômes infarctus?",
        "Comment reconnaître AVC?",
        "Que faire brûlure grave?",
        "Quand appeler urgences?",
        "Comment administrer garrot?",
        "Signes déshydratation enfant",
        "Différence ROUGE JAUNE",
        "Protocole accueil urgences",
        "Temps attente VERT",
        "Unités soins disponibles",
    ]

    safe_expanded = safe_queries * 100
    ds_safe = Dataset.from_dict({"query": safe_expanded, "label": [0] * len(safe_expanded)})

    full_dataset = concatenate_datasets([injections, ds_safe])
    full_dataset = full_dataset.shuffle(seed=42)

    print(f"✅ Total: {len(full_dataset)} exemples")
    print(f"   Threats: {sum(full_dataset['label'])}")
    print(f"   Safe: {len(full_dataset) - sum(full_dataset['label'])}")

    return full_dataset


def randomized_search_hist_gradient(X_train, y_train) -> Tuple:
    """RandomizedSearch rapide pour HistGradientBoosting."""
    print("\n🔍 RandomizedSearch HistGradientBoosting (20 combinaisons)...")
    
    param_dist = {
        'learning_rate': [0.05, 0.1, 0.15, 0.2],
        'max_iter': [100, 150, 200, 250],
        'max_depth': [5, 7, 10, 12],
        'min_samples_leaf': [5, 10, 15, 20],
        'l2_regularization': [0.0, 0.3, 0.5, 0.7, 1.0],
    }
    
    clf = HistGradientBoostingClassifier(random_state=42, verbose=0)
    
    search = RandomizedSearchCV(
        clf,
        param_dist,
        n_iter=20,  # Test seulement 20 combinaisons au lieu de 405
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        verbose=1,
        random_state=42,
    )
    
    start = time.time()
    search.fit(X_train, y_train)
    search_time = time.time() - start
    
    print(f"\n✅ Meilleurs params:")
    for key, value in search.best_params_.items():
        print(f"   {key}: {value}")
    print(f"   CV F1: {search.best_score_:.4f}")
    print(f"   Time: {search_time:.1f}s")
    
    return search.best_estimator_, search_time


def randomized_search_random_forest(X_train, y_train) -> Tuple:
    """RandomizedSearch rapide pour RandomForest."""
    print("\n🔍 RandomizedSearch RandomForest (20 combinaisons)...")
    
    param_dist = {
        'n_estimators': [100, 150, 200, 250, 300],
        'max_depth': [10, 15, 20, 25, None],
        'min_samples_split': [2, 5, 10, 15],
        'min_samples_leaf': [1, 2, 4, 6],
        'max_features': ['sqrt', 'log2', 0.5],
    }
    
    clf = RandomForestClassifier(random_state=42, n_jobs=-1, verbose=0)
    
    search = RandomizedSearchCV(
        clf,
        param_dist,
        n_iter=20,  # Test seulement 20 combinaisons
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        verbose=1,
        random_state=42,
    )
    
    start = time.time()
    search.fit(X_train, y_train)
    search_time = time.time() - start
    
    print(f"\n✅ Meilleurs params:")
    for key, value in search.best_params_.items():
        print(f"   {key}: {value}")
    print(f"   CV F1: {search.best_score_:.4f}")
    print(f"   Time: {search_time:.1f}s")
    
    return search.best_estimator_, search_time


def evaluate_classifier(clf, X_test, y_test, name: str, search_time: float = 0) -> Dict:
    """Évalue un classifieur."""
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"{'='*60}")
    
    start = time.time()
    y_pred = clf.predict(X_test)
    predict_time = time.time() - start
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    
    print(f"\n📈 Métriques:")
    print(f"   Accuracy:  {accuracy:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    
    print(f"\n⏱️  Temps:")
    print(f"   Search: {search_time:.1f}s")
    print(f"   Predict: {predict_time:.4f}s")
    print(f"   Speed: {len(y_test)/predict_time:.0f} q/s")
    
    print(f"\n🎭 Confusion:")
    print(f"   TN={tn}  FP={fp}")
    print(f"   FN={fn}  TP={tp}")
    
    print(f"\n⚠️  Erreurs:")
    print(f"   FPR: {fpr:.2%}")
    print(f"   FNR: {fnr:.2%}")
    
    return {
        "name": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "search_time": search_time,
        "predict_time": predict_time,
        "qps": len(y_test) / predict_time,
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "fpr": fpr, "fnr": fnr,
    }


def quick_compare():
    """Comparaison rapide avec RandomizedSearch."""
    total_start = time.time()
    
    # Données
    dataset = prepare_datasets_fast()
    split = dataset.train_test_split(test_size=0.2, seed=42)
    train_ds, test_ds = split["train"], split["test"]
    
    # Embeddings
    print("\n🔤 Génération embeddings...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    X_train_emb = model.encode(train_ds["query"], show_progress_bar=True, batch_size=32)
    X_test_emb = model.encode(test_ds["query"], show_progress_bar=True, batch_size=32)
    
    y_train = np.array(train_ds["label"])
    y_test = np.array(test_ds["label"])
    
    # RandomizedSearch
    print("\n" + "="*60)
    print("🔬 OPTIMISATION RAPIDE (20 iter chacun)")
    print("="*60)
    
    clf_hist, hist_time = randomized_search_hist_gradient(X_train_emb, y_train)
    clf_rf, rf_time = randomized_search_random_forest(X_train_emb, y_train)
    
    # Évaluation
    print("\n" + "="*60)
    print("🎯 ÉVALUATION")
    print("="*60)
    
    r1 = evaluate_classifier(clf_hist, X_test_emb, y_test, "HistGradientBoosting", hist_time)
    r2 = evaluate_classifier(clf_rf, X_test_emb, y_test, "RandomForest", rf_time)
    
    # Comparaison
    print(f"\n{'='*60}")
    print("📊 COMPARAISON")
    print(f"{'='*60}\n")
    
    print(f"{'Metric':<12} {'HistGB':<15} {'RandomForest':<15} {'Winner'}")
    print("-" * 55)
    
    metrics = [
        ("F1", "f1", "{:.4f}"),
        ("Accuracy", "accuracy", "{:.4f}"),
        ("FPR", "fpr", "{:.2%}"),
        ("FNR", "fnr", "{:.2%}"),
        ("Search", "search_time", "{:.0f}s"),
        ("Speed", "qps", "{:.0f} q/s"),
    ]
    
    for name, key, fmt in metrics:
        v1, v2 = r1[key], r2[key]
        
        if key in ["fpr", "fnr", "search_time"]:
            winner = "HistGB 🏆" if v1 < v2 else "RF 🏆"
        else:
            winner = "HistGB 🏆" if v1 > v2 else "RF 🏆"
        
        print(f"{name:<12} {fmt.format(v1):<15} {fmt.format(v2):<15} {winner}")
    
    # Score composite
    score1 = r1["f1"] - (r1["fpr"] + r1["fnr"]) / 2
    score2 = r2["f1"] - (r2["fpr"] + r2["fnr"]) / 2
    
    print(f"\n{'='*60}")
    print("💡 CONCLUSION")
    print(f"{'='*60}")
    print(f"\nScore composite:")
    print(f"   HistGB: {score1:.4f}")
    print(f"   RandomForest: {score2:.4f}")
    
    if score1 > score2:
        print(f"\n✅ HistGradientBoosting recommandé (+{score1-score2:.4f})")
        winner = clf_hist
        winner_name = "histgradient"
    else:
        print(f"\n✅ RandomForest recommandé (+{score2-score1:.4f})")
        winner = clf_rf
        winner_name = "randomforest"
    
    # Temps total
    total_time = time.time() - total_start
    print(f"\n⏱️  Temps total: {total_time/60:.1f} minutes")
    
    # Sauvegarde
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "guardrail_histgradient.pkl", "wb") as f:
        pickle.dump(clf_hist, f)
    
    with open(output_dir / "guardrail_randomforest.pkl", "wb") as f:
        pickle.dump(clf_rf, f)
    
    with open(output_dir / "guardrail.pkl", "wb") as f:
        pickle.dump(winner, f)
    
    print(f"\n✅ Modèles sauvegardés:")
    print(f"   • data/guardrail.pkl ({winner_name})")
    print(f"   • data/guardrail_histgradient.pkl")
    print(f"   • data/guardrail_randomforest.pkl")


if __name__ == "__main__":
    quick_compare()