import requests
import json
import logging
from typing import Optional
from app.llm.base import LLMProvider, LLMError, LLMUnavailableError
from app.config import get_settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self._available_cache: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available_cache is not None:
            return self._available_cache

        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                self._available_cache = any(self.model in name for name in model_names)
                if not self._available_cache:
                    logger.warning(f"Model '{self.model}' not found in Ollama. Available: {model_names}")
                return self._available_cache
        except requests.RequestException as e:
            logger.warning(f"Ollama not available at {self.base_url}: {e}")
            self._available_cache = False

        return False

    def get_model_info(self) -> dict:
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "available": self.is_available(),
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise LLMUnavailableError(
                f"Ollama is not available or model '{self.model}' not found. "
                f"Please ensure Ollama is running at {self.base_url} and run: "
                f"ollama pull {self.model}"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except requests.Timeout:
            raise LLMError(f"Ollama request timed out after {self.timeout}s")
        except requests.RequestException as e:
            raise LLMError(f"Ollama request failed: {e}")
        except json.JSONDecodeError:
            raise LLMError("Invalid JSON response from Ollama")