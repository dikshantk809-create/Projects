# TruthLens AI — Installation Guide

This guide covers a clean installation on **Windows, macOS, and Linux**. The
project is intentionally lightweight: the full app runs with no GPU, no API key,
and no internet connection after the dependencies are installed.

---

## 1. Prerequisites

| Requirement | Version | Check command |
|-------------|---------|---------------|
| Python      | 3.9 – 3.12 | `python --version` |
| pip         | latest  | `python -m pip --version` |
| Git (optional) | any  | `git --version` |

> **Tip:** If `python` opens the Microsoft Store on Windows, use `py` instead
> (e.g. `py --version`, `py -m venv .venv`).

---

## 2. Get the project

The project already lives in your folder:

```
Desktop/minor degree project/source_code
```

Open a terminal **inside the `source_code` folder**:

- **Windows:** open the `source_code` folder → click the address bar → type `cmd` → Enter
- **macOS/Linux:** `cd "~/Desktop/minor degree project/source_code"`

---

## 3. Create a virtual environment (recommended)

Keeps dependencies isolated from your system Python.

**Windows (PowerShell or CMD):**
```bat
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should now see `(.venv)` at the start of your prompt.

---

## 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Streamlit, scikit-learn, pandas, numpy, matplotlib, plotly,
requests and pytest. Installation typically takes 1–3 minutes.

### Optional power-ups (not required)
```bash
# Stronger semantic retrieval for the RAG fact-check agent
pip install -r requirements-optional.txt

# Fluent LLM-written explanations via a free LOCAL model
#   1. install Ollama:  https://ollama.com
#   2. pull a small model:
ollama pull llama3.2
```
If you skip these, TruthLens automatically uses a TF-IDF retriever and a
deterministic template generator — everything still works offline.

---

## 5. Verify the installation

```bash
python -m src.train     # builds the dataset + trains the model (a few seconds)
pytest                  # should report all tests passing
```

If both succeed, you are ready to launch (see the **Usage Guide**).

---

## 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: streamlit` | The virtual environment isn't active, or deps not installed. Re-run step 3–4. |
| `python` not found (Windows) | Use `py` instead of `python`. |
| `pip` SSL / timeout errors | Re-run the install; add `--default-timeout=120`. |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |
| Model file missing | Run `python -m src.train` (the app also auto-trains on first launch). |
