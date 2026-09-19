import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

@app.get("/")
def read_root():
    return {"status": "Study Assistant API is running"}

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