"""
The interpretable ML core of TruthLens.

A scikit-learn Pipeline (TF-IDF -> calibrated Logistic Regression) provides a
fast, fully-offline, *interpretable* classifier with calibrated probabilities.
Interpretability matters: the Explainer agent surfaces the top weighted
n-grams behind every prediction.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from . import config
from .preprocessing import clean_text


# --------------------------------------------------------------------------- #
# Model construction
# --------------------------------------------------------------------------- #
def build_pipeline() -> Pipeline:
    """Create the TF-IDF + Logistic Regression pipeline."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=clean_text,
                    max_features=config.TFIDF_MAX_FEATURES,
                    ngram_range=config.TFIDF_NGRAM_RANGE,
                    min_df=config.TFIDF_MIN_DF,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=config.RANDOM_STATE,
                    n_jobs=None,
                ),
            ),
        ]
    )


def combine_fields(title: str, text: str) -> str:
    """Join the headline and body — the headline carries strong signal."""
    title = (title or "").strip()
    text = (text or "").strip()
    return f"{title}. {text}".strip(". ").strip()


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def save_model(pipeline: Pipeline, path: Path = config.MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)


def load_model(path: Path = config.MODEL_PATH) -> Pipeline:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Model not found at {path}. Run `python -m src.train` first."
        )
    return joblib.load(path)


def model_exists(path: Path = config.MODEL_PATH) -> bool:
    return Path(path).exists()


def load_metrics(path: Path = config.METRICS_PATH) -> dict[str, Any]:
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


# --------------------------------------------------------------------------- #
# Inference helpers
# --------------------------------------------------------------------------- #
def predict_proba_fake(pipeline: Pipeline, title: str, text: str) -> float:
    """Return P(label == FAKE) for a single article."""
    doc = combine_fields(title, text)
    proba = pipeline.predict_proba([doc])[0]
    classes = list(pipeline.named_steps["clf"].classes_)
    fake_idx = classes.index(config.LABEL_FAKE)
    return float(proba[fake_idx])


def top_indicative_terms(
    pipeline: Pipeline, title: str, text: str, top_n: int = 8
) -> dict[str, list[tuple[str, float]]]:
    """
    Explainability: return the n-grams in THIS document that pushed the
    prediction toward FAKE and toward REAL, using model coefficients * tf-idf.
    """
    doc = combine_fields(title, text)
    vec: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clf: LogisticRegression = pipeline.named_steps["clf"]

    x = vec.transform([doc])
    feature_names = np.array(vec.get_feature_names_out())
    coefs = clf.coef_[0]  # binary LR: positive coef -> class 1 (FAKE)

    x_coo = x.tocoo()
    contributions = [(feature_names[j], coefs[j] * x_coo.data[k])
                     for k, j in enumerate(x_coo.col)]
    contributions.sort(key=lambda t: t[1])

    toward_real = [(t, round(float(w), 4)) for t, w in contributions[:top_n] if w < 0]
    toward_fake = [(t, round(float(w), 4)) for t, w in contributions[::-1][:top_n] if w > 0]
    return {"toward_fake": toward_fake, "toward_real": toward_real}
