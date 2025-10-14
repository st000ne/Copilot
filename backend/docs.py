import os
from typing import List, Dict
from dotenv import load_dotenv
from pydantic import SecretStr
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from backend.helper import _extract_texts_from_faiss_index
from backend.embeddings_cache import get_or_create_embedding

# -------------------------------------------------
# Configuration
# -------------------------------------------------
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

DOCS_INDEX_PATH = "backend/memory/faiss_docs_index"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=SecretStr(OPENAI_API_KEY))

# -------------------------------------------------
# Index Utilities
# -------------------------------------------------
def get_or_create_docs_index() -> FAISS:
    if os.path.exists(DOCS_INDEX_PATH):
        return FAISS.load_local(DOCS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    return FAISS.from_texts(["init"], embeddings)


def save_docs_index(index: FAISS):
    os.makedirs(DOCS_INDEX_PATH, exist_ok=True)
    index.save_local(DOCS_INDEX_PATH)


# -------------------------------------------------
# CRUD Operations
# -------------------------------------------------
def add_document(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    duplicate_threshold: float = 0.9,
):
    """
    Add a long document text to the FAISS docs index.
    Text will be split into chunks and stored as Documents.
    """
    text = text.strip()
    if not text:
        return {"added": 0, "reason": "Empty text"}

    index = get_or_create_docs_index()

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_text(text)

    added = 0
    new_docs = []

    for chunk in chunks:
        # Skip near-duplicate chunks
        existing = index.similarity_search_with_score(chunk, k=1)
        if existing:
            _, dist = existing[0]
            if dist < (1 - duplicate_threshold):
                continue

        new_docs.append(Document(page_content=chunk))
        added += 1

    if new_docs:
        index.add_documents(new_docs)  # ✅ same as in memory.py
        save_docs_index(index)

    return {"added": added, "chunks": len(chunks)}


def query_docs(query: str, threshold: float = 0.75, k: int = 5) -> List[Dict]:
    index = get_or_create_docs_index()
    docs_with_scores = index.similarity_search_with_score(query, k=k)

    results = []
    for doc, dist in docs_with_scores:
        sim = 1 - dist / 2
        if sim >= threshold:
            results.append({"content": doc.page_content, "score": sim})

    return results


def list_documents() -> List[str]:
    """List all stored document chunks."""
    index = get_or_create_docs_index()
    return _extract_texts_from_faiss_index(index)


def edit_document(old_text: str, new_text: str):
    """Replace a document chunk by text match."""
    index = get_or_create_docs_index()
    all_texts = _extract_texts_from_faiss_index(index)
    if old_text not in all_texts:
        return {"edited": False, "reason": "Chunk not found"}

    new_index = FAISS.from_texts([t if t != old_text else new_text for t in all_texts], embeddings)
    save_docs_index(new_index)
    return {"edited": True}


def delete_document(text: str):
    """Delete a document chunk by content match."""
    index = get_or_create_docs_index()
    all_texts = _extract_texts_from_faiss_index(index)
    if text not in all_texts:
        return {"deleted": False, "reason": "Chunk not found"}

    remaining = [t for t in all_texts if t != text]
    new_index = FAISS.from_texts(remaining, embeddings)
    save_docs_index(new_index)
    return {"deleted": True}
