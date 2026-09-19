import os
from dotenv import load_dotenv
from google import genai
import chromadb

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="study_assistant")

def get_embedding(text):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

def search(query, top_k=3):
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results

def generate_answer(query, retrieved_chunks):
    """Build a prompt with retrieved context and ask Gemini to answer."""
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

if __name__ == "__main__":
    query = input("Ask a question about OS or DBMS: ")
    
    results = search(query)
    retrieved_texts = results['documents'][0]
    metadatas = results['metadatas'][0]
    
    print("\nGenerating answer...\n")
    answer = generate_answer(query, retrieved_texts)
    
    print("=== ANSWER ===")
    print(answer)
    
    print("\n=== SOURCES ===")
    for meta in metadatas:
        print(f"- {meta['subject']}/{meta['filename']}")