import json
from . import register_tool
from .base import BaseTool
from backend.memory import query_memory
from backend.docs import query_docs


@register_tool
class RetrievalTool(BaseTool):
    name = "retrieval"
    description = "Retrieve relevant information from stored memories and uploaded documents."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to look up."},
            "top_k": {
                "type": "integer",
                "description": "Number of most relevant results to return.",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def run(self, query: str, top_k: int = 5) -> str:
        """Combine memory and doc retrieval results."""
        try:
            memory_results = query_memory(query, top_k)
        except Exception as e:
            memory_results = []
            print("[RetrievalTool] Memory query failed:", e)

        try:
            doc_results = query_docs(query, top_k)
        except Exception as e:
            doc_results = []
            print("[RetrievalTool] Doc query failed:", e)

        combined = memory_results + doc_results
        if not combined:
            return "No relevant information found."
        return json.dumps(combined[:top_k], ensure_ascii=False, indent=2)
