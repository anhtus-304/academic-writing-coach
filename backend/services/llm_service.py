import json
import logging
import httpx
from typing import Type, TypeVar, Any, Optional
from pydantic import BaseModel
try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """High-performance wrapper for OpenRouter API interactions with DeepSeek."""

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

    async def generate_structured_output_with_usage(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.3,
        timeout: Optional[float] = None,
    ) -> tuple[T, dict[str, Any]]:
        """Generates structured output and returns (parsed_result, usage_dict)."""
        selected_model = model or self.default_model or settings.DEFAULT_MODEL
        api_key = self.api_key or settings.OPENROUTER_API_KEY
        base_url = (self.base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        timeout_val = timeout if timeout is not None else getattr(settings, "LLM_TIMEOUT_SECONDS", 1.0)

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")

        json_schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)

        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            f"BẠN BẮT BUỘC PHẢI TRẢ VỀ DỮ LIỆU DƯỚI ĐỊNH DẠNG JSON HỢP LỆ (VALID JSON) TUÂN THỦ CHÍNH XÁC SCHEMA SAU:\n"
            f"```json\n{json_schema_str}\n```\n\n"
            "QUY TẮC:\n"
            "- Chỉ trả về duy nhất chuỗi JSON hợp lệ (không kèm bất kỳ lời chào, ghi chú hay ký tự thừa nào ngoài JSON).\n"
            "- Cấu trúc đầy đủ các trường yêu cầu trong schema, tiếng Việt chuẩn học thuật."
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://academic-writing-coach.local",
            "X-Title": "Academic Writing Coach Agent",
            "Content-Type": "application/json",
        }

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.info(f"Calling OpenRouter model '{selected_model}' (timeout={timeout_val}s)...")
        
        async with httpx.AsyncClient(timeout=timeout_val) as http_client:
            response = await http_client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            res_data = response.json()
            raw_content = res_data["choices"][0]["message"]["content"]
            usage = res_data.get("usage", {})
            parsed = self._clean_and_parse_json(raw_content, schema)
            return parsed, usage

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.3,
        timeout: Optional[float] = None,
    ) -> T:
        """Generates structured output validated against a Pydantic schema using OpenRouter."""
        result, _ = await self.generate_structured_output_with_usage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            model=model,
            temperature=temperature,
            timeout=timeout,
        )
        return result


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
            logger.error(f"Failed to parse JSON string: {cleaned[:300]}...")
            raise ValueError(f"Could not parse valid {schema.__name__} from LLM output: {err}")


# Single shared instance for convenience
llm_service = LLMService()
