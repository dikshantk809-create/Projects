# TruthLens AI — Setup Guide (Quick Start)

Get TruthLens running in **three commands**.

```bash
cd "Desktop/minor degree project/source_code"
pip install -r requirements.txt
streamlit run app.py
```

That's it. On first launch the app automatically:
1. generates the bundled dataset (`/dataset/train.csv`, `test.csv`, `knowledge_base.csv`),
2. trains the TF-IDF + Logistic-Regression classifier,
3. saves the model to `/source_code/models/truthlens_model.joblib`,
4. opens the UI in your browser at **http://localhost:8501**.

---

## One-click launchers

| OS | Command |
|----|---------|
| Windows | double-click `run.bat` (or `run.bat` in a terminal) |
| macOS / Linux | `bash run.sh` |

These install dependencies, train the model, and launch the app in one step.

---

## Project layout

```
minor degree project/
├── source_code/          ← the working application
│   ├── app.py            ← Streamlit UI (run this)
│   ├── src/              ← package: model, agents, retrieval, features
│   │   └── agents/       ← ClassifierAgent · ExplainerAgent · FactCheckAgent · Orchestrator
│   ├── tests/            ← pytest suite
│   ├── models/           ← saved model + metrics (created by training)
│   ├── requirements.txt
│   └── run.bat / run.sh
├── dataset/              ← train/test CSVs + knowledge base
├── documentation/        ← these guides
├── report/               ← academic project report + selection analysis
├── ppt/                  ← presentation
├── images/               ← architecture diagram + result charts
└── interview_prep/       ← viva & interview Q&A
```

---

## Configuration (optional)

All tunables live in `src/config.py`. Environment variables you can set:

| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_HOST` | Local LLM server URL | `http://localhost:11434` |
| `TRUTHLENS_LLM_MODEL` | Local model name | `llama3.2` |

Nothing needs to be configured for a standard run.

---

## Next steps
- **Usage Guide** — how to use every feature of the app.
- **Testing Guide** — how to run and extend the test suite.
- **Installation Guide** — detailed, platform-specific setup and troubleshooting.
