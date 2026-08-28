from typing import List, Optional
from pydantic import BaseModel, Field


class OutlineSubSection(BaseModel):
    """Sub-section / item details within an outline section."""
    title: str = Field(..., description="Tên tiểu mục (e.g., 1.1. Khái niệm...)")
    description: Optional[str] = Field(None, description="Mô tả nội dung cần viết trong tiểu mục")
    estimated_word_count: Optional[int] = Field(None, description="Số từ dự kiến cho tiểu mục")
    key_points: List[str] = Field(default_factory=list, description="Các ý chính cần phát triển")


class OutlineSection(BaseModel):
    """Main section / Chapter in the outline."""
    section_code: str = Field(..., description="Mã phần hoặc chương (e.g., INTRO, CH1, OUTRO)")
    title: str = Field(..., description="Tên chương / phần chính")
    description: Optional[str] = Field(None, description="Mô tả mục tiêu của chương")
    subsections: List[OutlineSubSection] = Field(default_factory=list, description="Danh sách tiểu mục")


class AcademicOutline(BaseModel):
    """Structured Academic Outline data model."""
    topic: str = Field(..., description="Tên đề tài nghiên cứu")
    document_type: str = Field(..., description="Loại văn bản (tieu_luan, khoa_luan, luan_van, etc.)")
    field: Optional[str] = Field(None, description="Ngành / Lĩnh vực chuyên môn")
    language: str = Field("vi", description="Ngôn ngữ trình bày (vi / en)")
    total_estimated_pages: Optional[str] = Field(None, description="Số trang / số từ ước tính toàn bài")
    sections: List[OutlineSection] = Field(..., description="Danh sách các chương/phần chính")
    research_methodology_suggestion: Optional[str] = Field(None, description="Gợi ý phương pháp nghiên cứu phù hợp")
    key_academic_keywords: List[str] = Field(default_factory=list, description="Từ khóa học thuật gợi ý cho tra cứu")
    writing_guidelines: Optional[str] = Field(None, description="Hướng dẫn viết & lưu ý chuyên môn cho đề tài này")


class OutlineGenerationInput(BaseModel):
    """Input payload for outline generation agent."""
    topic: str = Field(..., description="Đề tài / Tên bài viết học thuật")
    document_type: str = Field("tieu_luan", description="Loại văn bản (tieu_luan, khoa_luan, luan_van, bai_bao_khoa_hoc, bao_cao_thuc_tap, de_cuong_nghien_cuu, tong_quan_tai_lieu, phan_tich_case_study)")
    field: Optional[str] = Field(None, description="Chuyên ngành / Lĩnh vực (VD: Quản trị kinh doanh, CNTT, Luật, Y học)")
    target_length: Optional[str] = Field(None, description="Dung lượng mong muốn (VD: 20 trang, 5000 từ)")
    template_id: Optional[str] = Field(None, description="ID template dàn ý mẫu (nếu muốn áp dụng cụ thể)")
    user_requirements: Optional[str] = Field(None, description="Yêu cầu riêng của giảng viên / người dùng")
    language: str = Field("vi", description="Ngôn ngữ dàn ý (vi/en)")


class OutlineResponse(BaseModel):
    """Response returned from outline agent."""
    success: bool = True
    outline: Optional[AcademicOutline] = None
    template_used: Optional[str] = None
    error: Optional[str] = None
