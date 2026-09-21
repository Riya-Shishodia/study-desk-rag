import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
import chromadb
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
from pathlib import Path
from extract_text import extract_text_from_pdf
from chunking import chunk_text

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="study_assistant")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    subject: str = "all"

def process_and_store_pdf(pdf_path: str, subject: str, filename: str):
    """Extract, chunk, embed, and store a single newly-uploaded PDF — batched."""
    text = extract_text_from_pdf(pdf_path)
    text_chunks = chunk_text(text)

    if not text_chunks:
        return 0

    # One (or a few) API calls instead of one-per-chunk
    embeddings = get_embeddings_batch(text_chunks)

    ids = [f"{subject}_{filename}_{i}" for i in range(len(text_chunks))]
    metadatas = [
        {"subject": subject, "filename": filename, "chunk_id": i}
        for i in range(len(text_chunks))
    ]

    # One database write instead of one per chunk too
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=text_chunks,
        metadatas=metadatas
    )

    return len(text_chunks)

def call_with_retry(func, max_retries=3, base_delay=2):
    """
    Call a Gemini API function, retrying if it fails due to
    temporary server overload (503) or rate limiting (429).
    Waits longer between each retry (2s, 4s, 8s...).
    """
    for attempt in range(max_retries):
        try:
            return func()
        except genai_errors.ServerError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = base_delay * (2 ** attempt)
            print(f"Gemini server busy (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
        except genai_errors.ClientError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"Rate limited (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

def get_embedding(text):
    def call():
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return result.embeddings[0].values
    return call_with_retry(call)

def get_embeddings_batch(texts, batch_size=50):
    """
    Embed multiple texts in as few API calls as possible.
    Splits into batches of `batch_size` as a safety margin against
    any request-size limits, rather than sending everything in one call.
    """
    all_embeddings = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        def call():
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=batch
            )
            return [e.values for e in result.embeddings]

        batch_embeddings = call_with_retry(call)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings

def search(query, top_k=3, subject="all"):
    query_embedding = get_embedding(query)

    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": top_k
    }

    if subject != "all":
        query_params["where"] = {"subject": subject}

    results = collection.query(**query_params)
    return results

def generate_answer(query, retrieved_chunks):
    context = "\n\n---\n\n".join(retrieved_chunks)

    prompt = f"""Answer the question using ONLY the context below. If the answer isn't in the context, say you don't know based on the provided material.

Context:
{context}

Question: {query}

Answer:"""

    def call():
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        return response.text

    return call_with_retry(call)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), subject: str = Form(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported."}

    if subject not in ("os", "dbms"):
        return {"error": "Subject must be 'os' or 'dbms'."}

    # Save the uploaded file temporarily so pypdf can read it
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunk_count = process_and_store_pdf(str(temp_path), subject, file.filename)
    except Exception as e:
        return {"error": f"Failed to process file: {str(e)}"}
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "message": f"Successfully processed '{file.filename}'",
        "chunks_added": chunk_count,
        "note": "This file is searchable now, but won't persist after the server restarts (free-tier hosting limitation)."
    }

@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        results = search(request.question, subject=request.subject)
        retrieved_texts = results['documents'][0]
        metadatas = results['metadatas'][0]

        if not retrieved_texts:
            return {
                "answer": "No relevant content found for this subject filter.",
                "sources": []
            }

        answer = generate_answer(request.question, retrieved_texts)
        sources = list(set([f"{m['subject']}/{m['filename']}" for m in metadatas]))

        return {
            "answer": answer,
            "sources": sources
        }
    except genai_errors.ServerError:
        return {
            "answer": "The AI service is temporarily overloaded. Please try asking again in a moment.",
            "sources": []
        }