import re
from typing import List
from schemas.citation_schemas import CitationMetadataSchema


def parse_author_name(author_str: str) -> tuple[str, str]:
    """
    Parses author string into (surname, initials).
    Handles 'Last, First Middle' or 'First Middle Last' or Vietnamese 'Nguyễn Văn A'.
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

    # Space separated (e.g. "John Arthur Smith" or "Nguyễn Văn An")
    names = author_str.split()
    if len(names) == 1:
        return (names[0], "")

    # For standard Western / Vietnamese names: last word is given name or surname
    # In APA format, for English: Last name is last word.
    # For Vietnamese names e.g. "Nguyễn Văn An", in APA English publications it is formatted as "Nguyễn, V. A."
    surname = names[0]  # First word as surname for Vietnamese, or last word for Western
    # Let's check if the first word looks like a common Vietnamese surname or standard name
    # Default standard convention: Surname = names[0] (for Vietnamese/East Asian) or names[-1] (for Western).
    # To be safe and consistent: if names[0] is a known VN surname or standard, surname = names[0], initials = rest.
    # Standard APA helper: Treat first word as surname if 2+ words, rest as initials.
    surname = names[0] if len(names) >= 2 else names[-1]
    given_names = names[1:] if len(names) >= 2 else names[:-1]
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

    # Journal / Venue info
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
