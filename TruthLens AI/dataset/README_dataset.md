# Dataset — TruthLens AI

## Files

| File | Rows | Description |
|------|------|-------------|
| `train.csv` | ~2,400 | Training split — columns: `title`, `text`, `label` |
| `test.csv`  | ~600   | Held-out test split — same schema |
| `knowledge_base.csv` | 18 | Verified reference statements (`topic`, `statement`) used by the RAG fact-check agent |

`label`: **0 = REAL**, **1 = FAKE**. Classes are balanced (~50/50).

## How it is built

Public fake-news corpora (e.g. Kaggle's *Fake and Real News* `True.csv` /
`Fake.csv`) are large and licence-gated, so they are **not** bundled. Instead,
`src/data_generator.py` synthesises a balanced, linguistically realistic corpus
so the project trains and demos out-of-the-box, fully offline.

To keep the learned boundary **realistic** (not trivially 100% separable) the
generator deliberately includes:

- **Cross-class overlap** — fake articles sometimes contain measured sentences
  and vice-versa.
- **Shared neutral sentences** used by both classes.
- **~5% ambiguous / mislabelled samples**, emulating the label noise found in
  real-world datasets.

This yields realistic held-out metrics (≈ 94% accuracy, 0.95 ROC-AUC).

## Using the REAL Kaggle dataset instead

1. Download `True.csv` and `Fake.csv` from the Kaggle *Fake and Real News
   Dataset*.
2. Drop both files into this `/dataset` folder.
3. Re-run `python -m src.train`.

`load_real_kaggle_if_present()` detects the files automatically, labels them,
and trains on the real data — no code changes required.

## Schema example

| title | text | label |
|-------|------|-------|
| Reserve Bank releases quarterly update on the economy | According to the Reserve Bank, the economy grew by 4 percent ... | 0 |
| THE SHOCKING TRUTH ABOUT public health they are hiding | SHOCKING: They don't want you to know ... | 1 |
