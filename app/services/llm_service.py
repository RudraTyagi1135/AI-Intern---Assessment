import logging
from typing import Optional
from app.llm.base import LLMProvider, LLMError, LLMUnavailableError
from app.llm.ollama import OllamaProvider
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt, parse_llm_response
from app.query.schemas import StructuredQuery
from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or self._create_default_provider()

    def _create_default_provider(self) -> LLMProvider:
        settings = get_settings()
        if settings.llm_provider.lower() == "ollama":
            return OllamaProvider()
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    def parse_question(self, question: str) -> StructuredQuery:
        if not self.provider.is_available():
            raise LLMUnavailableError(
                f"LLM provider not available. "
                f"For Ollama, ensure it's running and run: ollama pull {get_settings().ollama_model}"
            )

        prompt = build_user_prompt(question)
        try:
            response = self.provider.generate(prompt, SYSTEM_PROMPT)
            logger.debug(f"LLM response: {response[:200]}...")
            return parse_llm_response(response)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse question: {e}")
            raise LLMError(f"Failed to understand question: {e}")

    def get_status(self) -> dict:
        return {
            "provider": self.provider.get_model_info(),
            "available": self.provider.is_available(),
        }