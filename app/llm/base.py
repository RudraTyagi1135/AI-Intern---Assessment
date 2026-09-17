from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        pass


class LLMError(Exception):
    pass


class LLMUnavailableError(LLMError):
    pass