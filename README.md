# 🧠 DocMind AI — Advanced RAG Intelligence Platform

> Built with **Endee Vector Database** | 20 AI-powered features | FastAPI + Vanilla JS

---

## 🚀 What It Does

DocMind AI is a full-stack RAG (Retrieval Augmented Generation) platform that transforms any PDF document into an interactive AI-powered knowledge base. Upload a PDF and instantly unlock 20 intelligent features.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Ask questions, get answers with source references |
| 🚨 **Hallucination Detector** | Verifies every AI answer against document |
| ⚡ **Confidence Score** | HIGH / MEDIUM / LOW rating per answer |
| 📍 **Source Highlighter** | Shows exact page and passage used |
| 💡 **Smart Question Suggester** | Auto-suggests 5 questions on upload |
| 💬 **Chat Memory** | Remembers conversation context |
| 🎓 **Tutor Mode** | Socratic teaching style |
| 🌐 **Web + Doc Hybrid** | Combines document + live web search |
| 🗺️ **Mind Map** | Visual topic structure |
| 🕸️ **Knowledge Graph** | Entity relationship visualization |
| 😊 **Tone Analyzer** | Sentiment, emotions, formality |
| 🃏 **Flashcard Generator** | Auto study cards (exportable CSV) |
| 📝 **Quiz Generator** | MCQ quiz with scoring |
| 📅 **Timeline Extractor** | Dates and events visual timeline |
| ✅ **Action Items** | Extracts tasks and to-dos |
| 🥊 **Document Debate** | Compare two documents head-to-head |
| 📧 **Executive Email** | One-click professional summary email |
| 🔍 **Facts vs Opinions** | Color-coded classification |
| ⚠️ **Contradiction Finder** | Finds conflicting statements |
| 📚 **Multi-Doc Search** | Search across all documents simultaneously |

---

## 🏗️ System Design

```
[User Browser]
     │
     ▼
[Frontend: HTML/CSS/JS]
     │  REST API calls
     ▼
[FastAPI Backend]
     │
     ├── /api/documents  → Upload, Ask, Multi-doc
     ├── /api/analysis   → MindMap, Tone, Debate, Email...
     ├── /api/quiz       → Flashcards, Quiz, Score
     └── /api/search     → Semantic, Hybrid, Evolution
     │
     ├── [Endee Vector DB] ← PDF chunks stored as embeddings
     ├── [OpenAI GPT-4o]   ← LLM for answers & analysis
     └── [SerpAPI]         ← Optional web search
```

---

## 🔧 How Endee Is Used

Endee serves as the **core vector database** for this platform:

1. PDF text is split into chunks (1000 chars, 200 overlap)
2. Each chunk is embedded using OpenAI `text-embedding-3-small`
3. Embeddings are stored in **Endee vector collections**
4. On every question, the query is embedded and **Endee performs similarity search**
5. Top-K most relevant chunks are retrieved and passed to GPT-4o

---

## ⚙️ Setup Instructions

### 1. Clone & Fork
```bash
# Star and fork https://github.com/endee-io/endee first!
git clone https://github.com/YOUR_USERNAME/endee.git
cd endee
```

### 2. Install Backend
```bash
cd advanced-rag-platform/backend
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your keys:
# OPENAI_API_KEY=sk-...
# SERPAPI_KEY=...  (optional, for web search)
```

### 4. Run Backend
```bash
python main.py
# Server starts at http://localhost:8000
```

### 5. Open Frontend
```
Open browser → http://localhost:8000
```

---

## 📁 Project Structure

```
advanced-rag-platform/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration & env vars
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── documents.py           # Upload, ask, multi-doc
│   │   ├── analysis.py            # All analysis features
│   │   ├── quiz.py                # Quiz & flashcards
│   │   └── search.py              # Semantic & hybrid search
│   ├── services/
│   │   ├── rag_service.py         # Core RAG pipeline
│   │   ├── hallucination_service.py
│   │   ├── analysis_service.py    # MindMap, KG, Tone...
│   │   ├── flashcard_service.py
│   │   └── web_search_service.py
│   └── utils/
│       ├── embeddings.py          # Endee vector store
│       └── pdf_processor.py       # PDF text extraction
└── frontend/
    ├── index.html                 # Single page app
    ├── styles.css                 # Dark theme UI
    └── app.js                     # All frontend logic
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Vector DB | **Endee** (ChromaDB compatible) |
| LLM | OpenAI GPT-4o |
| Embeddings | OpenAI text-embedding-3-small |
| Backend | FastAPI + Python |
| Frontend | Vanilla JS + HTML/CSS |
| PDF Processing | pdfplumber + PyPDF2 |
| Knowledge Graph | vis.js network |
| Web Search | SerpAPI (optional) |

---

## 📸 Screenshots

> Upload PDF → Ask questions → Get verified answers with source references, hallucination detection, and 20 more intelligent features.

---

## 👨‍💻 Author

Built for the **Endee.io Internship Assessment**  
GitHub: [your-username](https://github.com/your-username)

---

⭐ **Don't forget to star [endee-io/endee](https://github.com/endee-io/endee)!**
