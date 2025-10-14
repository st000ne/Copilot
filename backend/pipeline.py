# backend/pipeline.py
import os
import re
import numpy as np
import tiktoken
from dotenv import load_dotenv
from pathlib import Path
from pydantic import SecretStr
from difflib import SequenceMatcher

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Direct access helpers for FAISS-based storage
from backend.memory import query_memory, get_or_create_faiss_index
from backend.docs import query_docs, get_or_create_docs_index
from backend.embeddings_cache import get_or_create_embedding
from backend.helper import _extract_texts_from_faiss_index

# --- Load environment ---
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable. See .env.example")

# --- Config ---
MODEL_NAME = "gpt-4o-mini"
MAX_CONTEXT_TOKENS = 3000
SUMMARIZE_AFTER_MESSAGES = 20
SYSTEM_PROMPT = (
    "You are a helpful, intelligent assistant that remembers context "
    "and answers clearly, concisely, and helpfully."
)

# --- Initialize models ---
llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.7, openai_api_key=SecretStr(OPENAI_API_KEY))
summarizer = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3, openai_api_key=SecretStr(OPENAI_API_KEY))
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=SecretStr(OPENAI_API_KEY))

# --- Helpers ---
def num_tokens_from_messages(messages, model_name=MODEL_NAME):
    enc = tiktoken.encoding_for_model(model_name)
    text = "".join(m["content"] for m in messages)
    return len(enc.encode(text))


def summarize_messages(messages):
    summary_prompt = (
        "Summarize the following conversation briefly so it can be used as context:\n\n"
        + "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    )
    resp = summarizer.invoke([HumanMessage(content=summary_prompt)])
    return resp.content.strip()


# ---- Keyword search utilities ----
WORD_RE = re.compile(r"\w+")


def simple_keyword_score(text: str, query: str) -> float:
    q_words = set(WORD_RE.findall(query.lower()))
    t_words = set(WORD_RE.findall(text.lower()))
    if not q_words:
        return 0.0
    overlap = q_words & t_words
    return len(overlap) / len(q_words)


def keyword_search_corpus(corpus: list[dict], query: str, top_k: int = 50):
    """Return top_k results by keyword overlap."""
    scored = []
    for item in corpus:
        score = simple_keyword_score(item["content"], query)
        if score > 0:
            scored.append({**item, "keyword_score": float(score)})
    scored.sort(key=lambda x: x["keyword_score"], reverse=True)
    return scored[:top_k]


# --- Hybrid retrieval (semantic + keyword + rerank) ---
def retrieve_context(user_input: str, mem_threshold: float = 0.7, doc_threshold: float = 0.7):
    """Unified retrieval from memory + docs, using semantic + keyword hybrid."""

    # 1) Semantic matches
    mem_sem = query_memory(user_input, threshold=mem_threshold) or []
    doc_sem = query_docs(user_input, threshold=doc_threshold) or []

    mem_sem_items = [{"type": "memory", "content": m["content"], "score": float(m.get("score", 1.0))} for m in mem_sem]
    doc_sem_items = [{"type": "doc", "content": d["content"], "score": float(d.get("score", 1.0))} for d in doc_sem]

    # 2) Keyword scan corpus
    corpus = []

    try:
        mem_index = get_or_create_faiss_index()
        for t in _extract_texts_from_faiss_index(mem_index):
            corpus.append({"type": "memory", "content": t, "score": 0.85})
    except Exception:
        pass

    try:
        docs_index = get_or_create_docs_index()
        for t in _extract_texts_from_faiss_index(docs_index):
            corpus.append({"type": "doc", "content": t, "score": 0.8})
    except Exception:
        pass

    corpus.extend(mem_sem_items)
    corpus.extend(doc_sem_items)

    # 3) Keyword search
    keyword_results = keyword_search_corpus(corpus, user_input, top_k=200)

    # Combine + deduplicate (type, normalized text)
    combined_candidates = {
        (item["type"], item["content"].strip().lower()[:400]): item
        for item in (mem_sem_items + doc_sem_items + keyword_results)
    }
    combined = list(combined_candidates.values())
    if not combined:
        return []

    # 4) Flexible duplicate merge
    unique = []
    for item in combined:
        text = item["content"].strip()
        if not text:
            continue
        is_dup = False
        for u in unique:
            if SequenceMatcher(None, text, u["content"]).ratio() > 0.92:
                if item.get("score", 0) > u.get("score", 0):
                    u.update(item)
                is_dup = True
                break
        if not is_dup:
            unique.append(item)

    # 5) Re-rank using cosine similarity (with cached embeddings)
    try:
        query_emb = np.array(get_or_create_embedding(user_input, embeddings.embed_query))
    except Exception:
        query_emb = None

    rank_scores = []
    for c in unique:
        base_score = float(c.get("score", 0.75))
        if query_emb is not None:
            try:
                chunk_emb = np.array(get_or_create_embedding(c["content"], embeddings.embed_query))
                cosine_sim = float(np.dot(query_emb, chunk_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(chunk_emb) + 1e-12))
            except Exception:
                cosine_sim = 0.0
        else:
            cosine_sim = 0.0

        keyword_boost = float(c.get("keyword_score", 0.0))
        type_weight = 1.08 if c["type"] == "memory" else 1.0
        c["rank_score"] = (0.55 * base_score + 0.35 * cosine_sim + 0.10 * keyword_boost) * type_weight
        rank_scores.append(c["rank_score"])

    if not rank_scores:
        return []

    # 6) Adaptive cutoff
    mean_rank = float(np.mean(rank_scores))
    std_rank = float(np.std(rank_scores))
    adaptive_cutoff = max(0.5, mean_rank - 0.5 * std_rank)

    final = [c for c in unique if c["rank_score"] >= adaptive_cutoff]
    return sorted(final, key=lambda x: x["rank_score"], reverse=True)


# --- Chat orchestration ---
def run_chat(messages: list[dict]):
    """Run chat with hybrid context injection and summarization."""
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Summarize old conversation
    if len(messages) > SUMMARIZE_AFTER_MESSAGES:
        summary_text = summarize_messages(messages[:-10])
        messages = (
            [messages[0], {"role": "system", "content": f"Conversation summary: {summary_text}"}]
            + messages[-10:]
        )

    # Trim token overflow
    while num_tokens_from_messages(messages) > MAX_CONTEXT_TOKENS and len(messages) > 5:
        messages.pop(1)

    # Retrieve hybrid context
    user_last = next((m for m in reversed(messages) if m["role"] == "user"), None)
    context_snippets = retrieve_context(user_last["content"]) if user_last else []

    if context_snippets:
        mem_texts = [c for c in context_snippets if c["type"] == "memory"]
        doc_texts = [c for c in context_snippets if c["type"] == "doc"]

        injected = (
            "You have access to the following relevant context from user memory and reference documents. "
            "Use these facts and snippets to inform your reply (treat facts as reliable when applicable):\n"
        )

        if mem_texts:
            injected += "\n---\nMemories:\n" + "\n".join(
                f"- [Memory] ({m['rank_score']:.3f}) {m['content']}" for m in mem_texts
            )
        if doc_texts:
            injected += "\n---\nReference Docs:\n" + "\n".join(
                f"- [Doc] ({d['rank_score']:.3f}) {d['content']}" for d in doc_texts
            )

        messages.insert(1, {"role": "system", "content": injected})

    # Convert to LangChain message objects
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else
        AIMessage(content=m["content"]) if m["role"] == "assistant" else
        SystemMessage(content=m["content"])
        for m in messages
    ]

    response = llm.invoke(lc_messages)
    return {"role": "assistant", "content": response.content}
