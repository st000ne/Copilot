import spacy
from . import register_tool
from .base import BaseTool

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

@register_tool
class KeywordTool(BaseTool):
    name = "extract_keywords"
    description = "Extract keywords from text using spaCy noun and proper noun extraction."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to analyze."},
            "limit": {"type": "integer", "description": "Maximum number of keywords.", "default": 10},
        },
        "required": ["text"],
    }

    def run(self, text: str, limit: int = 10) -> list:
        doc = nlp(text)
        keywords = []
        for token in doc:
            if token.pos_ in {"NOUN", "PROPN"} and len(token.text) > 2:
                keywords.append(token.lemma_.lower())

        # Deduplicate + sort by frequency
        keywords = list(dict.fromkeys(keywords))
        return keywords[:limit]
