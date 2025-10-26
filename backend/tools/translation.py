import os
from dotenv import load_dotenv
from . import register_tool
from .base import BaseTool

load_dotenv()

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

try:
    from googletrans import Translator
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


@register_tool
class TranslationTool(BaseTool):
    name = "translate"
    description = "Translate text between languages using DeepL (preferred) or Google Translate fallback."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate."},
            "target_lang": {"type": "string", "description": "Target language code, e.g. 'FR', 'ES', 'DE'."},
        },
        "required": ["text", "target_lang"],
    }

    def run(self, text: str, target_lang: str) -> str:
        api_key = os.getenv("DEEPL_API_KEY")
        if DEEPL_AVAILABLE and api_key:
            try:
                translator = deepl.Translator(api_key)
                result = translator.translate_text(text, target_lang=target_lang.upper())
                return result.text
            except Exception as e:
                return f"DeepL translation failed: {e}"

        elif GOOGLE_AVAILABLE:
            try:
                translator = Translator()
                result = translator.translate(text, dest=target_lang.lower())
                return result.text
            except Exception as e:
                return f"Google Translate failed: {e}"

        return "No translation backend available. Install `deepl` or `googletrans`."
