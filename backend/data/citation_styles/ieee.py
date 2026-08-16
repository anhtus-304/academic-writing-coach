from typing import List
from schemas.citation_schemas import CitationMetadataSchema
from data.citation_styles.apa7 import parse_author_name


def format_ieee_author_name(author_str: str) -> str:
    surname, initials = parse_author_name(author_str)
    if initials:
        return f"{initials} {surname}"
    return surname


def format_ieee_authors_full(authors: List[str]) -> str:
    if not authors:
        return "Unknown Author,"

    formatted_authors = [format_ieee_author_name(a) for a in authors]
    n = len(formatted_authors)

    if n == 1:
        return f"{formatted_authors[0]},"
    elif 2 <= n <= 6:
        all_but_last = ", ".join(formatted_authors[:-1])
        return f"{all_but_last} and {formatted_authors[-1]},"
    else: # > 6 authors
        return f"{formatted_authors[0]} et al.,"


def format_ieee_full(meta: CitationMetadataSchema, index: int = 1) -> str:
    """
    Formats metadata into full IEEE citation string.
    Example:
    [1] V. A. Nguyen and T. B. Tran, "Title of paper," Journal Name, vol. 12, no. 3, pp. 45-52, 2023, doi: 10.xxx.
    """
    authors_str = format_ieee_authors_full(meta.authors)
    title_str = f'"{meta.title.rstrip(".")},"'

    parts = [f"[{index}] {authors_str}", title_str]

    venue_parts = []
    if meta.journal:
        venue_parts.append(meta.journal)
    elif meta.publisher:
        venue_parts.append(meta.publisher)

    if meta.volume:
        venue_parts.append(f"vol. {meta.volume}")
    if meta.issue:
        venue_parts.append(f"no. {meta.issue}")
    if meta.pages:
        venue_parts.append(f"pp. {meta.pages}")

    venue_parts.append(str(meta.year))

    parts.append(", ".join(venue_parts) + ".")

    if meta.doi:
        doi_clean = meta.doi.replace("https://doi.org/", "")
        parts.append(f"doi: {doi_clean}.")
    elif meta.url:
        parts.append(f"url: {meta.url}.")

    return " ".join(parts)


def format_ieee_in_text(index: int = 1) -> str:
    """
    Formats IEEE in-text citation string.
    Example: [1]
    """
    return f"[{index}]"
