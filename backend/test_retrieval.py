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
    """Embed the query and find the most similar chunks."""
    query_embedding = get_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    return results

if __name__ == "__main__":
    query = input("Ask a question about OS or DBMS: ")
    results = search(query)
    
    print(f"\nTop {len(results['documents'][0])} matching chunks:\n")
    for i in range(len(results['documents'][0])):
        metadata = results['metadatas'][0][i]
        text = results['documents'][0][i]
        distance = results['distances'][0][i]
        
        print(f"--- Match {i+1} (subject: {metadata['subject']}, file: {metadata['filename']}, distance: {distance:.4f}) ---")
        print(text[:300])
        print()