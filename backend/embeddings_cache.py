import json
import os
from hashlib import sha256

CACHE_PATH = "data/embedding_cache.json"

def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)

def get_or_create_embedding(text: str, embed_func) -> list[float]:
    cache = load_cache()
    key = _hash_text(text)
    if key in cache:
        return cache[key]
    embedding = embed_func(text)
    cache[key] = embedding
    save_cache(cache)
    return embedding
