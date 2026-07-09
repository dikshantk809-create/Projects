<div align="center">

<img src="https://capsule-render.vercel.app/api?type=transparent&color=gradient&customColorList=6,11,20&height=180&section=header&text=🤖%20Autonomous%20AI%20Agent&fontSize=48&fontColor=7F5AF0&animation=twinkling&desc=Tool%20Use%20+%20Memory%20+%20Multi-Step%20Reasoning&descSize=18&descAlignY=75" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=7F5AF0&center=true&vCenter=true&width=720&lines=Think+%E2%86%92+Act+%E2%86%92+Observe+%E2%86%92+Repeat+%F0%9F%94%81;10+Built-in+Tools+%F0%9F%9B%A0%EF%B8%8F;Streaming+Responses+via+SSE+%E2%9A%A1;Per-Session+Memory+with+Redis+%F0%9F%A7%A0;Built+with+LangGraph+%F0%9F%95%B8%EF%B8%8F" alt="Typing SVG" />

<br/><br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_API-412991?style=for-the-badge&logo=openai&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<img src="https://img.shields.io/badge/Agent_Loop-LangGraph_FSM-blueviolet?style=flat-square"/>
<img src="https://img.shields.io/badge/Tools-10_Built--in-green?style=flat-square"/>
<img src="https://img.shields.io/badge/Output-Token_Streaming-orange?style=flat-square"/>
<img src="https://img.shields.io/badge/Memory-Session_Isolated-red?style=flat-square"/>

</div>

---

## 🧠 What Is This?

> **Ek AI agent jo khud decide karta hai** — kab web search karna hai, kab code chalana hai, kab file padhni hai. One-shot reply nahi — **multi-step reasoning loop**.

Built with **LangGraph**, served as a **streaming FastAPI** API, with **Redis-backed per-session memory** — parallel users kabhi context mix nahi karte.

---

## 🔁 The Agent Loop

```mermaid
flowchart LR
    S(["🚀 START"]) --> A["🧠 Agent Node<br/>(LLM thinks)"]
    A -->|"🛠️ wants a tool"| T["⚙️ Tools Node<br/>(executes)"]
    T -->|"📨 results back"| A
    A -->|"✅ final answer"| E(["🏁 END"])

    style S fill:#16161a,color:#fff,stroke:#7F5AF0
    style A fill:#7F5AF0,color:#fff,stroke:#2CB67D,stroke-width:3px
    style T fill:#2CB67D,color:#fff,stroke:#7F5AF0,stroke-width:2px
    style E fill:#16161a,color:#fff,stroke:#2CB67D
```

**Think → Call a tool → Observe result → Think again → Answer.** Ye loop hi ise agent banata hai — conditional edge (`tools_condition`) decide karti hai flow tools par jaye ya END par.

---

## 🛠️ 10 Built-in Tools

<div align="center">

| | | |
|---|---|---|
| 🔍 Web Search | 📚 Wikipedia | 🌐 Fetch URL |
| 🧮 Calculator | 🐍 Python Execution | 🕐 Date/Time |
| 📝 Word Count | 📖 Read File | 💾 Write File |
| 📏 Unit Conversion | ➕ *Add your own in minutes* | |

</div>

---

## ✨ Key Features

<table>
<tr>
<td width="50%" valign="top">

### 🔁 Multi-Step Reasoning
Agent ek loop mein sochta hai — tool call karta hai, result dekhta hai, phir aage ka plan banata hai. Complex tasks automatically decompose ho jaate hain.

</td>
<td width="50%" valign="top">

### ⚡ Token Streaming
Answers **Server-Sent Events** se token-by-token stream hote hain — client ko text turant dikhna shuru ho jata hai.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧠 Session Memory
Har session ka apna **Redis key** — do users ya do parallel runs fully isolated. Same `session_id` bhejo, conversation continue.

</td>
<td width="50%" valign="top">

### 🧩 Plug-and-Play Tools
`@tool` decorator + `ALL_TOOLS` list mein add karo — LLM automatically pick kar leta hai. No other changes needed.

</td>
</tr>
</table>

---

## 📂 Project Structure

```
🤖 Autonomous-AI-Agent/
│
├── 🕸️ agent.py             → LangGraph graph (the agent loop)
├── 🛠️ tools.py             → 10 tools the agent can call
├── 🧠 memory.py            → Redis-backed session memory
├── 🚀 main.py              → FastAPI app + streaming /chat endpoint
├── 💻 client_example.py    → Terminal streaming client
├── 📦 requirements.txt
└── 🔐 env.example
```

---

## ⚙️ Quick Start

```bash
# 1️⃣ Clone & install
git clone https://github.com/dikshantk809-create/Projects.git
cd "Projects/Autonomous AI Agent with Tool Use & Memory"
pip install -r requirements.txt

# 2️⃣ Add your API key
cp env.example .env       # paste your OpenAI key inside

# 3️⃣ Start Redis (Docker)
docker run -d -p 6379:6379 --name agent-redis redis

# 4️⃣ Launch the API
uvicorn main:app --reload
```

**Try it:**

```bash
# 🌐 Browser → http://localhost:8000/docs

# 💻 Streaming client
python client_example.py "Search the web for today's top AI news and summarise it"

# ⚡ Direct (no server)
python agent.py "What is 25 * 17, and who is the CEO of OpenAI?"
```

---

## 🔌 API

```http
POST /chat
{ "message": "your question", "session_id": "optional-id" }
```

**Response stream (SSE):**

```
{"type":"session", ...}          ← session id milta hai
{"type":"token","content":"..."} ← tokens aate rehte hain
{"type":"done"}                  ← complete
```

> 💡 Same `session_id` dubara bhejo → conversation **memory ke saath** continue hogi.

---

## ➕ Add Your Own Tool (30 seconds)

```python
@tool
def reverse_text(text: str) -> str:
    """Reverse a piece of text."""
    return text[::-1]
```

Bas `ALL_TOOLS` list mein add karo — **LLM automatically use karna shuru kar dega.** 🎉

---

## 🗺️ Roadmap

- [x] LangGraph agent loop with 10 tools
- [x] SSE token streaming
- [x] Redis per-session memory
- [ ] 📉 History trimming/summarisation (token savings)
- [ ] 🔍 Stream tool steps to client (not just final tokens)
- [ ] 📦 Sandboxed Python executor
- [ ] 🔐 Auth + rate limiting for public deployment

---

## ⚠️ Security Note

> `python_repl` aur file tools **host machine par** chalte hain — local dev/demo ke liye theek hai, lekin publicly expose karne se pehle **sandbox** karo.

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ Star this repo if agents excite you!

*"Give an AI tools and memory, and it stops answering — it starts doing."*

**Built with ❤️ & 🕸️ by Dikshant**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2CB67D,100:7F5AF0&height=110&section=footer" width="100%"/>

</div>
