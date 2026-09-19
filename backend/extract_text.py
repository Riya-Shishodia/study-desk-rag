import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    """Extract all text from a single PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_all_documents(documents_folder):
    """
    Go through each subject folder inside documents_folder,
    extract text from every PDF, and return a list of dicts
    like: {"subject": "os", "filename": "os_1.pdf", "text": "..."}
    """
    all_docs = []
    
    for subject in os.listdir(documents_folder):
        subject_path = os.path.join(documents_folder, subject)
        if not os.path.isdir(subject_path):
            continue
        
        for filename in os.listdir(subject_path):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(subject_path, filename)
                print(f"Extracting: {subject}/{filename}")
                text = extract_text_from_pdf(pdf_path)
                all_docs.append({
                    "subject": subject,
                    "filename": filename,
                    "text": text
                })
    
    return all_docs

if __name__ == "__main__":
    documents_folder = os.path.join("..", "documents")
    docs = extract_all_documents(documents_folder)
    
    print(f"\nTotal documents extracted: {len(docs)}")
    for doc in docs:
        print(f"- {doc['subject']}/{doc['filename']}: {len(doc['text'])} characters extracted")