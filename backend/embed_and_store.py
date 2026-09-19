import os
import time
from dotenv import load_dotenv
from google import genai
import chromadb
from chunking import chunk_all_documents

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found! Check your .env file.")

client = genai.Client(api_key=api_key)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="study_assistant")

def get_embedding(text):
    """Call Gemini's embedding model on a single piece of text."""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

def get_already_stored_filenames():
    """Check what files are already in the ChromaDB collection."""
    existing = collection.get()
    stored_files = set()
    for metadata in existing["metadatas"]:
        stored_files.add(f"{metadata['subject']}/{metadata['filename']}")
    return stored_files

def embed_and_store_all_chunks(documents_folder):
    all_chunks = chunk_all_documents(documents_folder)
    already_stored = get_already_stored_filenames()
    
    new_chunks = [
        c for c in all_chunks 
        if f"{c['subject']}/{c['filename']}" not in already_stored
    ]
    
    if not new_chunks:
        print("No new files to process. Everything is already embedded.")
        return
    
    print(f"Found {len(new_chunks)} new chunks to embed (skipping already-processed files).\n")

    for i, chunk in enumerate(new_chunks):
        embedding = get_embedding(chunk["text"])
        chunk_id = f"{chunk['subject']}_{chunk['filename']}_{chunk['chunk_id']}"

        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[{
                "subject": chunk["subject"],
                "filename": chunk["filename"],
                "chunk_id": chunk["chunk_id"]
            }]
        )

        print(f"[{i+1}/{len(new_chunks)}] Stored: {chunk_id}")
        time.sleep(0.5)

    print(f"\nDone! Added {len(new_chunks)} new chunks.")
    print(f"Total items in collection now: {collection.count()}")

if __name__ == "__main__":
    documents_folder = os.path.join("..", "documents")
    embed_and_store_all_chunks(documents_folder)