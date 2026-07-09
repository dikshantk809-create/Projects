<div align="center">

<img src="https://capsule-render.vercel.app/api?type=blur&color=0:0F2027,50:203A43,100:2C5364&height=220&section=header&text=📚%20Multimodal%20RAG&fontSize=58&fontColor=00D9FF&animation=fadeIn&desc=Text%20+%20Image%20+%20Table%20Understanding&descSize=20&descAlignY=75" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=00D9FF&center=true&vCenter=true&width=720&lines=Ask+Any+PDF+Anything+%F0%9F%93%84;Tables+%2B+Charts+Become+Searchable+%F0%9F%93%8A;Hybrid+Retrieval%3A+FAISS+%2B+BM25+%F0%9F%94%8D;Every+Answer+Has+a+Citation+%F0%9F%93%8C;Zero+Guessing%2C+Low+Hallucination+%E2%9C%85" alt="Typing SVG" />

<br/><br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![GPT-4o](https://img.shields.io/badge/GPT--4o_Vision-412991?style=for-the-badge&logo=openai&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-0467DF?style=for-the-badge&logo=meta&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)

<img src="https://img.shields.io/badge/Retrieval-Hybrid_(Dense+Sparse)-blueviolet?style=flat-square"/>
<img src="https://img.shields.io/badge/Fusion-Reciprocal_Rank-orange?style=flat-square"/>
<img src="https://img.shields.io/badge/Answers-Citation_Grounded-green?style=flat-square"/>
<img src="https://img.shields.io/badge/Tests-Offline_(No_API_Key)-red?style=flat-square"/>

</div>

---

## 🎯 What Is This?

> **PDF se sawaal pucho — answer milega document se grounded, exact page citation ke saath.**

Sirf text nahi — **tables aur images bhi**. Charts/diagrams ko GPT-4o vision describe karta hai, isliye wo bhi searchable ban jaate hain. Agar answer document mein nahi hai, system **guess nahi karta — bol deta hai "not in the document"**. 🎯

---

## 🏗️ How It Works

```mermaid
flowchart TB
    A["📄 PDF Upload"] --> B["⚙️ ingest.py"]
    B --> C["📝 Text Chunks<br/>(cleaned + overlap)"]
    B --> D["📊 Tables<br/>(→ Markdown)"]
    B --> E["🖼️ Images<br/>(GPT-4o vision captions)"]
    C --> F["🗄️ vectorstore.py"]
    D --> F
    E --> F
    F --> G["🧲 FAISS<br/>(semantic)"]
    F --> H["🔑 BM25<br/>(keyword)"]
    G --> I{"🔀 Reciprocal<br/>Rank Fusion"}
    H --> I
    J["❓ Question"] --> I
    I --> K["🧠 rag.py<br/>GPT-4o answers<br/>WITH citations [1][2]"]
    K --> L["💬 React Chat UI<br/>(clickable citation chips)"]

    style A fill:#0F2027,color:#fff,stroke:#00D9FF
    style B fill:#2C5364,color:#fff,stroke:#00D9FF
    style F fill:#203A43,color:#fff,stroke:#00D9FF,stroke-width:2px
    style G fill:#0467DF,color:#fff,stroke:#00D9FF
    style H fill:#FF9800,color:#000,stroke:#F57C00
    style I fill:#7F5AF0,color:#fff,stroke:#B721FF,stroke-width:3px
    style K fill:#009688,color:#fff,stroke:#00D9FF,stroke-width:3px
    style L fill:#61DAFB,color:#000,stroke:#0288D1
```

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 📄 Multimodal Ingestion
PDF teen tarah ke searchable pieces mein split hota hai — **text** (chunked with overlap), **tables** (Markdown mein converted), **images** (GPT-4o vision describes them).

</td>
<td width="50%" valign="top">

### 🔀 Hybrid Retrieval
**FAISS** semantic matches dhundhta hai, **BM25** exact keywords/names/numbers pakadta hai — **RRF** dono rankings ko fuse karke best results upar laata hai.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📌 Grounded Citations
Har claim ke saath **[1], [2]** citation — click karo aur exact source snippet dekho. Answer document mein nahi? System saaf bata dega.

</td>
<td width="50%" valign="top">

### 💬 Multi-Turn Chat
Follow-up questions conversation yaad rakhte hain. React UI — upload, ask, click citations. **No build step needed.**

</td>
</tr>
</table>

---

## 📂 Project Structure

```
📚 Multimodal-RAG-System/
│
├── ⚙️ ingest.py          → PDF → text/table/image-caption Documents
├── 🗄️ vectorstore.py     → Hybrid retriever: FAISS + BM25 + RRF
├── 🧠 rag.py             → Retrieve → GPT-4o grounded answers + citations
├── 🚀 main.py            → FastAPI: /ingest & /query endpoints
├── 💬 index.html         → React chat UI (single file!)
├── 🧪 test_rag.py        → Offline tests (no API key needed)
├── 📦 requirements.txt
└── 🔐 env.example
```

---

## ⚙️ Quick Start

```bash
# 1️⃣ Clone & install
git clone https://github.com/dikshantk809-create/Projects.git
cd "Projects/Multimodal RAG System"
pip install -r requirements.txt

# 2️⃣ API key
cp env.example .env       # paste your OpenAI key

# 3️⃣ Start the API
uvicorn main:app --reload

# 4️⃣ Open the UI
# → index.html browser mein kholo, ya:
python -m http.server 5500
# → visit http://localhost:5500
```

**Upload PDF → indexing ka wait karo → questions pucho → citation chips click karke source dekho.** 🎉

---

## 🔌 API

```bash
# 📥 Index a PDF
curl -F "file=@report.pdf" http://localhost:8000/ingest

# ❓ Ask a question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was total revenue in 2023?"}'
```

**Response:**

```json
{
  "answer": "...",
  "sources": [{ "n": 1, "page": 4, "type": "table" }]
}
```

---

## 🧪 Tests (No API Key Needed!)

```bash
pip install pytest
pytest -q
```

> Tests ek chhota PDF banate hain, extract karte hain, aur **poora hybrid-retrieval pipeline fake embeddings ke saath** chalate hain — completely offline. ✅

---

## 🗺️ Roadmap

- [x] Multimodal ingestion — text + tables + images
- [x] Hybrid retrieval (FAISS + BM25 + RRF)
- [x] Citation-grounded answers
- [x] Multi-turn chat + React UI
- [ ] 💾 Persist FAISS index (`save_local`/`load_local`)
- [ ] 🧠 Redis history for multi-user deployments
- [ ] 🎛️ Tune RRF weights per document type
- [ ] 📏 Labelled Q&A set for honest accuracy measurement

---

## 🔐 Security Note

> API file uploads accept karta hai aur external models call karta hai — publicly expose karne se pehle **auth, file-size limits & rate limiting** add karo.

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ If this made your PDFs smarter, drop a star!

*"Don't make the AI guess — make it cite."*

**Built with ❤️ & 📚 by Dikshant**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2C5364,100:0F2027&height=110&section=footer" width="100%"/>

</div>
