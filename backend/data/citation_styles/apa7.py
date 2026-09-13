import re
from typing import List
from schemas.citation_schemas import CitationMetadataSchema, DocumentType


def is_vietnamese_name(name: str) -> bool:
    vn_chars = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]'
    if re.search(vn_chars, name):
        return True
    first_word = name.strip().split()[0].lower() if name.strip() else ""
    common_vn_surnames = {
        "nguyen", "tran", "le", "pham", "hoang", "huynh", "phan", "vu", "vo", 
        "dang", "bui", "do", "ho", "ngo", "duong", "ly", "dinh", "doan"
    }
    return first_word in common_vn_surnames


def parse_author_name(author_str: str) -> tuple[str, str]:
    """
    Parses author string into (surname, initials).
    Handles:
    - 'Last, First Middle' -> ('Last', 'F. M.')
    - Vietnamese 'Nguyễn Văn A' -> ('Nguyễn', 'V. A.')
    - Western 'Cedric De Boom' -> ('De Boom', 'C.')
    - Western 'John Arthur Smith' -> ('Smith', 'J. A.')
    """
    author_str = author_str.strip()
    if not author_str:
        return ("Unknown", "")

    if "," in author_str:
        parts = author_str.split(",", 1)
        surname = parts[0].strip()
        first_names = parts[1].strip().split()
        initials = ". ".join([name[0].upper() for name in first_names if name]) + "." if first_names else ""
        return (surname, initials)

    names = author_str.split()
    if len(names) == 1:
        return (names[0], "")

    if is_vietnamese_name(author_str):
        surname = names[0]
        given_names = names[1:]
    else:
        # Western name handling:
        # Check compound surname prefixes (e.g. "Cedric De Boom", "Ludwig van Beethoven")
        prefixes = {"de", "van", "von", "der", "du", "da", "di", "la", "le", "del", "dos", "das"}
        if len(names) >= 3 and names[-2].lower() in prefixes:
            surname = f"{names[-2]} {names[-1]}"
            given_names = names[:-2]
        else:
            surname = names[-1]
            given_names = names[:-1]

    initials = ". ".join([n[0].upper() for n in given_names if n]) + "." if given_names else ""
    return (surname, initials)


def format_apa7_authors_full(authors: List[str]) -> str:
    if not authors:
        return "Unknown Author."

    formatted_authors = []
    for author in authors:
        surname, initials = parse_author_name(author)
        if initials:
            formatted_authors.append(f"{surname}, {initials}")
        else:
            formatted_authors.append(surname)

    n = len(formatted_authors)
    if n == 1:
        return f"{formatted_authors[0]}."
    elif n == 2:
        return f"{formatted_authors[0]}, & {formatted_authors[1]}."
    elif 3 <= n <= 20:
        return f"{', '.join(formatted_authors[:-1])}, & {formatted_authors[-1]}."
    else: # > 20 authors
        first_19 = ", ".join(formatted_authors[:19])
        last = formatted_authors[-1]
        return f"{first_19}, ... {last}."


def format_apa7_authors_in_text(authors: List[str]) -> str:
    if not authors:
        return "Unknown"

    surnames = [parse_author_name(a)[0] for a in authors]
    n = len(surnames)
    if n == 1:
        return surnames[0]
    elif n == 2:
        return f"{surnames[0]} & {surnames[1]}"
    else:
        return f"{surnames[0]} et al."


def format_apa7_full(meta: CitationMetadataSchema) -> str:
    """
    Formats metadata into full APA 7th edition citation string.
    Example:
    Nguyen, V. A., & Tran, T. B. (2023). Title of paper. Journal Name, 12(3), 45-52. https://doi.org/xxx
    """
    authors_str = format_apa7_authors_full(meta.authors)
    year_str = f"({meta.year})."
    title_str = meta.title.rstrip(".") + "."

    elements = [authors_str, year_str, title_str]

    doc_type = getattr(meta, "doc_type", DocumentType.JOURNAL)

    if doc_type == DocumentType.BOOK:
        pub = meta.publisher or meta.journal
        if pub:
            elements.append(pub.rstrip(".") + ".")
    elif doc_type == DocumentType.CONFERENCE:
        conf_name = meta.journal or meta.publisher or "Conference Proceedings"
        page_part = f"(pp. {meta.pages})" if meta.pages else ""
        in_conf = f"In {conf_name} {page_part}".strip()
        elements.append(in_conf.rstrip(".") + ".")
    elif doc_type == DocumentType.THESIS:
        school = meta.publisher or "University"
        thesis_label = f"[{meta.journal or 'Master dissertation'}, {school}]."
        elements.append(thesis_label)
    elif doc_type == DocumentType.WEB:
        site = meta.publisher or meta.journal
        if site:
            elements.append(site.rstrip(".") + ".")
    else:
        # Default / JOURNAL
        venue_parts = []
        if meta.journal:
            venue_parts.append(meta.journal)
        elif meta.publisher:
            venue_parts.append(meta.publisher)

        if meta.volume:
            vol_issue = meta.volume
            if meta.issue:
                vol_issue += f"({meta.issue})"
            venue_parts.append(vol_issue)

        if meta.pages:
            venue_parts.append(meta.pages)

        if venue_parts:
            elements.append(", ".join(venue_parts) + ".")

    # DOI or URL
    if meta.doi:
        doi_url = meta.doi if meta.doi.startswith("http") else f"https://doi.org/{meta.doi}"
        elements.append(doi_url)
    elif meta.url:
        elements.append(meta.url)

    return " ".join(elements)


def format_apa7_in_text(meta: CitationMetadataSchema) -> str:
    """
    Formats metadata into APA 7th edition in-text citation string.
    Example: (Nguyen & Tran, 2023)
    """
    authors_str = format_apa7_authors_in_text(meta.authors)
    return f"({authors_str}, {meta.year})"
