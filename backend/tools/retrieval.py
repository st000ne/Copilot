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
            "query": {"type": "string", "description": "Search query to look up."},
            "top_k": {
                "type": "integer",
                "description": "Number of top relevant results to return.",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def run(self, query: str, top_k: int = 5) -> str:
        """Fetch top relevant items from both memory and docs."""
        memory_results = []
        doc_results = []

        try:
            memory_results = query_memory(query)
        except Exception as e:
            print("[RetrievalTool] Memory query failed:", e)

        try:
            doc_results = query_docs(query, k=top_k)
        except Exception as e:
            print("[RetrievalTool] Doc query failed:", e)

        combined = memory_results + doc_results
        if not combined:
            return "No relevant results found."

        combined = sorted(combined, key=lambda x: x["score"], reverse=True)[:top_k]

        # Compact text format, better for LLM consumption
        formatted = "\n\n".join(
            f"[{i+1}] (score: {r['score']:.2f}) {r['content'][:800]}"
            for i, r in enumerate(combined)
        )
        return formatted
