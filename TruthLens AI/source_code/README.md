# 🛡️ TruthLens AI — Agentic AI for Explainable Misinformation Detection

> A production-structured system that detects fake news **and explains why**,
> combining an interpretable ML classifier, retrieval-augmented fact-checking
> (RAG), and a multi-agent Generative-AI explanation layer — running **fully
> offline on a laptop**, with no API key and no cost.

**Author:** Dikshant Aggarwal (Roll No. 12303021) · Punjabi University, Patiala
**Guide:** Dr. Chandan Deep Singh · AI/ML Minor Degree Project

---

## ✨ Why this project stands out

Most student fake-news projects stop at a classifier that outputs a label.
TruthLens goes further with the exact capabilities recruiters look for in 2026:

- **Interpretable ML core** — TF-IDF + Logistic Regression with per-article
  term attribution (you see *which words* drove the verdict).
- **Explainability layer** — a transparent linguistic credibility-signal engine
  (sensationalism, clickbait, vague sourcing, citations, dates, named entities).
- **RAG fact-checking** — semantic retrieval over a verified knowledge base to
  ground each verdict in reference statements.
- **Multi-agent orchestration** — `ClassifierAgent → ExplainerAgent →
  FactCheckAgent`, fused into one calibrated verdict with a visible reasoning trace.
- **Generative AI, gracefully optional** — uses a local LLM (Ollama) to phrase
  explanations when available, and a deterministic template generator when not,
  so the demo **never fails offline**.

---

## 📊 Results (held-out test set, 600 articles)

| Metric | Score |
|--------|:-----:|
| Accuracy | **94.2%** |
| Precision (fake) | 93.4% |
| Recall (fake) | 93.7% |
| F1 (fake) | 93.5% |
| ROC-AUC | **0.947** |
| 5-fold CV accuracy | 94.8% ± 0.8% |

Confusion matrix `[[TN=312, FP=18], [FN=17, TP=253]]`. Charts in `../images/`.

---

## 🚀 Quick start

```bash
cd source_code
pip install -r requirements.txt
streamlit run app.py
```

On first launch the app auto-generates the dataset, trains the model, and opens
at **http://localhost:8501**. (Or run `run.bat` on Windows / `bash run.sh` on
macOS/Linux to do everything in one step.)

---

## 🧱 Project structure

```
source_code/
├── app.py                  # Streamlit UI (entry point)
├── src/
│   ├── config.py           # paths + hyper-parameters
│   ├── preprocessing.py    # dependency-free text cleaning
│   ├── features.py         # explainable credibility signals
│   ├── data_generator.py   # realistic dataset + knowledge base
│   ├── model.py            # TF-IDF + Logistic Regression pipeline
│   ├── train.py            # training + evaluation -> metrics.json
│   ├── retrieval.py        # RAG retriever (dense or TF-IDF fallback)
│   ├── llm.py              # optional local-LLM client + fallback
│   ├── make_charts.py      # result visualisations
│   └── agents/             # ClassifierAgent · ExplainerAgent · FactCheckAgent · Orchestrator
├── tests/                  # pytest suite
├── models/                 # trained artifacts (auto-created)
├── requirements.txt
└── run.bat / run.sh
```

---

## 🧪 Testing

```bash
cd source_code
pytest                       # runs the full suite
```

See `../documentation/TESTING_GUIDE.md` for details.

---

## ⚙️ Tech stack

Python · scikit-learn · pandas · NumPy · Streamlit · Plotly/Matplotlib ·
sentence-transformers + FAISS *(optional)* · Ollama *(optional local LLM)*

---

## ⚠️ Responsible-use note

TruthLens is a **decision-support tool**, not an arbiter of absolute truth. It
estimates the *likelihood* of misinformation from linguistic and statistical
patterns and should complement, not replace, human judgement and primary-source
verification.

---

## 📄 License

Released for academic use as part of a Minor Degree Project submission.
