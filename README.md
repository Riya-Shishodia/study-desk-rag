# Study Desk — Multi-Subject RAG Study Assistant

A full-stack Retrieval-Augmented Generation (RAG) web application that lets students ask natural-language questions about their lecture notes and get answers grounded strictly in the actual course material — with source citations, and an honest "I don't know" when the answer isn't in the notes.

**Live app:** https://study-desk-rag.onrender.com
**Live API:** https://study-desk-rag-api.onrender.com

> Note: both are hosted on Render's free tier, which spins down after inactivity. The first request after idle time may take 30–50 seconds to wake up.

## What it does

- Answers questions using only the content of uploaded lecture PDFs — no hallucinated answers from general LLM knowledge
- Every answer includes the source file(s) it was pulled from
- Subject-based filtering (e.g., restrict search to OS-only or DBMS-only content)
- Persistent chat history (per-browser, via localStorage)
- New lecture PDFs can be added and indexed incrementally, without re-processing existing documents
- Automatic retry handling for transient LLM API failures

## How it works

1. **Extraction** — lecture PDFs are parsed and their text extracted (`pypdf`)
2. **Chunking** — extracted text is split into overlapping chunks to preserve context across boundaries
3. **Embedding** — each chunk is converted into a vector using Google's Gemini Embeddings API
4. **Storage** — vectors are stored in a local ChromaDB vector database, tagged with subject and source file
5. **Retrieval** — a user's question is embedded and matched against stored chunks via similarity search, optionally filtered by subject
6. **Generation** — the most relevant chunks are passed to Gemini as context, with an explicit instruction to answer only from that context

## Tech stack

**Backend:** Python, FastAPI, ChromaDB, Google Gemini API (embeddings + generation), pypdf
**Frontend:** HTML, CSS, JavaScript (no framework)
**Deployment:** Render (backend as a Web Service, frontend as a Static Site)

## Running it locally

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file inside `backend/` with:
GEMINI_KEY = your_key_here


Then embed your documents and start the server:
```bash
python embed_and_store.py
python -m uvicorn main:app --reload
```

**Frontend:**
Open `frontend/index.html` directly in a browser, or serve it with the VS Code Live Server extension. Update `API_URL` in `script.js` if pointing to a different backend.

## Adding new lecture content

1. Drop new PDFs into `documents/<subject>/` (e.g., `documents/os/os_4.pdf`)
2. Run `python embed_and_store.py` — it automatically detects and processes only the new files

## Project structure

study-desk-rag/
├── backend/
│ ├── extract_text.py # PDF text extraction
│ ├── chunking.py # Splits text into overlapping chunks
│ ├── embed_and_store.py # Generates embeddings, stores in ChromaDB
│ ├── main.py # FastAPI app and /ask endpoint
│ └── chroma_db/ # Persisted vector store
├── frontend/
│ ├── index.html
│ ├── style.css
│ └── script.js
└── documents/
├── os/
└── dbms/


## Author

Riya Shishodia — [LinkedIn](https://linkedin.com/in/riya-shishodia) · [GitHub](https://github.com/Riya-Shishodia)