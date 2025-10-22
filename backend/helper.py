def _extract_texts_from_faiss_index(index) -> list[dict]:
    """
    Extract readable text contents and metadata from a LangChain FAISS index.
    """
    items = []

    try:
        ds = getattr(index, "docstore", None)
        if ds:
            store = getattr(ds, "_dict", getattr(ds, "docs", {}))
            for key, v in store.items():
                # Handle Document objects (LangChain type)
                if hasattr(v, "page_content"):
                    items.append({
                        "content": v.page_content,
                        "metadata": getattr(v, "metadata", {})
                    })
                elif isinstance(v, dict):
                    content = v.get("page_content") or v.get("text") or v.get("content")
                    metadata = v.get("metadata", {})
                    if content:
                        items.append({"content": content, "metadata": metadata})

        # Handle index_to_docstore_id mapping if present
        mapping = getattr(index, "index_to_docstore_id", None)
        if mapping:
            for doc_id in mapping.values():
                try:
                    doc = index.docstore[doc_id]
                    if hasattr(doc, "page_content"):
                        items.append({
                            "content": doc.page_content,
                            "metadata": getattr(doc, "metadata", {})
                        })
                    elif isinstance(doc, dict):
                        content = doc.get("page_content") or doc.get("text")
                        metadata = doc.get("metadata", {})
                        if content:
                            items.append({"content": content, "metadata": metadata})
                except Exception:
                    continue

    except Exception:
        pass

    # Deduplicate by content
    seen = set()
    unique = []
    for item in items:
        c = item["content"]
        if c not in seen:
            unique.append(item)
            seen.add(c)

    return unique