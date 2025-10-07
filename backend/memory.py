import os
from dotenv import load_dotenv
from pydantic import SecretStr

from pathlib import Path

dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable. See .env.example")

import os
import json
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# -----------------------------
# Configuration
# -----------------------------
EMBEDDINGS_PATH = "memory/faiss_index"
NOTES_PATH = "memory/notes.json"
os.makedirs("memory", exist_ok=True)

# OpenAI’s lightweight embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=SecretStr(OPENAI_API_KEY))

# -----------------------------
# FAISS Index Management (Cosine-based)
# -----------------------------
def get_or_create_faiss_index():
    """
    Load an existing cosine-similarity FAISS index, or create a new one.
    """
    if os.path.exists(EMBEDDINGS_PATH):
        return FAISS.load_local(
            EMBEDDINGS_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )
    else:
        # normalize_L2=True makes FAISS use cosine similarity
        return FAISS.from_texts(["Your name is Petro."], embeddings, normalize_L2=True)


def save_faiss_index(index: FAISS):
    index.save_local(EMBEDDINGS_PATH)


# -----------------------------
# Notes Management (Non-embedded)
# -----------------------------
def load_notes() -> list[str]:
    if not os.path.exists(NOTES_PATH):
        return []
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_notes(notes: list[str]):
    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


# -----------------------------
# Memory Management
# -----------------------------
def add_memory(text: str, memory_type: str = "fact"):
    """
    Add a new memory depending on type.
    - 'fact': embedded + stored in FAISS
    - 'note': plain text in JSON file
    """
    if memory_type == "fact":
        index = get_or_create_faiss_index()
        index.add_texts([text])
        save_faiss_index(index)
    elif memory_type == "note":
        notes = load_notes()
        notes.append(text)
        save_notes(notes)
    else:
        raise ValueError(f"Unknown memory_type: {memory_type}")


def query_memory(query: str, threshold: float = 0.75):
    """
    Retrieve both vector-based and note-based memories relevant to a query.
    Uses cosine similarity and a configurable threshold (0–1).
    """
    results = []

    # --- 1. FAISS semantic retrieval ---
    if os.path.exists(EMBEDDINGS_PATH):
        index = get_or_create_faiss_index()
        docs_and_scores = index.similarity_search_with_score(query, k=10)

        for doc, distance in docs_and_scores:
            # FAISS with normalize_L2=True gives cosine *distance* = 1 - similarity
            similarity = 1 - distance
            if similarity >= threshold:
                results.append(
                    {
                        "content": doc.page_content,
                        "source": "fact",
                        "score": float(similarity),
                    }
                )

    # --- 2. Simple keyword-based note matching ---
    for note in load_notes():
        if any(word.lower() in note.lower() for word in query.split()):
            results.append({"content": note, "source": "note", "score": 0.9})

    # --- 3. Sort by score descending & deduplicate ---
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["content"] not in seen:
            unique.append(r)
            seen.add(r["content"])

    return unique