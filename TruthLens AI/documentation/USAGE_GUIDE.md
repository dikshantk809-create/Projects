# TruthLens AI — Usage Guide

## Launching the app

```bash
cd source_code
streamlit run app.py
```
Your browser opens at **http://localhost:8501**.

## Analysing an article

1. (Optional) Type or paste a **headline** in the *Headline* box.
2. Paste the **article text** in the *Article text* box.
3. Click **🔍 Analyze article**.

Don't have an article handy? Click **⚠️ Load fake example** or **✅ Load real
example** on the right to populate the form instantly — ideal for a live demo.

## Reading the results

| Panel | What it tells you |
|-------|-------------------|
| **Verdict card** | FAKE or REAL, the confidence %, a confidence band (High/Medium/Low) and a recommendation. |
| **Score metrics** | Fused fake-score, the model's raw P(fake), the linguistic signal-risk, and latency. |
| **Agentic reasoning pipeline** | The exact sequence of agents that ran, each with its summary and timing — your "explainability trace". |
| **🧠 Explanation tab** | A plain-language justification (LLM-written if a local model is available, else a deterministic template). |
| **🔎 Signals & terms tab** | Detected misinformation markers, credibility markers, and the most influential model terms for *this* article. |
| **📚 Retrieved evidence tab** | Verified reference statements pulled by the RAG fact-check agent. |

## Demo script (2 minutes, for viva)

1. Load the **fake** example → show the red FAKE verdict, point to the
   sensational/clickbait signals and the FAKE-leaning terms.
2. Load the **real** example → show the green REAL verdict, point to the
   credibility markers (named sources, dates) and retrieved evidence.
3. Paste a **mixed** article of your own → show the calibrated confidence band
   and the agent trace explaining the decision.

## Command-line usage

```bash
python -m src.train          # (re)train the model and write metrics.json
python -m src.make_charts    # regenerate result charts into ../images
pytest                       # run the test suite
```

## Optional upgrades

- **Better explanations (local LLM):** install [Ollama](https://ollama.com) and
  run `ollama pull llama3.2`. TruthLens detects it automatically — no API key.
- **Stronger retrieval:** `pip install -r requirements-optional.txt` to enable
  dense sentence-transformer embeddings + FAISS for the fact-check agent.

If neither is installed, the app still runs fully — it falls back to the
template generator and a TF-IDF retriever.
