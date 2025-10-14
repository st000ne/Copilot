import uuid
import os
from typing import List, Dict
from dotenv import load_dotenv
from pydantic import SecretStr
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from backend.helper import _extract_texts_from_faiss_index

# -------------------------------------------------
# Configuration
# -------------------------------------------------
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

EMBEDDINGS_PATH = "backend/memory/faiss_index"
os.makedirs("backend/memory", exist_ok=True)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small", openai_api_key=SecretStr(OPENAI_API_KEY)
)

# -------------------------------------------------
# FAISS Index Utilities
# -------------------------------------------------
def get_or_create_faiss_index() -> FAISS:
    """Load or create FAISS index for factual memories."""
    if os.path.exists(EMBEDDINGS_PATH):
        return FAISS.load_local(EMBEDDINGS_PATH, embeddings, allow_dangerous_deserialization=True)
    return FAISS.from_texts(["System initialized memory store."], embeddings, normalize_L2=True)


def save_faiss_index(index: FAISS):
    os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
    index.save_local(EMBEDDINGS_PATH)


def extract_memories_from_index() -> List[str]:
    """Return all memory texts from FAISS index."""
    index = get_or_create_faiss_index()
    return _extract_texts_from_faiss_index(index)

# -------------------------------------------------
# CRUD Operations
# -------------------------------------------------
def add_memory(text: str, duplicate_threshold: float = 0.9):
    """
    Add a memory (fact) to FAISS index, skipping duplicates.
    Incremental addition without rebuilding the index.
    """
    text = text.strip()
    if not text:
        return {"added": 0, "reason": "Empty text"}

    index = get_or_create_faiss_index()

    # Check for duplicates using similarity
    existing = index.similarity_search_with_score(text, k=1)
    if existing:
        closest_text, score = existing[0]
        if score < (1 - duplicate_threshold):
            return {"added": 0, "reason": "Duplicate detected"}

    # Create Document and add incrementally
    doc = Document(page_content=text)
    index.add_documents([doc])  # no need to pass embed function
    save_faiss_index(index)

    return {"added": 1, "text": text}


def query_memory(query: str, threshold: float = 0.5):
    """Hybrid search through FAISS memories (semantic + keyword)."""
    results = []

    if not os.path.exists(EMBEDDINGS_PATH):
        return []

    index = get_or_create_faiss_index()
    docs_and_scores = index.similarity_search_with_score(query, k=10)
    for doc, dist in docs_and_scores:
        sim = 1 - dist
        if sim >= threshold:
            results.append({"content": doc.page_content, "score": sim})

    # Keyword boost: include any memory containing query words
    all_texts = _extract_texts_from_faiss_index(index)
    for text in all_texts:
        if any(word.lower() in text.lower() for word in query.split()):
            results.append({"content": text, "score": 0.9})

    # Deduplicate & sort
    seen, unique = set(), []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["content"] not in seen:
            seen.add(r["content"])
            unique.append(r)

    return unique


def list_memories() -> Dict[str, List[str]]:
    """Return all stored factual memories."""
    return {"facts": extract_memories_from_index()}


def edit_memory(old_text: str, new_text: str, duplicate_threshold: float = 0.9):
    """
    Edit an existing memory text in FAISS.
    Incremental but accurate: rebuilds without old_text, adds new_text.
    """
    old_text, new_text = old_text.strip(), new_text.strip()
    if not new_text:
        return {"edited": False, "reason": "Empty new text"}

    index = get_or_create_faiss_index()
    all_texts = _extract_texts_from_faiss_index(index)

    if old_text not in all_texts:
        return {"edited": False, "reason": "Memory not found"}

    # Check duplicates (excluding old_text)
    existing = index.similarity_search_with_score(new_text, k=1)
    if existing:
        doc, score = existing[0]
        if doc.page_content != old_text and score < (1 - duplicate_threshold):
            return {"edited": False, "reason": "Duplicate detected"}

    # Build new FAISS index from scratch (excluding old_text)
    filtered_texts = [t for t in all_texts if t != old_text] + [new_text]
    docs = [Document(page_content=t) for t in filtered_texts]
    new_index = FAISS.from_documents(docs, embeddings, normalize_L2=True)
    save_faiss_index(new_index)

    return {"edited": True, "text": new_text}


def delete_memory(old_text: str):
    """
    Delete a memory text from FAISS by rebuilding index.
    """
    old_text = old_text.strip()
    index = get_or_create_faiss_index()
    all_texts = _extract_texts_from_faiss_index(index)

    if old_text not in all_texts:
        return {"deleted": False, "reason": "Memory not found"}

    filtered_texts = [t for t in all_texts if t != old_text]
    docs = [Document(page_content=t) for t in filtered_texts]
    new_index = FAISS.from_documents(docs, embeddings, normalize_L2=True)
    save_faiss_index(new_index)

    return {"deleted": True}
