import os
import json
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

MEMORIES_PATH = "backend/data/memories.json"
FAISS_PATH = "backend/memory/faiss_index"
os.makedirs("backend/memory", exist_ok=True)
os.makedirs("backend/data", exist_ok=True)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small", openai_api_key=SecretStr(OPENAI_API_KEY)
)

# -------------------------------------------------
# JSON Utilities
# -------------------------------------------------
def load_memories() -> List[str]:
    """Safely load memories from JSON file."""
    try:
        if not os.path.exists(MEMORIES_PATH):
            with open(MEMORIES_PATH, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return []

        with open(MEMORIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data if isinstance(x, str)]
            return []
    except Exception as e:
        print(f"[WARN] load_memories failed: {e}")
        return []


def save_memories(memories: List[str]):
    """Safely overwrite memories.json."""
    try:
        tmp = MEMORIES_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        os.replace(tmp, MEMORIES_PATH)
    except Exception as e:
        print(f"[WARN] save_memories failed: {e}")


def append_memory(text: str):
    """Append memory to JSON (avoid duplicates)."""
    text = text.strip()
    if not text:
        return
    memories = load_memories()
    if text not in memories:
        memories.append(text)
        save_memories(memories)

# -------------------------------------------------
# FAISS Index Utilities
# -------------------------------------------------
def get_or_create_faiss_index() -> FAISS:
    """Load or create FAISS index for factual memories."""
    if os.path.exists(FAISS_PATH):
        return FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    # Create empty index (no dummy 'Init')
    return FAISS.from_texts(["init"], embeddings, normalize_L2=True)


def save_faiss_index(index: FAISS):
    """Persist FAISS index to disk."""
    os.makedirs(FAISS_PATH, exist_ok=True)
    # Clean out 'init' entries if somehow exist
    try:
        store = getattr(index.docstore, "_dict", {})
        for k, v in list(store.items()):
            if hasattr(v, "page_content") and str(v.page_content).strip().lower() == "init":
                del store[k]
    except Exception:
        pass
    index.save_local(FAISS_PATH)


def _extract_memory_texts_from_faiss_index(index) -> List[str]:
    """Extract only memory texts from FAISS."""
    texts = []
    try:
        store = getattr(index.docstore, "_dict", {})
        for v in store.values():
            if hasattr(v, "page_content"):
                t = v.page_content
            elif isinstance(v, dict):
                t = v.get("page_content") or v.get("content") or v.get("text")
            else:
                t = None
            if isinstance(t, str) and t.strip():
                texts.append(t.strip())
    except Exception:
        pass
    # deduplicate preserving order
    return list(dict.fromkeys(texts))

# -------------------------------------------------
# CRUD Operations
# -------------------------------------------------
def add_memory(text: str, duplicate_threshold: float = 0.9):
    """
    Add a memory (fact) to FAISS index and JSON file.
    """
    text = text.strip()
    if not text:
        return {"added": 0, "reason": "Empty text"}

    index = get_or_create_faiss_index()

    # Check duplicates
    try:
        existing = index.similarity_search_with_score(text, k=1)
        if existing:
            _, score = existing[0]
            if score < (1 - duplicate_threshold):
                return {"added": 0, "reason": "Duplicate detected"}
    except Exception:
        pass

    # Add new document
    doc = Document(page_content=text)
    index.add_documents([doc])
    save_faiss_index(index)

    append_memory(text)
    return {"added": 1, "text": text}


def query_memory(query: str, threshold: float = 0.5):
    """Search through FAISS memories with semantic and keyword logic."""
    results = []
    if not os.path.exists(FAISS_PATH):
        return []

    index = get_or_create_faiss_index()
    try:
        docs_and_scores = index.similarity_search_with_score(query, k=10)
        for doc, dist in docs_and_scores:
            sim = 1 - dist
            if sim >= threshold:
                results.append({"content": doc.page_content, "score": sim})
    except Exception:
        pass

    # Keyword-based fallback
    all_texts = _extract_texts_from_faiss_index(index)
    for text in all_texts:
        if any(word.lower() in text.lower() for word in query.split()):
            results.append({"content": text, "score": 0.9})

    # Deduplicate + sort
    seen, unique = set(), []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["content"] not in seen:
            seen.add(r["content"])
            unique.append(r)
    return unique


def list_memories() -> Dict[str, List[str]]:
    """List all stored memories."""
    index = get_or_create_faiss_index()
    return {"facts": _extract_memory_texts_from_faiss_index(index)}


def edit_memory(old_text: str, new_text: str, duplicate_threshold: float = 0.9):
    """Edit an existing memory."""
    old_text, new_text = old_text.strip(), new_text.strip()
    if not new_text:
        return {"edited": False, "reason": "Empty new text"}

    index = get_or_create_faiss_index()
    all_texts = _extract_memory_texts_from_faiss_index(index)

    if old_text not in all_texts:
        return {"edited": False, "reason": "Memory not found"}

    # Check duplicates (excluding old_text)
    try:
        existing = index.similarity_search_with_score(new_text, k=1)
        if existing:
            doc, score = existing[0]
            if getattr(doc, "page_content", None) != old_text and score < (1 - duplicate_threshold):
                return {"edited": False, "reason": "Duplicate detected"}
    except Exception:
        pass

    # Rebuild index without old text
    filtered_texts = [t for t in all_texts if t != old_text] + [new_text]
    docs = [Document(page_content=t) for t in filtered_texts]
    new_index = FAISS.from_documents(docs, embeddings, normalize_L2=True)
    save_faiss_index(new_index)

    # Update JSON
    try:
        mems = load_memories()
        mems = [m for m in mems if m != old_text]
        mems.append(new_text)
        save_memories(mems)
    except Exception as e:
        print(e)

    return {"edited": True, "text": new_text}


def delete_memory(old_text: str):
    """Delete a memory text from FAISS and JSON."""
    old_text = old_text.strip()
    index = get_or_create_faiss_index()
    all_texts = _extract_memory_texts_from_faiss_index(index)

    if old_text not in all_texts:
        return {"deleted": False, "reason": "Memory not found"}

    # Rebuild FAISS index without old text
    filtered_texts = [t for t in all_texts if t != old_text]
    docs = [Document(page_content=t) for t in filtered_texts]
    new_index = FAISS.from_documents(docs, embeddings, normalize_L2=True)
    save_faiss_index(new_index)

    # Update JSON
    try:
        mems = load_memories()
        mems = [m for m in mems if m != old_text]
        save_memories(mems)
    except Exception as e:
        print(e)

    return {"deleted": True}


def reindex_memories():
    """Rebuild FAISS index from the memories.json file."""
    raw_memories = load_memories()
    if not raw_memories:
        return {"reindexed": False, "reason": "No stored memories found"}

    docs = [Document(page_content=m) for m in raw_memories]
    new_index = FAISS.from_documents(docs, embeddings, normalize_L2=True)
    save_faiss_index(new_index)

    return {"reindexed": True, "memories": len(raw_memories)}
