import json
import logging
from typing import Type, TypeVar, Any, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Wrapper for OpenRouter API interactions (DeepSeek V4/Flash/Pro/R1, etc.)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        temperature: float = 0.3,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.default_model = default_model or settings.DEFAULT_MODEL
        self.temperature = temperature

    def get_client(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = 4000,
    ) -> ChatOpenAI:
        """Returns a configured ChatOpenAI instance pointing to OpenRouter."""
        selected_model = model or self.default_model or settings.DEFAULT_MODEL
        temp = temperature if temperature is not None else self.temperature
        api_key = self.api_key or settings.OPENROUTER_API_KEY
        base_url = self.base_url or settings.OPENROUTER_BASE_URL

        if not api_key:
            logger.warning("OPENROUTER_API_KEY is empty! OpenRouter will return 401 Unauthorized.")

        extra_headers = {
            "HTTP-Referer": "https://academic-writing-coach.local",
            "X-Title": "Academic Writing Coach Agent",
        }

        return ChatOpenAI(
            model_name=selected_model,
            openai_api_key=api_key if api_key else "placeholder_key",
            openai_api_base=base_url,
            temperature=temp,
            max_tokens=max_tokens,
            default_headers=extra_headers,
        )


    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generates structured output validated against a Pydantic schema using OpenRouter."""
        client = self.get_client(model=model, temperature=temperature)
        
        # Try native structured output first
        try:
            structured_llm = client.with_structured_output(schema)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            result = await structured_llm.ainvoke(messages)
            if isinstance(result, schema):
                return result
            elif isinstance(result, dict):
                return schema.model_validate(result)
        except Exception as e:
            logger.warning(f"Native structured output failed, falling back to manual JSON parsing: {e}")

        # Fallback to direct prompt instruction & manual JSON parsing
        json_instruction_system = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Return ONLY a valid JSON object matching the requested schema. "
            "Do not include any Markdown code block wrappers like ```json ... ``` or commentary outside the JSON."
        )
        
        messages = [
            SystemMessage(content=json_instruction_system),
            HumanMessage(content=user_prompt),
        ]
        
        response = await client.ainvoke(messages)
        content = response.content
        if isinstance(content, list):
            content = "".join([str(c) for c in content])
        
        return self._clean_and_parse_json(content, schema)

    def _clean_and_parse_json(self, raw_text: str, schema: Type[T]) -> T:
        """Helper to extract JSON block from model response and validate against schema."""
        cleaned = raw_text.strip()
        
        # Remove Markdown code fence if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()

        # Find first '{' and last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1]

        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except Exception as err:
            logger.error(f"Failed to parse JSON string: {cleaned[:200]}...")
            raise ValueError(f"Could not parse valid {schema.__name__} from LLM output: {err}")


# Single shared instance for convenience
llm_service = LLMService()
