import os
import sys
import json
import yaml
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
try:
    from backend.agents.base_agent import BaseAgent
    from backend.services.llm_service import LLMService, llm_service
    from backend.schemas.outline_schemas import (
        AcademicOutline,
        OutlineGenerationInput,
        OutlineResponse,
        OutlineSection,
        OutlineSubSection,
    )
    from backend.prompts.outline_prompts import (
        OUTLINE_SYSTEM_PROMPT,
        OUTLINE_USER_PROMPT_TEMPLATE,
    )
except ImportError:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService, llm_service
    from schemas.outline_schemas import (
        AcademicOutline,
        OutlineGenerationInput,
        OutlineResponse,
        OutlineSection,
        OutlineSubSection,
    )
    from prompts.outline_prompts import (
        OUTLINE_SYSTEM_PROMPT,
        OUTLINE_USER_PROMPT_TEMPLATE,
    )

logger = logging.getLogger(__name__)


class OutlineAgent(BaseAgent):
    """Agent responsible for generating structured academic outlines."""

    def __init__(
        self,
        llm_service_instance: Optional[LLMService] = None,
        templates_dir: Optional[str] = None,
    ):
        super().__init__(llm_service_instance=llm_service_instance)
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent.parent / "templates"

    def load_template(
        self, template_id_or_doc_type: str
    ) -> Optional[Dict[str, Any]]:
        """Loads a YAML template matching template_id or document_type."""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return None

        # Direct file check (e.g. tieu_luan_default.yaml)
        candidate_paths = [
            self.templates_dir / f"{template_id_or_doc_type}.yaml",
            self.templates_dir / f"{template_id_or_doc_type}_default.yaml",
        ]

        # Scan templates directory for matching id or document_type
        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        continue
                    if (
                        data.get("id") == template_id_or_doc_type
                        or data.get("document_type") == template_id_or_doc_type
                    ):
                        return data
            except Exception as e:
                logger.warning(f"Failed to parse template {yaml_file}: {e}")

        # Try candidate paths directly if scan didn't find match
        for path in candidate_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logger.warning(f"Failed to read template at {path}: {e}")

        return None

    def _build_outline_from_template(
        self,
        topic: str,
        document_type: str,
        field: Optional[str],
        target_length: Optional[str],
        template_data: Optional[Dict[str, Any]],
    ) -> AcademicOutline:
        sections: list[OutlineSection] = []
        if template_data and "sections" in template_data:
            for s in template_data["sections"]:
                subsections = []
                for sub in s.get("subsections", []):
                    subsections.append(
                        OutlineSubSection(
                            title=sub.get("title", "Tiểu mục"),
                            description=sub.get("description", ""),
                            estimated_word_count=500,
                            key_points=[
                                f"Nội dung trọng tâm liên quan đến {topic[:35]}...",
                                "Phân tích và đối chiếu tài liệu học thuật liên quan",
                            ],
                        )
                    )
                sections.append(
                    OutlineSection(
                        section_code=s.get("code", "SEC"),
                        title=s.get("title", "Chương"),
                        description=s.get("description", ""),
                        subsections=subsections,
                    )
                )

        if not sections:
            sections = [
                OutlineSection(
                    section_code="INTRO",
                    title="MỞ ĐẦU",
                    description="Tổng quan và tính cấp thiết",
                    subsections=[
                        OutlineSubSection(
                            title="1. Lý do chọn đề tài",
                            description=f"Tính cấp thiết của nghiên cứu về {topic}",
                            estimated_word_count=400,
                            key_points=["Bối cảnh thực tiễn", "Khoảng trống nghiên cứu"],
                        ),
                        OutlineSubSection(
                            title="2. Mục tiêu nghiên cứu",
                            description="Mục tiêu tổng quát và cụ thể",
                            estimated_word_count=300,
                            key_points=["Mục tiêu lý luận", "Mục tiêu thực tiễn"],
                        ),
                    ],
                ),
                OutlineSection(
                    section_code="CH1",
                    title="CHƯƠNG 1: CƠ SỞ LÝ LUẬN VÀ TỔNG QUAN TÀI LIỆU",
                    description="Khung lý thuyết nền tảng",
                    subsections=[
                        OutlineSubSection(
                            title="1.1. Các khái niệm và định nghĩa cơ bản",
                            description="Lý thuyết nền tảng",
                            estimated_word_count=1000,
                            key_points=["Khái niệm cốt lõi", "Mô hình phân tích"],
                        )
                    ],
                ),
                OutlineSection(
                    section_code="CH2",
                    title="CHƯƠNG 2: THỰC TRẠNG VÀ ĐÁNH GIÁ VẤN ĐỀ",
                    description="Phân tích số liệu và hiện trạng",
                    subsections=[
                        OutlineSubSection(
                            title="2.1. Phân tích thực trạng",
                            description="Đánh giá dữ liệu và khảo sát thực tế",
                            estimated_word_count=1500,
                            key_points=["Dữ liệu thu thập", "Phát hiện chính"],
                        )
                    ],
                ),
                OutlineSection(
                    section_code="CH3",
                    title="CHƯƠNG 3: ĐỀ XUẤT GIẢI PHÁP VÀ KIẾN NGHỊ",
                    description="Các định hướng và giải pháp khả thi",
                    subsections=[
                        OutlineSubSection(
                            title="3.1. Các giải pháp trọng tâm",
                            description="Giải pháp cụ thể cho đề tài",
                            estimated_word_count=1000,
                            key_points=["Giải pháp ngắn hạn", "Giải pháp dài hạn"],
                        )
                    ],
                ),
                OutlineSection(
                    section_code="OUTRO",
                    title="KẾT LUẬN VÀ TÀI LIỆU THAM KHẢO",
                    description="Tổng kết và nguồn trích dẫn",
                    subsections=[
                        OutlineSubSection(
                            title="Kết luận",
                            description="Tổng kết kết quả đạt được",
                            estimated_word_count=400,
                            key_points=["Tóm tắt đóng góp nghiên cứu"],
                        )
                    ],
                ),
            ]

        keywords = [
            topic.split()[0] if topic else "Nghiên cứu",
            field or "Học thuật",
            "Phương pháp phân tích tổng hợp",
        ]

        return AcademicOutline(
            topic=topic,
            document_type=document_type,
            field=field,
            language="vi",
            total_estimated_pages=target_length or "20 trang",
            sections=sections,
            research_methodology_suggestion="Kết hợp phương pháp nghiên cứu định tính (tổng quan tài liệu) và định lượng (số liệu khảo sát).",
            key_academic_keywords=keywords,
            writing_guidelines="Chú ý trích dẫn nguồn học thuật theo chuẩn APA/IEEE, đảm bảo tính mạch lạc và lập luận chặt chẽ.",
        )

    async def generate_outline(
        self,
        topic: str,
        document_type: str = "tieu_luan",
        field: Optional[str] = None,
        target_length: Optional[str] = None,
        template_id: Optional[str] = None,
        user_requirements: Optional[str] = None,
        language: str = "vi",
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AcademicOutline:
        """Generates a structured academic outline based on topic and parameters."""
        logger.info(f"Generating outline for topic: '{topic}' (Type: {document_type})")

        # 1. Try loading matching YAML template
        lookup_key = template_id or document_type
        template_data = self.load_template(lookup_key)

        template_context_block = ""
        if template_data:
            template_context_block = (
                f"\n- **Khung Mẫu Chuẩn Tham Khảo ({template_data.get('name')})**:\n"
                f"```yaml\n{yaml.dump(template_data, allow_unicode=True, sort_keys=False)}\n```"
            )

        user_req_block = ""
        if user_requirements:
            user_req_block = f"- **Yêu cầu bổ sung của giảng viên/người dùng**: {user_requirements}"

        target_len_str = target_length or (
            template_data.get("target_pages") if template_data else "15-25 trang"
        )
        field_str = field or "Chưa xác định (Hãy tự động xác định dựa trên đề tài)"

        # 2. Render prompt
        user_prompt = OUTLINE_USER_PROMPT_TEMPLATE.format(
            topic=topic,
            document_type=document_type,
            field=field_str,
            target_length=target_len_str,
            language=language,
            user_requirements_block=user_req_block,
            template_context_block=template_context_block,
        )

        # 3. Call LLM with Pydantic structured output, with fallback
        try:
            outline = await self.llm_service.generate_structured_output(
                system_prompt=OUTLINE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema=AcademicOutline,
                model=model,
                timeout=timeout,
            )
            return outline
        except Exception as e:
            logger.warning(
                f"LLM generation failed ({e}). Falling back to template-based synthesis."
            )
            return self._build_outline_from_template(
                topic=topic,
                document_type=document_type,
                field=field,
                target_length=target_len_str,
                template_data=template_data,
            )

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseAgent implementation method."""
        inp = OutlineGenerationInput.model_validate(input_data)
        outline = await self.generate_outline(
            topic=inp.topic,
            document_type=inp.document_type,
            field=inp.field,
            target_length=inp.target_length,
            template_id=inp.template_id,
            user_requirements=inp.user_requirements,
            language=inp.language,
        )
        return outline.model_dump()


# Shared instance
outline_agent = OutlineAgent()


# Standalone runner for testing / CLI usage
async def main():
    print("=" * 60)
    print("Academic Writing Coach - OutlineAgent Standalone Runner")
    print("=" * 60)

    test_topic = "Ứng dụng Trí tuệ Nhân tạo (AI) trong Quản trị Chuỗi Cung ứng tại Việt Nam"
    test_doc_type = "tieu_luan"
    test_field = "Quản trị Kinh doanh / Logistics"

    print(f"Đề tài: {test_topic}")
    print(f"Loại văn bản: {test_doc_type}")
    print(f"Lĩnh vực: {test_field}")
    print("-" * 60)

    try:
        outline = await outline_agent.generate_outline(
            topic=test_topic,
            document_type=test_doc_type,
            field=test_field,
            target_length="20 trang",
        )

        json_output = json.dumps(outline.model_dump(), ensure_ascii=False, indent=2)
        print("\nKẾT QUẢ DÀN Ý HỌC THUẬT (JSON):\n")
        print(json_output)
        print("\n" + "=" * 60)
        print(" THÀNH CÔNG: Dàn ý JSON hợp lệ đã được khởi tạo!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[X] LỖI THỰC THI: {e}")
        print("Mẹo: Hãy đảm bảo bạn đã đặt OPENROUTER_API_KEY trong file backend/.env hoặc môi trường.")


if __name__ == "__main__":
    # Ensure UTF-8 output encoding for Windows terminal
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Ensure current directory is in python path
    current_dir = Path(__file__).parent.parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    asyncio.run(main())


