import io
import re
import docx
import mammoth
import markdown


def parse_outline_from_markdown(content: str) -> list[dict]:
    """
    Phân tích văn bản Markdown thành cây phân cấp OutlineNode:
    - # hoặc ## -> Level 1 (Chương)
    - ### -> Level 2 (Mục)
    - #### hoặc - / * / 1. -> Level 3 (Ý chính)
    """
    lines = content.splitlines()
    sections: list[dict] = []
    current_sec: dict | None = None
    current_sub: dict | None = None

    sec_idx = 1
    sub_idx = 1
    kp_idx = 1

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Level 1: # hoặc ##
        if line.startswith("# ") or line.startswith("## "):
            title = re.sub(r"^#{1,2}\s*", "", line).strip()
            current_sec = {
                "id": f"sec-{sec_idx}",
                "title": title,
                "level": 1,
                "children": [],
            }
            sections.append(current_sec)
            sec_idx += 1
            sub_idx = 1
            kp_idx = 1
            current_sub = None

        # Level 2: ###
        elif line.startswith("### "):
            title = re.sub(r"^###\s*", "", line).strip()
            if not current_sec:
                current_sec = {
                    "id": f"sec-{sec_idx}",
                    "title": "Chương 1",
                    "level": 1,
                    "children": [],
                }
                sections.append(current_sec)
                sec_idx += 1
                sub_idx = 1

            current_sub = {
                "id": f"sub-{sec_idx - 1}-{sub_idx}",
                "title": title,
                "level": 2,
                "children": [],
            }
            current_sec["children"].append(current_sub)
            sub_idx += 1
            kp_idx = 1

        # Level 3: #### hoặc Bullet list - / * / + hoặc Số thứ tự 1.
        elif line.startswith("#### ") or line.startswith("- ") or line.startswith("* ") or re.match(r"^\d+\.\s+", line):
            clean_title = re.sub(r"^(####|-|\*|\+|\d+\.)\s*", "", line).strip()
            if not current_sec:
                current_sec = {
                    "id": f"sec-{sec_idx}",
                    "title": "Chương 1",
                    "level": 1,
                    "children": [],
                }
                sections.append(current_sec)
                sec_idx += 1
                sub_idx = 1

            if not current_sub:
                current_sub = {
                    "id": f"sub-{sec_idx - 1}-{sub_idx}",
                    "title": "Mục 1.1",
                    "level": 2,
                    "children": [],
                }
                current_sec["children"].append(current_sub)
                sub_idx += 1

            kp_node = {
                "id": f"kp-{sec_idx - 1}-{sub_idx - 1}-{kp_idx}",
                "title": f"• {clean_title}",
                "level": 3,
                "children": [],
            }
            current_sub["children"].append(kp_node)
            kp_idx += 1

        # Dòng chữ thông thường
        else:
            if current_sub:
                kp_node = {
                    "id": f"kp-{sec_idx - 1}-{sub_idx - 1}-{kp_idx}",
                    "title": f"• {line}",
                    "level": 3,
                    "children": [],
                }
                current_sub["children"].append(kp_node)
                kp_idx += 1

    return sections


def parse_outline_from_docx(file_bytes: bytes) -> list[dict]:
    """
    Phân tích file Word .docx thành cây phân cấp OutlineNode:
    Nhận diện dựa trên Heading 1, 2, 3 và các tiền tố học thuật ("Chương", "1.", "1.1").
    """
    doc = docx.Document(io.BytesIO(file_bytes))
    sections: list[dict] = []
    current_sec: dict | None = None
    current_sub: dict | None = None

    sec_idx = 1
    sub_idx = 1
    kp_idx = 1

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        style_name = p.style.name.lower() if p.style else ""

        # Level 1: Heading 1 hoặc "Chương X" hoặc "1. Tiêu đề"
        is_h1 = (
            "heading 1" in style_name
            or bool(re.match(r"^(chương\s+[0-9ivx]+|phần\s+[0-9ivx]+|[0-9]+\.)\s+", text, re.IGNORECASE))
        )

        # Level 2: Heading 2 hoặc "1.1 Tiêu đề"
        is_h2 = (
            "heading 2" in style_name
            or bool(re.match(r"^[0-9]+\.[0-9]+\.?\s+", text))
        )

        # Level 3: Heading 3 hoặc "1.1.1 Tiêu đề" hoặc bullet list
        is_h3 = (
            "heading 3" in style_name
            or "list" in style_name
            or bool(re.match(r"^[0-9]+\.[0-9]+\.[0-9]+\.?\s+", text))
            or text.startswith("•")
            or text.startswith("-")
        )

        if is_h1:
            current_sec = {
                "id": f"sec-{sec_idx}",
                "title": text,
                "level": 1,
                "children": [],
            }
            sections.append(current_sec)
            sec_idx += 1
            sub_idx = 1
            kp_idx = 1
            current_sub = None
        elif is_h2:
            if not current_sec:
                current_sec = {
                    "id": f"sec-{sec_idx}",
                    "title": "Chương 1",
                    "level": 1,
                    "children": [],
                }
                sections.append(current_sec)
                sec_idx += 1
                sub_idx = 1

            current_sub = {
                "id": f"sub-{sec_idx - 1}-{sub_idx}",
                "title": text,
                "level": 2,
                "children": [],
            }
            current_sec["children"].append(current_sub)
            sub_idx += 1
            kp_idx = 1
        elif is_h3:
            if not current_sec:
                current_sec = {
                    "id": f"sec-{sec_idx}",
                    "title": "Chương 1",
                    "level": 1,
                    "children": [],
                }
                sections.append(current_sec)
                sec_idx += 1
                sub_idx = 1

            if not current_sub:
                current_sub = {
                    "id": f"sub-{sec_idx - 1}-{sub_idx}",
                    "title": "Mục 1.1",
                    "level": 2,
                    "children": [],
                }
                current_sec["children"].append(current_sub)
                sub_idx += 1

            clean_text = text if text.startswith("•") else f"• {text}"
            kp_node = {
                "id": f"kp-{sec_idx - 1}-{sub_idx - 1}-{kp_idx}",
                "title": clean_text,
                "level": 3,
                "children": [],
            }
            current_sub["children"].append(kp_node)
            kp_idx += 1

    return sections


def convert_file_to_editor_html(file_bytes: bytes, filename: str) -> str:
    """
    Chuyển đổi file tải lên (.docx hoặc .md) sang chuỗi HTML sạch chuẩn ngữ nghĩa cho Tiptap Editor.
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ("docx", "doc"):
        result = mammoth.convert_to_html(io.BytesIO(file_bytes))
        html = result.value
        return html
    elif ext in ("md", "markdown", "txt"):
        try:
            content_str = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = file_bytes.decode("latin-1", errors="replace")

        html = markdown.markdown(
            content_str,
            extensions=["tables", "fenced_code", "nl2br"]
        )
        return html
    else:
        raise ValueError(f"Định dạng file không được hỗ trợ: .{ext}. Vui lòng tải lên file .docx hoặc .md")
