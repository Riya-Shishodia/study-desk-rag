from extract_text import extract_all_documents
import os

def chunk_text(text, chunk_size=800, overlap=100):
    """
    Split text into overlapping chunks.
    chunk_size: roughly how many characters per chunk
    overlap: how many characters repeat between consecutive chunks
             (helps avoid cutting a sentence's meaning in half)
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

def chunk_all_documents(documents_folder):
    """
    Extract text from all PDFs, then chunk each document's text.
    Returns a list of dicts, each representing ONE chunk.
    """
    docs = extract_all_documents(documents_folder)
    all_chunks = []
    
    for doc in docs:
        text_chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(text_chunks):
            all_chunks.append({
                "subject": doc["subject"],
                "filename": doc["filename"],
                "chunk_id": i,
                "text": chunk
            })
    
    return all_chunks

if __name__ == "__main__":
    documents_folder = os.path.join("..", "documents")
    chunks = chunk_all_documents(documents_folder)
    
    print(f"Total chunks created: {len(chunks)}")
    print("\n--- Sample chunk ---")
    print(f"Subject: {chunks[0]['subject']}")
    print(f"File: {chunks[0]['filename']}")
    print(f"Chunk ID: {chunks[0]['chunk_id']}")
    print(f"Text preview: {chunks[0]['text'][:200]}...")
    