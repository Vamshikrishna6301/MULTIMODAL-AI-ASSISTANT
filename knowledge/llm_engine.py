import requests
import re
from core.response_model import UnifiedResponse


class LLMEngine:
    """
    Production LLM Engine (TinyLlama via Ollama)
    Used for reasoning and complex queries only.
    Strictly formatted, no assistant fluff.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL_NAME = "tinyllama"
    TIMEOUT = 40

    def __init__(self, context_memory=None):
        self.context_memory = context_memory

    def handle(self, decision: dict) -> UnifiedResponse:

        query = decision.get("target")

        if not query:
            return UnifiedResponse.error_response(
                category="knowledge",
                spoken_message="I did not receive a question.",
                error_code="NO_QUERY"
            )

        try:
            response = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.MODEL_NAME,
                    "prompt": self._build_prompt(query),
                    "stream": False,
                    "options": {
                        "num_predict": 80,
                        "temperature": 0.2,
                        "num_ctx": 512,
                        "num_thread": 8,
                        "top_p": 0.9
                    }
                },
                timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                return UnifiedResponse.error_response(
                    category="knowledge",
                    spoken_message="Local AI model is not responding.",
                    error_code="LLM_CONNECTION_ERROR"
                )

            data = response.json()
            raw_answer = data.get("response", "").strip()

            cleaned = self._clean_response(raw_answer)

            return UnifiedResponse.success_response(
                category="knowledge",
                spoken_message=cleaned
            )

        except Exception:
            return UnifiedResponse.error_response(
                category="knowledge",
                spoken_message="Local AI model encountered an error.",
                error_code="LLM_EXCEPTION"
            )

    # -----------------------------------------------------

    def _build_prompt(self, query: str):

        context_block = ""
        if self.context_memory:
            context_str = self.context_memory.get_context_prompt(count=3)
            if context_str:
                context_block = f"\nConversation context:\n{context_str}\n"

        return f"""
You are a concise factual assistant.

Answer directly.
Do not say:
- "Sure"
- "Here is"
- "Here’s"
- "In this case"
- "The answer is"
- Any conversational filler

Maximum 2 short sentences.
No paragraphs.
No bullet points.
Use conversation context when the user is asking a follow-up.

{context_block}
Answer the question:
{query}
Answer:
"""
    

    # -----------------------------------------------------

    def _clean_response(self, text: str) -> str:

        if not text:
            return "I could not generate an answer."

        # Remove common assistant fluff
        fluff_patterns = [
            r"^sure[,!\s]*",
            r"^here( is|'s)[,!\s]*",
            r"^in this case[,!\s]*",
            r"^the answer is[,:\s]*",
        ]

        text = text.strip()

        for pattern in fluff_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Hard limit to 2 sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) > 2:
            text = " ".join(sentences[:2])

        return text.strip()
