def _extract_texts_from_faiss_index(index) -> list[str]:
    """
	Extract readable text contents from a LangChain FAISS index,
	handling both Document objects and older dict-based stores.
	"""
    texts = []

    try:
        ds = getattr(index, "docstore", None)
        if ds:
            store = getattr(ds, "_dict", getattr(ds, "docs", {}))
            for key, v in store.items():
                if hasattr(v, "page_content"):
                    texts.append(v.page_content)
                elif isinstance(v, dict):
                    # Some versions store docs as dicts with nested content
                    if "page_content" in v:
                        texts.append(v["page_content"])
                    elif "text" in v:
                        texts.append(v["text"])
                    elif "content" in v:
                        texts.append(v["content"])
                else:
                    # As a last resort, avoid appending IDs or raw UUID strings
                    s = str(v)
                    if len(s) > 8 and not all(c.isalnum() or c in "-_" for c in s):
                        texts.append(s)

        # Handle index_to_docstore_id mapping if present
        mapping = getattr(index, "index_to_docstore_id", None)
        if mapping:
            for doc_id in mapping.values():
                try:
                    doc = index.docstore[doc_id]
                    if hasattr(doc, "page_content"):
                        texts.append(doc.page_content)
                    elif isinstance(doc, dict):
                        if "page_content" in doc:
                            texts.append(doc["page_content"])
                        elif "text" in doc:
                            texts.append(doc["text"])
                except Exception:
                    continue

    except Exception:
        pass

    # Deduplicate and ensure no IDs or empty strings
    return list(dict.fromkeys([t for t in texts if t and not t.strip().isdigit()]))
