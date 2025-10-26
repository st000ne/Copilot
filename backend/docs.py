import json
import os
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.llm_client import llm, embeddings
from langchain.schema import Document, HumanMessage
from backend.file_utils import extract_text_from_file

# -------------------------------------------------
# Configuration
# -------------------------------------------------
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

DOCS_INDEX_PATH = "backend/memory/faiss_docs_index"
DOCS_DIR = "backend/data/docs"

# -------------------------------------------------
# Index Utilities
# -------------------------------------------------
def get_or_create_docs_index() -> FAISS:
    """Load FAISS docs index or create an empty one."""
    if os.path.exists(DOCS_INDEX_PATH):
        return FAISS.load_local(
            DOCS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

    # Create an empty FAISS index (no 'init' dummy doc)
    return FAISS.from_texts(["init"], embeddings)


def save_docs_index(index: FAISS):
    """Safely persist the FAISS docs index to disk, removing 'init' dummy docs."""
    try:
        ds = getattr(index, "docstore", None)
        if ds:
            store = getattr(ds, "_dict", getattr(ds, "docs", {}))
            # Identify and remove 'init' docs
            keys_to_delete = []
            for k, v in list(store.items()):
                content = getattr(v, "page_content", None)
                if isinstance(content, str) and content.strip().lower() == "init":
                    keys_to_delete.append(k)
            for k in keys_to_delete:
                try:
                    del store[k]
                except Exception:
                    pass

        # Save cleaned index
        os.makedirs(os.path.dirname(DOCS_INDEX_PATH), exist_ok=True)
        index.save_local(DOCS_INDEX_PATH)
    except Exception as e:
        print(f"⚠️ Warning: Failed to clean 'init' entries before saving docs index: {e}")


def _extract_docs_from_faiss_index(index) -> list[dict]:
    """Extract docs with metadata for the Docs tab."""
    items = []
    try:
        store = getattr(index.docstore, "_dict", {})
        for v in store.values():
            if hasattr(v, "page_content"):
                items.append({
                    "content": v.page_content,
                    "metadata": getattr(v, "metadata", {})
                })
            elif isinstance(v, dict):
                c = v.get("page_content") or v.get("content") or v.get("text")
                if c:
                    items.append({
                        "content": c,
                        "metadata": v.get("metadata", {})
                    })
    except Exception:
        pass

    # Remove 'init' placeholder if any
    cleaned = [
        it for it in items
        if isinstance(it.get("content"), str) and it["content"].strip().lower() != "init"
    ]
    return cleaned


# -------------------------------------------------
# CRUD Operations
# -------------------------------------------------
def add_document(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    duplicate_threshold: float = 0.9,
    base_name: Optional[str] = None,
    use_outline: bool = True,
):
    """
    Add a long document text to the FAISS docs index.
    Optionally uses an LLM to segment the text into coherent sections before chunking.
    """

    text = text.strip()
    if not text:
        return {"added": 0, "reason": "Empty text"}

    index = get_or_create_docs_index()
    sections = [{"title": "Full Document", "text": text}]

    if use_outline and len(text) > 5000:
        try:
            prompt = (
                "You are an expert document parser. Split the following text into meaningful, coherent sections. "
                "Each section should represent a logical unit of the document (e.g., a heading, topic, or paragraph group). "
                "Return a valid JSON list of objects, each with 'title' and 'text' keys.\n\n"
                "If the document has natural headings or numbered sections, use those titles.\n\n"
                "Don't summarize. Keep original text as much as possible.\n\n"
                f"Document:\n{text[:15000]}\n\n"  # cut off to avoid overloading the prompt
                "Return only valid JSON. Example output:\n"
                "[{\"title\": \"Introduction\", \"text\": \"...\"}, {\"title\": \"Method\", \"text\": \"...\"}]"
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            start, end = raw.find("["), raw.rfind("]") + 1
            if start != -1 and end != -1:
                raw = raw[start:end]
            parsed = json.loads(raw)
            if isinstance(parsed, list) and all(isinstance(s, dict) for s in parsed):
                sections = parsed
        except Exception as e:
            print(f"[Outline Warning] Failed to generate sections: {e}")
            paragraphs = re.split(r"\n{2,}", text)
            sections = [
                {"title": f"Section {i+1}", "text": p.strip()}
                for i, p in enumerate(paragraphs) if p.strip()
            ]

    added = 0
    total_chunks = 0
    new_docs = []

    for section in sections:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        chunks = splitter.split_text(section["text"])
        total_chunks += len(chunks)

        for i, chunk in enumerate(chunks):
            existing = index.similarity_search_with_score(chunk, k=1)
            if existing:
                _, score = existing[0]
                similarity = 1 - score / 2
                if similarity >= duplicate_threshold:
                    continue

            metadata = {
                "section_title": section["title"],
                "chunk_index": i + 1,
            }
            if base_name:
                metadata["filename"] = base_name
                metadata["source"] = f"{base_name}_{section['title']}_chunk{i+1}"

            new_docs.append(Document(page_content=chunk, metadata=metadata))
            added += 1

    if new_docs:
        index.add_documents(new_docs)
        save_docs_index(index)

    return {
        "added": added,
        "chunks": total_chunks,
        "sections": len(sections),
    }



def query_docs(query: str, threshold: float = 0.75, k: int = 5) -> List[Dict]:
    """Query stored documents by semantic similarity."""
    index = get_or_create_docs_index()
    docs_with_scores = index.similarity_search_with_score(query, k=k)

    results = []
    for doc, dist in docs_with_scores:
        sim = 1 - dist / 2
        if sim >= threshold:
            results.append({"content": doc.page_content, "score": sim})
    return results


def list_documents() -> List[Dict]:
    """List all stored document chunks with filename and text."""
    index = get_or_create_docs_index()
    texts = _extract_docs_from_faiss_index(index)

    results = []
    for t in texts:
        filename = (
            t.get("metadata", {}).get("filename")
            if isinstance(t, dict)
            else "Unknown"
        ) or "Unknown"

        if isinstance(t, dict):
            content = (
                t.get("page_content")
                or t.get("text")
                or t.get("content")
                or str(t)
            )
        else:
            content = str(t)

        results.append({"filename": filename, "content": content})
    return results


def edit_document(old_text: str, new_text: str):
    """Replace a document chunk by text match."""
    index = get_or_create_docs_index()
    all_texts = _extract_docs_from_faiss_index(index)
    all_contents = [t["content"] for t in all_texts]

    if old_text not in all_contents:
        return {"edited": False, "reason": "Chunk not found"}

    new_docs = []
    for t in all_texts:
        content = t["content"]
        metadata = t.get("metadata", {})
        if content == old_text:
            new_docs.append(Document(page_content=new_text, metadata=metadata))
        else:
            new_docs.append(Document(page_content=content, metadata=metadata))

    new_index = FAISS.from_documents(new_docs, embeddings, normalize_L2=True)
    save_docs_index(new_index)
    return {"edited": True}


def delete_document_by_filename(filename: str):
    """
    Delete all chunks belonging to a given filename and remove files from disk.
    """
    index = get_or_create_docs_index()
    store = getattr(index.docstore, "_dict", {})
    all_docs = [
        Document(page_content=v.page_content, metadata=v.metadata)
        for v in store.values()
        if hasattr(v, "page_content")
    ]

    # Remove chunks belonging to this filename
    filtered_docs = [
        d for d in all_docs if d.metadata.get("filename") != filename
    ]

    new_index = FAISS.from_documents(filtered_docs, embeddings, normalize_L2=True)
    save_docs_index(new_index)

    # Also remove any matching files from backend/data/docs
    try:
        if os.path.isdir(DOCS_DIR):
            for f in os.listdir(DOCS_DIR):
                fpath = os.path.join(DOCS_DIR, f)
                if not os.path.isfile(fpath):
                    continue
                stem = os.path.splitext(f)[0]
                if stem == filename:
                    try:
                        os.remove(fpath)
                        print(f"🗑️ Deleted file: {fpath}")
                    except Exception as e:
                        print(f"⚠️ Failed to delete {fpath}: {e}")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    return {"deleted": True, "filename": filename}


def reindex_docs():
    """
    Rebuild FAISS docs index from all files in backend/data/docs.
    """
    if not os.path.exists(DOCS_DIR):
        return {"reindexed": False, "reason": "Docs directory not found"}

    all_files = [
        f for f in os.listdir(DOCS_DIR)
        if os.path.isfile(os.path.join(DOCS_DIR, f))
    ]

    if not all_files:
        return {"reindexed": False, "reason": "No files to index"}

    all_texts = []
    for file in all_files:
        try:
            file_path = os.path.join(DOCS_DIR, file)
            text = extract_text_from_file(file_path)
            if text.strip():
                all_texts.append((os.path.splitext(file)[0], text))
        except Exception as e:
            print(f"[WARN] Skipped {file}: {e}")

    if not all_texts:
        return {"reindexed": False, "reason": "No valid text extracted"}

    # Build new FAISS index
    all_docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    for base_name, text in all_texts:
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            metadata = {"filename": base_name, "source": f"{base_name}_chunk{i+1}"}
            all_docs.append(Document(page_content=chunk, metadata=metadata))

    new_index = FAISS.from_documents(all_docs, embeddings)
    save_docs_index(new_index)

    return {
        "reindexed": True,
        "files_indexed": len(all_texts),
        "chunks": len(all_docs),
    }


def generate_outline_sections(text: str, max_section_len: int = 5000) -> list[dict]:
    """
    Use the LLM to create a structured outline of the document.
    Returns a list of {title, text} objects representing logical sections.
    If the LLM fails or text is too small, returns a single section with the full text.
    """
    text = text.strip()
    if not text:
        return []

    # Skip LLM outlining if the text is short enough
    if len(text) <= max_section_len:
        return [{"title": "Full Document", "text": text}]

    prompt = (
        "You are an expert document parser. Split the following text into meaningful, coherent sections. "
        "Each section should represent a logical unit of the document (e.g., a heading, topic, or paragraph group). "
        "Return a valid JSON list of objects, each with 'title' and 'text' keys.\n\n"
        "If the document has natural headings or numbered sections, use those titles.\n\n"
        f"Document:\n{text[:15000]}\n\n"  # cut off to avoid overloading the prompt
        "Return only valid JSON. Example output:\n"
        "[{\"title\": \"Introduction\", \"text\": \"...\"}, {\"title\": \"Method\", \"text\": \"...\"}]"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Try to find JSON in case model adds text before/after
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end != -1:
            raw = raw[start:end]

        sections = json.loads(raw)
        # Basic sanity check
        if not isinstance(sections, list) or not all(isinstance(s, dict) for s in sections):
            raise ValueError("Invalid JSON structure from LLM")
        return sections

    except Exception as e:
        print(f"[Outline Warning] Failed to generate structured outline: {e}")
        # Fallback: rough chunking if LLM fails
        import re
        paragraphs = re.split(r"\n{2,}", text)
        return [
            {"title": f"Section {i+1}", "text": p.strip()}
            for i, p in enumerate(paragraphs) if p.strip()
        ]
