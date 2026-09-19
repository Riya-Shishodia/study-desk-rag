import os
from dotenv import load_dotenv
from google import genai
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

# Allow your frontend (running on a different port) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development; we'll tighten this later
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    subject: str = "all"

def get_embedding(text):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

def search(query, top_k=3, subject="all"):
    query_embedding = get_embedding(query)

    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": top_k
    }

    #Only add a filter if a specific subject was chosen
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

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

@app.get("/")
def read_root():
    return {"status": "Study Assistant API is running"}

@app.post("/ask")
def ask_question(request: QuestionRequest):
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