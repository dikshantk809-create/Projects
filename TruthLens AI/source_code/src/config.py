"""
Central configuration for TruthLens AI.

All paths are resolved relative to the project root so the app works no matter
which directory it is launched from. Tunable constants live here so behaviour
can be changed without touching business logic.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
SRC_DIR: Path = Path(__file__).resolve().parent
SOURCE_CODE_DIR: Path = SRC_DIR.parent
PROJECT_ROOT: Path = SOURCE_CODE_DIR.parent          # the "minor degree project" folder

MODELS_DIR: Path = SOURCE_CODE_DIR / "models"
DATASET_DIR: Path = PROJECT_ROOT / "dataset"
IMAGES_DIR: Path = PROJECT_ROOT / "images"
ASSETS_DIR: Path = SOURCE_CODE_DIR / "assets"

MODEL_PATH: Path = MODELS_DIR / "truthlens_model.joblib"
METRICS_PATH: Path = MODELS_DIR / "metrics.json"

TRAIN_CSV: Path = DATASET_DIR / "train.csv"
TEST_CSV: Path = DATASET_DIR / "test.csv"
KNOWLEDGE_BASE_CSV: Path = DATASET_DIR / "knowledge_base.csv"

for _d in (MODELS_DIR, DATASET_DIR, IMAGES_DIR, ASSETS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Labels
# --------------------------------------------------------------------------- #
LABELS = {0: "REAL", 1: "FAKE"}
LABEL_REAL = 0
LABEL_FAKE = 1

# --------------------------------------------------------------------------- #
# Model hyper-parameters
# --------------------------------------------------------------------------- #
TFIDF_MAX_FEATURES = 1_500
TFIDF_NGRAM_RANGE = (1, 2)
TFIDF_MIN_DF = 3
TEST_SIZE = 0.2
RANDOM_STATE = 42
CV_FOLDS = 5

# --------------------------------------------------------------------------- #
# Retrieval (RAG) settings
# --------------------------------------------------------------------------- #
RETRIEVAL_TOP_K = 3
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# --------------------------------------------------------------------------- #
# LLM settings (all optional - system degrades gracefully when absent)
# --------------------------------------------------------------------------- #
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("TRUTHLENS_LLM_MODEL", "llama3.2")
LLM_TIMEOUT_SECONDS = 20

CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.60

APP_TITLE = "TruthLens AI"
APP_TAGLINE = "Agentic AI for Explainable Misinformation Detection"
