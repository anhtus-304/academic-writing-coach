import io
import pytest
import docx
from bs4 import BeautifulSoup

from services import export_service, import_service


def test_export_to_docx_structure():
    topic = "Nghiên cứu ứng dụng Blockchain trong Nông nghiệp thông minh"
    html_content = """
    <h2>CHƯƠNG 1: TỔNG QUAN</h2>
    <p>Nội dung giới thiệu về <strong>Blockchain</strong> và <em>Smart Contracts</em>.</p>
    <ul>
        <li>Tính bất biến</li>
        <li>Tính minh bạch</li>
    </ul>
    <p class="citation-entry">(Nguyen &amp; Tran, 2024). Ứng dụng Blockchain trong chuỗi cung ứng.</p>
    """

    buffer = export_service.export_to_docx(topic, html_content)
    assert isinstance(buffer, io.BytesIO)
    assert buffer.getbuffer().nbytes > 0

    # Đọc lại docx để kiểm tra cấu trúc
    doc = docx.Document(buffer)
    # Kiểm tra có tiêu đề và các đoạn văn
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "BLOCKCHAIN" in full_text
    assert "CHƯƠNG 1: TỔNG QUAN" in full_text
    assert "Tính bất biến" in full_text
    assert "Nguyen & Tran, 2024" in full_text

    # Kiểm tra lề trang chuẩn A4 học thuật
    section = doc.sections[0]
    assert round(section.page_width.cm, 1) == 21.0
    assert round(section.page_height.cm, 1) == 29.7
    assert round(section.top_margin.cm, 1) == 2.0
    assert round(section.bottom_margin.cm, 1) == 2.0
    assert round(section.left_margin.cm, 1) == 3.0
    assert round(section.right_margin.cm, 1) == 2.0


def test_export_to_markdown():
    topic = "Học máy trong Y tế"
    html_content = """
    <h2>Chương 1: Giới thiệu</h2>
    <p>Đây là bài nghiên cứu về <strong>AI</strong> và <em>Deep Learning</em>.</p>
    <ul>
        <li>Điểm 1</li>
        <li>Điểm 2</li>
    </ul>
    <p class="citation-entry">[1] LeCun, Y. et al. (2015). Deep learning. Nature.</p>
    """

    md = export_service.export_to_markdown(topic, html_content)
    assert "# Học máy trong Y tế" in md
    assert "## Chương 1: Giới thiệu" in md
    assert "**AI**" in md
    assert "*Deep Learning*" in md
    assert "- Điểm 1" in md
    assert "> [1] LeCun, Y. et al. (2015). Deep learning. Nature." in md


def test_parse_outline_from_markdown():
    md_outline = """
# Chương 1: Mở đầu
### 1.1 Tính cấp thiết
- Nhu cầu thực tiễn
- Mục tiêu nghiên cứu
### 1.2 Đối tượng và phạm vi
# Chương 2: Cơ sở lý thuyết
### 2.1 Khái niệm cơ bản
* Định nghĩa
* Phân loại
"""
    nodes = import_service.parse_outline_from_markdown(md_outline)
    assert len(nodes) == 2
    assert nodes[0]["title"] == "Chương 1: Mở đầu"
    assert nodes[0]["level"] == 1
    assert len(nodes[0]["children"]) == 2

    sub1 = nodes[0]["children"][0]
    assert sub1["title"] == "1.1 Tính cấp thiết"
    assert sub1["level"] == 2
    assert len(sub1["children"]) == 2
    assert "Nhu cầu thực tiễn" in sub1["children"][0]["title"]

    assert nodes[1]["title"] == "Chương 2: Cơ sở lý thuyết"
    assert len(nodes[1]["children"]) == 1


def test_parse_outline_from_docx():
    # Tạo docx giả lập có Heading 1, 2, 3
    doc = docx.Document()
    doc.add_heading("Chương 1: Tổng quan", level=1)
    doc.add_heading("1.1 Khái niệm", level=2)
    doc.add_paragraph("• Khái niệm ban đầu")
    doc.add_paragraph("• Khái niệm nâng cao")
    doc.add_heading("Chương 2: Thực nghiệm", level=1)
    doc.add_heading("2.1 Mô hình", level=2)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    nodes = import_service.parse_outline_from_docx(buf.getvalue())
    assert len(nodes) == 2
    assert nodes[0]["title"] == "Chương 1: Tổng quan"
    assert len(nodes[0]["children"]) == 1
    assert nodes[0]["children"][0]["title"] == "1.1 Khái niệm"
    assert len(nodes[0]["children"][0]["children"]) == 2
    assert nodes[1]["title"] == "Chương 2: Thực nghiệm"


def test_convert_file_to_editor_html():
    # Test Markdown file
    md_content = "# Tiêu đề chính\n\nĐây là một đoạn văn có **in đậm**."
    html_from_md = import_service.convert_file_to_editor_html(md_content.encode("utf-8"), "document.md")
    assert "<h1>Tiêu đề chính</h1>" in html_from_md
    assert "<strong>in đậm</strong>" in html_from_md

    # Test Docx file
    doc = docx.Document()
    doc.add_heading("Heading từ Docx", level=1)
    doc.add_paragraph("Đoạn văn trong file Word với định dạng nổi bật.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    html_from_docx = import_service.convert_file_to_editor_html(buf.getvalue(), "sample.docx")
    assert "<h1>Heading từ Docx</h1>" in html_from_docx
    assert "Đoạn văn trong file Word" in html_from_docx


def test_convert_file_unsupported_format():
    with pytest.raises(ValueError, match="không được hỗ trợ"):
        import_service.convert_file_to_editor_html(b"test", "test.pdf")


def test_vietnamese_content_disposition_header_encoding():
    import re
    import urllib.parse
    from starlette.responses import Response

    topic = "Nghiên cứu Ứng dụng Blockchain trong Nông nghiệp thông minh"
    clean_filename = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    ascii_fallback = re.sub(r'[^a-zA-Z0-9_\-]', '', clean_filename) or "Academic_Paper"
    encoded_filename = urllib.parse.quote(f"{clean_filename}.docx")

    header_val = f'attachment; filename="{ascii_fallback}.docx"; filename*=UTF-8\'\'{encoded_filename}'
    
    # Test Starlette Response accepts this header without UnicodeEncodeError
    res = Response(content=b"test", headers={"Content-Disposition": header_val})
    assert res.headers["Content-Disposition"] == header_val
    # Test encoding to latin-1 (exactly what Starlette does in init_headers)
    raw_encoded = header_val.encode("latin-1")
    assert raw_encoded is not None

