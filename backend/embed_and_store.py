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

def get_embeddings_batch(texts, batch_size=50):
    """
    Embed multiple texts in as few API calls as possible.
    Splits into batches of `batch_size` as a safety margin against
    any request-size limits, rather than sending everything in one call.
    """
    all_embeddings = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch
        )
        all_embeddings.extend([e.values for e in result.embeddings])
        print(f"Embedded batch {start // batch_size + 1} ({len(batch)} chunks)")
        time.sleep(0.5)  # small pause between batches, not between every single chunk

    return all_embeddings

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

    texts = [c["text"] for c in new_chunks]
    embeddings = get_embeddings_batch(texts)

    ids = [
        f"{c['subject']}_{c['filename']}_{c['chunk_id']}" for c in new_chunks
    ]
    metadatas = [
        {"subject": c["subject"], "filename": c["filename"], "chunk_id": c["chunk_id"]}
        for c in new_chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

    print(f"\nDone! Added {len(new_chunks)} new chunks.")
    print(f"Total items in collection now: {collection.count()}")

if __name__ == "__main__":
    documents_folder = os.path.join("..", "documents")
    embed_and_store_all_chunks(documents_folder)