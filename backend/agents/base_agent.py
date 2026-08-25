import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
try:
    from backend.services.llm_service import LLMService, llm_service
except ImportError:
    from services.llm_service import LLMService, llm_service

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract Base Class for all Academic Writing Coach agents."""

    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        self.llm_service = llm_service_instance or llm_service
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run agent logic on input data and return result dict."""
        pass
