<div align="center">

<img src="https://capsule-render.vercel.app/api?type=shark&color=0:0F0C29,50:302B63,100:24243e&height=230&section=header&text=🛡️%20TruthLens%20AI&fontSize=60&fontColor=FFD700&animation=fadeIn&desc=Agentic%20AI%20for%20Explainable%20Misinformation%20Detection&descSize=17&descAlignY=75" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=FFD700&center=true&vCenter=true&width=720&lines=Detects+Fake+News+%2B+Explains+WHY+%F0%9F%94%8D;Multi-Agent+AI+Orchestration+%F0%9F%A4%96;RAG-Grounded+Fact+Checking+%F0%9F%93%9A;94.2%25+Accuracy+%C2%B7+0.947+ROC-AUC+%F0%9F%93%88;Fully+Offline+%C2%B7+No+API+Key+%C2%B7+Zero+Cost+%E2%9A%A1" alt="Typing SVG" />

<br/><br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama_(optional)-000000?style=for-the-badge&logo=ollama&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-Fact_Checking-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)

<img src="https://img.shields.io/badge/Accuracy-94.2%25-brightgreen?style=flat-square"/>
<img src="https://img.shields.io/badge/ROC--AUC-0.947-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/F1_Score-93.5%25-blueviolet?style=flat-square"/>
<img src="https://img.shields.io/badge/5--Fold_CV-94.8%25_±_0.8%25-orange?style=flat-square"/>
<img src="https://img.shields.io/badge/Runs-100%25_Offline-red?style=flat-square"/>

<br/>

🎓 **AI/ML Minor Degree Project** · Punjabi University, Patiala
**Dikshant Aggarwal** (Roll No. 12303021) · Guide: **Dr. Chandan Deep Singh**

</div>

---

## 🎯 What Is This?

> **Zyada-tar fake-news projects sirf ek label dete hain. TruthLens batata hai — KYUN.**

Ek **Agentic AI system** jo interpretable ML classifier + RAG fact-checking + multi-agent GenAI explanation layer combine karta hai — aur **fully offline laptop par chalta hai**. No API key. No cost. Demo kabhi fail nahi hota. 🛡️

---

## 🤖 Multi-Agent Architecture

```mermaid
flowchart LR
    A["📰 News Article"] --> B["🎯 ClassifierAgent<br/>TF-IDF + LogReg<br/>(per-word attribution)"]
    B --> C["🔍 ExplainerAgent<br/>Credibility Signals:<br/>sensationalism, clickbait,<br/>vague sourcing, citations"]
    C --> D["📚 FactCheckAgent<br/>RAG over verified<br/>knowledge base"]
    D --> E{"⚖️ Fusion"}
    E --> F["✅ Calibrated Verdict<br/>+ Visible Reasoning Trace"]
    F --> G["💬 Explanation<br/>Local LLM (Ollama)<br/>or template fallback"]

    style A fill:#0F0C29,color:#fff,stroke:#FFD700
    style B fill:#302B63,color:#fff,stroke:#FFD700,stroke-width:2px
    style C fill:#7F5AF0,color:#fff,stroke:#B721FF,stroke-width:2px
    style D fill:#009688,color:#fff,stroke:#00D9FF,stroke-width:2px
    style E fill:#FFD700,color:#000,stroke:#FFA000,stroke-width:3px
    style F fill:#22c55e,color:#000,stroke:#16a34a,stroke-width:2px
    style G fill:#FF4B4B,color:#fff,stroke:#FF416C
```

---

## ✨ Why It Stands Out

<table>
<tr>
<td width="50%" valign="top">

### 🎯 Interpretable ML Core
TF-IDF + Logistic Regression with **per-article term attribution** — aap dekh sakte ho *kaunse words* ne verdict drive kiya.

</td>
<td width="50%" valign="top">

### 🔍 Explainability Layer
Transparent **linguistic credibility-signal engine** — sensationalism, clickbait, vague sourcing, citations, dates, named entities.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📚 RAG Fact-Checking
Verified knowledge base par **semantic retrieval** — har verdict reference statements se grounded hota hai.

</td>
<td width="50%" valign="top">

### 🤖 Graceful GenAI
Local LLM (**Ollama**) available ho to natural explanations, warna deterministic templates — **demo kabhi offline fail nahi hota.**

</td>
</tr>
</table>

---

## 📊 Headline Results

<div align="center">

| Metric | Score |
|--------|:-----:|
| 🎯 **Accuracy** | **94.2%** |
| 🎚️ Precision (fake) | 93.4% |
| 🔁 Recall (fake) | 93.7% |
| ⚖️ **F1 (fake)** | **93.5%** |
| 📈 **ROC-AUC** | **0.947** |
| 🔄 5-Fold CV | **94.8% ± 0.8%** |

*Held-out test set: 600 articles · Confusion matrix: `[[TN=312, FP=18], [FN=17, TP=253]]`*

📊 Charts: [`images/`](./images)

</div>

---

## ⚡ Run It in 3 Commands

```bash
cd source_code
pip install -r requirements.txt
streamlit run app.py
```

> 🚀 App **auto-trains on first launch** aur `http://localhost:8501` par khul jaata hai. No API key needed!

---

## 📁 Submission Contents

```
🛡️ TruthLens-AI/
│
├── 💻 source_code/       → Complete runnable app (Streamlit + ML + agents + tests)
├── 📚 documentation/     → Setup, installation, usage & testing guides
├── 📄 report/            → Academic project report + Phase-1 analysis
├── 🎤 ppt/               → 20-slide viva presentation
├── 🖼️ images/            → Architecture diagram, flowchart, result charts
├── 🗃️ dataset/           → Training/test data + knowledge base
└── 🎯 interview_prep/    → 50 viva Q&A + HR/technical/defense questions
```

---

## 🧭 Where to Look First

| Step | Location | Why |
|------|----------|-----|
| 1️⃣ | [`report/`](./report) | Full project report (Abstract → References) |
| 2️⃣ | [`source_code/README.md`](./source_code/README.md) | Technical overview + quick start |
| 3️⃣ | [`ppt/`](./ppt) | Viva presentation |
| 4️⃣ | [`interview_prep/`](./interview_prep) | 50 Q&A — viva defense ready |

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-----------|
| 🎨 UI | Streamlit |
| 🧠 ML | scikit-learn (TF-IDF + Logistic Regression) |
| 📚 RAG | Semantic retrieval over verified KB |
| 🤖 Agents | ClassifierAgent → ExplainerAgent → FactCheckAgent |
| 💬 GenAI | Ollama (local LLM, optional) + template fallback |

</div>

---

## 🗺️ Roadmap

- [x] Interpretable classifier with term attribution
- [x] Credibility-signal explanation engine
- [x] RAG fact-checking over knowledge base
- [x] Multi-agent orchestration + reasoning trace
- [x] 94.2% accuracy · 0.947 ROC-AUC
- [ ] 🌐 Live web-source retrieval
- [ ] 🗣️ Multilingual misinformation detection (Hindi/Punjabi)
- [ ] 📱 Browser extension for real-time checking

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ Truth deserves a star!

*"Don't just detect misinformation — explain it."*

**Built with ❤️ & 🛡️ by Dikshant Aggarwal**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:24243e,50:302B63,100:0F0C29&height=110&section=footer" width="100%"/>

</div>
