# Phase 1 — AI/ML Project Market Analysis & Selection (2026)

**Student:** Dikshant Aggarwal  **Roll No:** 12303021
**University:** Punjabi University, Patiala  **Guide:** Dr. Chandan Deep Singh
**Analyst role:** Senior AI Engineer perspective (Google / Amazon / Microsoft / NVIDIA / OpenAI lens)

---

## 1. 2026 Market Context (why the shortlist looks like this)

The 2026 hiring market for AI/ML interns has shifted decisively from *model-building* to *systems-building*. Evidence used to anchor this analysis:

- Job postings mentioning **"LLM" or "RAG" grew ~340% since 2024**, while generic "machine learning" postings declined ~18%.
- **RAG architecture appears in ~65%** of applied-LLM job listings; prompt-engineering demand rose ~135% in a single year.
- **Agentic AI** frameworks (LangGraph, CrewAI, Claude Agent SDK) and **multimodal** systems are the fastest-growing specializations.
- Over **75% of AI postings require domain specialization** — pure generalists are screened out early.

**Implication for a college project:** the highest-leverage project is one that (a) trains a real, measurable ML model, (b) layers **RAG + a multi-agent GenAI** system on top, and (c) is anchored to a **specific real-world domain**. It must run **free and fully offline on a laptop** (no paid API key) so it can be demonstrated live without risk.

---

## 2. Top 5 Projects (scored)

> Scoring key: Resume / Placement / Internship / Industry each out of 10.

### Project 1 — TruthLens AI · Agentic Misinformation Detector
- **Problem Statement:** Generative AI has made fake news cheap and convincing; people and platforms cannot manually verify the flood of content.
- **Why It Matters:** Misinformation affects elections, health, and finance. Detection + *explanation* is a 2026 priority for every social/media/search company.
- **AI/ML Technologies:** TF-IDF + calibrated linear classifier (interpretable core), sentence-transformer embeddings, FAISS semantic retrieval (RAG), multi-agent GenAI orchestration (Classifier → Explainer → Fact-Check → Verdict), local LLM (Ollama) with graceful offline fallback, Streamlit.
- **Difficulty:** Intermediate → Advanced
- **Resume 9.5 · Placement 9.5 · Internship 9 · Industry 9.5**

### Project 2 — DocuMind · Agentic RAG "Chat with your Documents"
- **Problem:** Knowledge workers waste hours searching long PDFs/manuals.
- **Why It Matters:** RAG is the single most requested 2026 skill.
- **Tech:** Embeddings, FAISS, chunking, RAG, agent routing, local LLM, Streamlit.
- **Difficulty:** Intermediate
- **Resume 9.5 · Placement 9 · Internship 9.5 · Industry 10**
- **Caveat:** Heavily saturated (everyone builds one); answer quality depends on the local LLM, which is a live-demo risk; weaker "trained-model + accuracy" story for the report.

### Project 3 — CareerForge AI · Agentic Resume ↔ JD Optimizer
- **Problem:** ATS filters reject strong candidates over formatting/keyword gaps.
- **Why It Matters:** Universally relatable; great demo.
- **Tech:** Embeddings similarity, NER, RAG over a skills KB, rewrite agent, Streamlit.
- **Difficulty:** Intermediate
- **Resume 8.5 · Placement 9 · Internship 8.5 · Industry 8.5**
- **Caveat:** Leans on prompt-engineering; lighter ML depth.

### Project 4 — MediScan AI · X-ray Classifier + GenAI Report
- **Problem:** Radiology backlogs; assistive triage.
- **Why It Matters:** High-impact applied CV.
- **Tech:** CNN/transfer learning (ResNet), Grad-CAM, GenAI report generation.
- **Difficulty:** Advanced
- **Resume 9 · Placement 8.5 · Internship 8.5 · Industry 9**
- **Caveat:** Heavy datasets + compute; medical domain is sensitive; harder to demo reliably offline on a laptop.

### Project 5 — FinSentinel · Fraud Detection + Agentic Alert Explainer
- **Problem:** Card fraud detection with human-readable alerts.
- **Why It Matters:** Core fintech use-case.
- **Tech:** Imbalanced-learning (XGBoost/IsolationForest), SHAP, agentic explanation.
- **Difficulty:** Intermediate → Advanced
- **Resume 8.5 · Placement 8.5 · Internship 8 · Industry 9**
- **Caveat:** Tabular data is less visually impressive; GenAI layer is thinner.

---

## 3. Ranking

| Rank | Project | Resume | Placement | Internship | Industry | **Total /40** |
|------|---------|:------:|:---------:|:----------:|:--------:|:-------------:|
| **1** | **TruthLens AI** | 9.5 | 9.5 | 9.0 | 9.5 | **37.5** |
| 2 | DocuMind (RAG) | 9.5 | 9.0 | 9.5 | 10.0 | 38.0* |
| 3 | CareerForge AI | 8.5 | 9.0 | 8.5 | 8.5 | 34.5 |
| 4 | MediScan AI | 9.0 | 8.5 | 8.5 | 9.0 | 35.0 |
| 5 | FinSentinel | 8.5 | 8.5 | 8.0 | 9.0 | 34.0 |

\*DocuMind scores marginally higher on raw keyword demand, **but** it loses on three project-specific constraints that matter more for *this* submission (see below), so it is ranked #2.

---

## 4. Selected Project → **TruthLens AI**

TruthLens is selected as the single best project because it **dominates on the constraints that actually decide this submission**, not just raw market hype:

1. **Fills every required report/PPT section cleanly.** It has a genuinely *trained* model → real Accuracy/Precision/Recall/F1, a confusion matrix, an ROC curve, and a labeled dataset. Pure RAG projects struggle to produce these.
2. **Reliably demonstrable live and offline.** The interpretable classifier core *always* works on a laptop with no API key. The GenAI/agent layer enhances output when a local LLM is present and **degrades gracefully to a template/extractive explanation** when it isn't — so the demo never fails in front of the examiner.
3. **Maximum resume surface from one project.** It legitimately lets Dikshant claim: NLP, scikit-learn, TF-IDF, sentence-transformers **embeddings**, **FAISS vector search**, **RAG**, **multi-agent orchestration**, model evaluation, and Streamlit deployment — covering the exact 2026 keywords (RAG + agents + domain specialization) in a single defensible story.
4. **Strong, current, real-world impact narrative.** "Detecting GenAI-amplified misinformation" is timely, socially meaningful, and easy to defend in a viva.
5. **Innovation angle:** most student fake-news projects stop at a classifier. TruthLens adds a **multi-agent explanation + retrieval-augmented fact-check** layer, which is what makes it look industry-level rather than a tutorial clone.

**Verdict:** Build **TruthLens AI — an Agentic AI system for Fake-News & Misinformation Detection with Explainable, Retrieval-Augmented Verdicts.**

---

*Sources informing the 2026 market context: Talent500 AI/ML Job Trends 2026; MirrorCV AI Engineer Resume Guide 2026; Acceler8/Second Talent in-demand-skills reports; finalproject.in & careerera 2026 GenAI project guides.*
