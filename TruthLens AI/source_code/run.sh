#!/usr/bin/env bash
# ── TruthLens AI launcher (macOS / Linux) ────────────────────────────
set -e
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Training model (first run only)..."
python -m src.train
echo "Launching TruthLens AI..."
streamlit run app.py
