import re
from typing import List
from schemas.citation_schemas import CitationMetadataSchema


def is_vietnamese_text(text: str) -> bool:
    """
    Checks if text contains Vietnamese diacritics / unicode characters or Vietnamese name pattern.
    """
    vn_chars = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]'
    return bool(re.search(vn_chars, text))


def get_sort_key_bgddt(meta: CitationMetadataSchema) -> tuple[int, str]:
    """
    Returns a sort key tuple:
    - 0 for Vietnamese documents, sorted by GIVEN NAME (Tên) of first author.
    - 1 for Foreign/English documents, sorted by SURNAME (Họ) of first author.
    """
    if not meta.authors:
        return (1, "Unknown")

    first_author = meta.authors[0].strip()
    is_vn = is_vietnamese_text(first_author) or is_vietnamese_text(meta.title)

    names = first_author.split()
    if is_vn:
        # Sort by last word (Given name in Vietnamese e.g. "An" in "Nguyễn Văn An")
        sort_name = names[-1].lower() if names else first_author.lower()
        return (0, sort_name)
    else:
        # Sort by Surname (First word if "Smith, John" or last word if "John Smith")
        if "," in first_author:
            surname = first_author.split(",")[0].strip().lower()
        else:
            surname = names[-1].lower() if names else first_author.lower()
        return (1, surname)


def format_bgddt_authors_full(authors: List[str], is_vn: bool) -> str:
    if not authors:
        return "Vô danh" if is_vn else "Unknown"

    if is_vn:
        # Vietnamese: keep full name unchanged, e.g. "Nguyễn Văn A, Trần Thị B"
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]}, {authors[1]}"
        else:
            return f"{authors[0]} và ctg."
    else:
        # Foreign: Surname I.M., e.g. "Smith J.A., Taylor R."
        formatted = []
        for a in authors:
            if "," in a:
                parts = a.split(",", 1)
                surname = parts[0].strip()
                initials = "".join([n[0].upper() + "." for n in parts[1].strip().split() if n])
                formatted.append(f"{surname} {initials}".strip())
            else:
                names = a.split()
                if len(names) >= 2:
                    surname = names[-1]
                    initials = "".join([n[0].upper() + "." for n in names[:-1] if n])
                    formatted.append(f"{surname} {initials}")
                else:
                    formatted.append(a)
        if len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]}, {formatted[1]}"
        else:
            return f"{formatted[0]} et al."


def format_bgddt_full(meta: CitationMetadataSchema, index: int = 1) -> str:
    """
    Formats metadata according to Vietnamese Ministry of Education & Training (Bộ GD&ĐT) standards.
    Example Vietnamese:
    [1] Nguyễn Văn A, Trần Thị B (2023), "Ảnh hưởng của...", Tạp chí Phát triển Kinh tế, Số 12, tr. 45-52.
    Example Foreign:
    [2] Smith J.A. (2023), "Social Media Influence...", Journal of Business, Vol. 12(No. 3), pp. 45-52.
    """
    is_vn = is_vietnamese_text(meta.authors[0] if meta.authors else meta.title) or is_vietnamese_text(meta.title)
    authors_str = format_bgddt_authors_full(meta.authors, is_vn)
    year_str = f"({meta.year})"
    title_str = f'"{meta.title.rstrip(".")}"'

    parts = [f"[{index}] {authors_str} {year_str}, {title_str}"]

    venue_parts = []
    if meta.journal:
        venue_parts.append(meta.journal)
    elif meta.publisher:
        venue_parts.append(meta.publisher)

    vol_issue_parts = []
    if meta.volume:
        vol_issue_parts.append(f"Tập {meta.volume}" if is_vn else f"Vol. {meta.volume}")
    if meta.issue:
        vol_issue_parts.append(f"Số {meta.issue}" if is_vn else f"No. {meta.issue}")

    if vol_issue_parts:
        venue_parts.append(" ".join(vol_issue_parts))

    if meta.pages:
        page_prefix = "tr. " if is_vn else "pp. "
        venue_parts.append(f"{page_prefix}{meta.pages}")

    if venue_parts:
        parts.append(", ".join(venue_parts) + ".")

    if meta.doi:
        parts.append(f"DOI: {meta.doi}.")

    return " ".join(parts)


def format_bgddt_in_text(meta: CitationMetadataSchema, index: int = 1, use_numeric: bool = True) -> str:
    """
    Formats Bộ GD&ĐT in-text citation string.
    If numeric (standard): [1]
    If author-year: (Nguyễn Văn A, 2023) or (Smith và ctg., 2023)
    """
    if use_numeric:
        return f"[{index}]"

    is_vn = is_vietnamese_text(meta.authors[0] if meta.authors else meta.title)
    if not meta.authors:
        author_ref = "Vô danh" if is_vn else "Unknown"
    else:
        first_author = meta.authors[0]
        if len(meta.authors) == 1:
            author_ref = first_author
        elif len(meta.authors) == 2:
            author_ref = f"{first_author} và {meta.authors[1]}" if is_vn else f"{first_author} & {meta.authors[1]}"
        else:
            author_ref = f"{first_author} và ctg." if is_vn else f"{first_author} et al."

    return f"({author_ref}, {meta.year})"


def sort_bgddt_bibliography(metadatas: List[CitationMetadataSchema]) -> List[CitationMetadataSchema]:
    """
    Sorts bibliography items according to Bộ GD&ĐT regulations:
    1. Vietnamese items sorted alphabetically by Author Given Name (Tên).
    2. Foreign items sorted alphabetically by Author Surname (Họ).
    """
    return sorted(metadatas, key=get_sort_key_bgddt)
