import os
import json

MEMORY_PATH = "backend/data/memories.json"


def load_memories() -> list[str]:
    """Load all raw factual memories from disk."""
    if not os.path.exists(MEMORY_PATH):
        return []
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memories(memories: list[str]):
    """Persist all factual memories to disk."""
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def append_memory(new_text: str):
    """Append a new memory to the JSON store."""
    memories = load_memories()
    memories.append(new_text)
    save_memories(memories)
