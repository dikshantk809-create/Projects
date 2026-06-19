"""
Generate publication-quality charts from the trained model's metrics.

Run (after training):  python -m src.make_charts
Outputs PNGs into the project-level /images folder for the report and slides.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")  # headless / no display needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config

PRIMARY = "#2c5364"
ACCENT = "#c31432"
GREEN = "#11998e"
plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "figure.dpi": 140})


def _load_metrics() -> dict:
    if not config.METRICS_PATH.exists():
        raise FileNotFoundError("metrics.json not found — run `python -m src.train` first.")
    return json.loads(config.METRICS_PATH.read_text(encoding="utf-8"))


def chart_confusion_matrix(m: dict) -> None:
    cm = np.array(m["confusion_matrix"])
    labels = m.get("labels", ["REAL", "FAKE"])
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix — Held-out Test Set")
    thresh = cm.max() / 2
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black", fontsize=14, fontweight="bold")
    fig.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(config.IMAGES_DIR / "confusion_matrix.png", bbox_inches="tight")
    plt.close(fig)


def chart_roc(m: dict) -> None:
    fpr = m["roc_curve"]["fpr"]; tpr = m["roc_curve"]["tpr"]
    fig, ax = plt.subplots(figsize=(5, 4.2))
    ax.plot(fpr, tpr, color=ACCENT, lw=2.5, label=f"ROC (AUC = {m['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve"); ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(config.IMAGES_DIR / "roc_curve.png", bbox_inches="tight")
    plt.close(fig)


def chart_metrics_bar(m: dict) -> None:
    names = ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]
    vals = [m["accuracy"], m["precision_fake"], m["recall_fake"], m["f1_fake"], m["roc_auc"]]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    bars = ax.bar(names, vals, color=[PRIMARY, "#3a6b86", "#4d82a0", "#11998e", "#c31432"])
    ax.set_ylim(0, 1.05); ax.set_title("TruthLens — Performance Metrics")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontweight="bold")
    fig.tight_layout()
    fig.savefig(config.IMAGES_DIR / "metrics_bar.png", bbox_inches="tight")
    plt.close(fig)


def chart_dataset_distribution() -> None:
    if not config.TRAIN_CSV.exists():
        return
    train = pd.read_csv(config.TRAIN_CSV)
    test = pd.read_csv(config.TEST_CSV)
    cats = ["REAL", "FAKE"]
    tr = [int((train["label"] == 0).sum()), int((train["label"] == 1).sum())]
    te = [int((test["label"] == 0).sum()), int((test["label"] == 1).sum())]
    x = np.arange(len(cats)); w = 0.35
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x - w / 2, tr, w, label="Train", color=PRIMARY)
    ax.bar(x + w / 2, te, w, label="Test", color=GREEN)
    ax.set_xticks(x, cats); ax.set_title("Dataset Class Distribution"); ax.legend()
    for i, (a, b) in enumerate(zip(tr, te)):
        ax.text(i - w / 2, a + 5, str(a), ha="center"); ax.text(i + w / 2, b + 5, str(b), ha="center")
    fig.tight_layout()
    fig.savefig(config.IMAGES_DIR / "dataset_distribution.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    m = _load_metrics()
    chart_confusion_matrix(m)
    chart_roc(m)
    chart_metrics_bar(m)
    chart_dataset_distribution()
    print(f"Charts written to {config.IMAGES_DIR}")


if __name__ == "__main__":
    main()
