"""
Training & evaluation entry-point for TruthLens AI.

Run:  python -m src.train

Generates the dataset if absent, trains the pipeline, evaluates it with both
k-fold cross-validation and a held-out test set, then persists the model and a
metrics.json artifact consumed by the report, the charts script, and the app.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import cross_val_score

from . import config
from .data_generator import generate_and_save
from .model import build_pipeline, combine_fields, save_model


def _load_split() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if not (config.TRAIN_CSV.exists() and config.TEST_CSV.exists()):
        info = generate_and_save()
        source = info["source"]
    else:
        source = "existing dataset CSVs"
    train = pd.read_csv(config.TRAIN_CSV).fillna("")
    test = pd.read_csv(config.TEST_CSV).fillna("")
    return train, test, source


def train_and_evaluate() -> dict:
    print("=" * 64)
    print("  TruthLens AI — training the misinformation classifier")
    print("=" * 64)

    train, test, source = _load_split()
    X_train = [combine_fields(t, x) for t, x in zip(train["title"], train["text"])]
    y_train = train["label"].astype(int).values
    X_test = [combine_fields(t, x) for t, x in zip(test["title"], test["text"])]
    y_test = test["label"].astype(int).values

    print(f"  Dataset source : {source}")
    print(f"  Train examples : {len(X_train):,}")
    print(f"  Test examples  : {len(X_test):,}")

    pipeline = build_pipeline()

    # ---- Cross-validation on the training set ---------------------------- #
    print("\n  Running 5-fold cross-validation ...")
    cv_scores = cross_val_score(
        pipeline, X_train, y_train, cv=config.CV_FOLDS, scoring="accuracy"
    )
    print(f"  CV accuracy    : {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # ---- Fit on full training set, evaluate on held-out test ------------- #
    t0 = time.time()
    pipeline.fit(X_train, y_train)
    train_secs = round(time.time() - t0, 2)

    proba = pipeline.predict_proba(X_test)
    fake_idx = list(pipeline.named_steps["clf"].classes_).index(config.LABEL_FAKE)
    y_score = proba[:, fake_idx]
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, pos_label=config.LABEL_FAKE)
    rec = recall_score(y_test, y_pred, pos_label=config.LABEL_FAKE)
    f1 = f1_score(y_test, y_pred, pos_label=config.LABEL_FAKE)
    auc = roc_auc_score(y_test, y_score)
    cm = confusion_matrix(y_test, y_pred).tolist()
    fpr, tpr, _ = roc_curve(y_test, y_score, pos_label=config.LABEL_FAKE)
    report = classification_report(
        y_test, y_pred, target_names=["REAL", "FAKE"], digits=4
    )

    print("\n  Held-out test performance")
    print("  " + "-" * 40)
    print(f"  Accuracy       : {acc:.4f}")
    print(f"  Precision(FAKE): {prec:.4f}")
    print(f"  Recall(FAKE)   : {rec:.4f}")
    print(f"  F1(FAKE)       : {f1:.4f}")
    print(f"  ROC-AUC        : {auc:.4f}")
    print(f"  Train time     : {train_secs}s")
    print("\n" + report)

    metrics = {
        "model": "TF-IDF (1,2-gram) + Logistic Regression",
        "dataset_source": source,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "cv_folds": config.CV_FOLDS,
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "accuracy": round(float(acc), 4),
        "precision_fake": round(float(prec), 4),
        "recall_fake": round(float(rec), 4),
        "f1_fake": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "train_seconds": train_secs,
        "confusion_matrix": cm,           # [[TN, FP],[FN, TP]] with labels [REAL, FAKE]
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "classification_report": report,
        "labels": ["REAL", "FAKE"],
    }

    save_model(pipeline)
    config.METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\n  Model saved    : {config.MODEL_PATH}")
    print(f"  Metrics saved  : {config.METRICS_PATH}")
    print("=" * 64)
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
