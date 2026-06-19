# TruthLens AI — Testing Guide

## Running the test suite

```bash
cd source_code
pip install -r requirements.txt   # includes pytest
pytest                            # quiet mode, runs everything
pytest -v                         # verbose: one line per test
```

## What is covered

| Test file | Focus | Example checks |
|-----------|-------|----------------|
| `tests/test_preprocessing.py` | Text cleaning | URLs/HTML/punctuation stripped, stop-words removed, empty/None handled, tokenizer & sentence splitter |
| `tests/test_features.py` | Explainable signals | sensational/clickbait detection, credible text scores low risk, risk score bounded to [0,1], empty-input safety |
| `tests/test_pipeline.py` | End-to-end agents | a fake article is flagged FAKE, a real one REAL, the 3-agent trace is present, empty text raises a clear error |

`test_pipeline.py` trains a small model in-memory from the synthetic generator,
so the suite is fast, deterministic, and independent of any saved model artifact.

## Manual verification

1. **Training reproduces metrics**
   ```bash
   python -m src.train
   ```
   Expect roughly: accuracy ≈ 0.94, ROC-AUC ≈ 0.95, 5-fold CV ≈ 0.95.
   (Exact values vary slightly by library version.)

2. **App smoke test** — launch the app, load the fake sample → red **FAKE**
   verdict; load the real sample → green **REAL** verdict.

3. **Offline guarantee** — disconnect from the internet and repeat step 2. The
   app must still work (template explanation + TF-IDF retrieval).

## Continuous-integration tip

```bash
pytest --maxfail=1 --disable-warnings -q
```
Use this as a pre-commit / CI gate; a non-zero exit code means a regression.
