# -*- coding: utf-8 -*-
"""
Curated Registry and Resolution Engine for Verified Scientific Literature & Non-DOI Papers.
Supports scholarly works published in peer-reviewed journals or academic repositories
that do not have registered Crossref DOIs or predate digital DOI indexing.
"""

from typing import List, Dict, Any, Optional
import os
import re
import json
import logging
from ranking import calculate_accurate_title_similarity, normalize_title_for_matching
from identifiers import normalize_doi

log = logging.getLogger("AcademicAPI")

# Core built-in registry of verified academic papers
DEFAULT_VERIFIED_PAPERS: List[Dict[str, Any]] = [
    {
        "title": "RP-HPLC method for determination of naproxen in pharmaceutical dosage form",
        "authors": ["Boyka Tsvetkova", "Lily Peikova"],
        "journal": "Pharmacia",
        "year": "2015",
        "volume": "62",
        "issue": "3",
        "pages": "15-19",
        "publisher": "Bulgarian Scientific Pharmaceutical Society (BSPHS)",
        "doi": None,
        "url": "https://www.researchgate.net/publication/282247012_RP-HPLC_method_for_determination_of_naproxen_in_pharmaceutical_dosage_form",
        "doi_url": "https://www.researchgate.net/publication/282247012_RP-HPLC_method_for_determination_of_naproxen_in_pharmaceutical_dosage_form",
        "oa_url": "https://www.researchgate.net/publication/282247012_RP-HPLC_method_for_determination_of_naproxen_in_pharmaceutical_dosage_form",
        "abstract": "A simple, rapid, accurate and precise reversed-phase high-performance liquid chromatography (RP-HPLC) method was developed and validated for the determination of Naproxen in tablet dosage forms. Chromatographic separation was achieved on a C18 column using a mobile phase of acetonitrile, 0.5 M potassium dihydrogen phosphate buffer (pH 2.5) and tetrahydrofuran (45:53:2 v/v/v) with UV detection at 254 nm.",
        "is_preprint": False,
        "source": "ResearchGate"
    }
]

def load_verified_registry() -> List[Dict[str, Any]]:
    """Loads verified papers including any custom additions from verified_papers.json."""
    papers = list(DEFAULT_VERIFIED_PAPERS)
    custom_path = os.path.join(os.path.dirname(__file__), "data", "verified_papers.json")
    if os.path.exists(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                custom_items = json.load(f)
                if isinstance(custom_items, list):
                    papers.extend(custom_items)
        except Exception as e:
            log.warning(f"Error loading custom verified papers: {e}")
    return papers

def search_verified_registry(title_query: str, min_similarity: float = 65.0) -> List[Dict[str, Any]]:
    """
    Searches the verified scholarly literature registry using accurate title similarity.
    Returns matched records sorted by similarity descending.
    """
    clean_q = (title_query or "").strip()
    if not clean_q:
        return []

    registry = load_verified_registry()
    matches = []
    norm_q = normalize_title_for_matching(clean_q)

    for paper in registry:
        p_title = paper.get("title", "")
        if not p_title:
            continue

        sim = calculate_accurate_title_similarity(clean_q, p_title)
        norm_p = normalize_title_for_matching(p_title)

        # Exact match boost
        if norm_q == norm_p:
            sim = 100.0

        if sim >= min_similarity:
            matched_rec = dict(paper)
            matched_rec["similarity"] = sim
            matches.append(matched_rec)

    matches.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return matches


def format_author_apa_7th(name: str) -> Optional[str]:
    """
    Converts author name to APA 7th standard: Family, Initial(s).
    Examples:
        'Boyka Tsvetkova' -> 'Tsvetkova, B.'
        'Lily Peikova' -> 'Peikova, L.'
        'Vaswani, Ashish' -> 'Vaswani, A.'
        'Aidan N. Gomez' -> 'Gomez, A. N.'
    """
    if not name or not isinstance(name, str):
        return None
    name = name.strip()
    if not name or name.lower() in ("unknown", "unknown authors", "et al", "et al.", "author", "none"):
        return None
    if "," in name:
        parts = name.split(",", 1)
        family = parts[0].strip()
        given = parts[1].strip()
    else:
        parts = name.split()
        if len(parts) == 1:
            return parts[0]
        family = parts[-1].strip()
        given = " ".join(parts[:-1]).strip()

    given_clean = re.sub(r"[^\w\s\-]", " ", given)
    tokens = [t for t in given_clean.split() if t]
    initials = [f"{t[0].upper()}." for t in tokens if t[0].isalpha()]
    if initials:
        initials_str = " ".join(initials)
        return f"{family}, {initials_str}"
    return family


def format_strict_apa_7th(paper: dict) -> Optional[str]:
    """
    Generates a strictly compliant APA 7th edition reference for a journal article.
    Returns None if ANY required information is missing or invalid.
    Strictly required:
        - authors (at least 1 valid author, none unknown)
        - year (valid 4-digit year, not 0000)
        - title (non-empty, non-generic)
        - journal (non-empty)
        - link (doi or verified direct url)
        - publication source details (volume and/or pages)
    """
    if not paper or not isinstance(paper, dict):
        return None

    # 1. Authors check
    raw_authors = paper.get("authors") or []
    if not isinstance(raw_authors, list) or len(raw_authors) == 0:
        return None
    formatted_authors = []
    for a in raw_authors:
        fmt = format_author_apa_7th(a)
        if not fmt:
            return None
        formatted_authors.append(fmt)
    if not formatted_authors:
        return None

    num_authors = len(formatted_authors)
    if num_authors == 1:
        authors_str = formatted_authors[0]
    elif num_authors == 2:
        authors_str = f"{formatted_authors[0]}, & {formatted_authors[1]}"
    elif 3 <= num_authors <= 20:
        authors_str = ", ".join(formatted_authors[:-1]) + f", & {formatted_authors[-1]}"
    else:
        authors_str = ", ".join(formatted_authors[:19]) + f", ... {formatted_authors[-1]}"

    # 2. Year check
    year = str(paper.get("year") or "").strip()
    if not year or not re.match(r"^\d{4}$", year) or year == "0000":
        return None
    year_str = f"({year})."

    # 3. Title check
    title = str(paper.get("title") or "").strip()
    if not title or title.lower().startswith("paper (") or title.lower() in ("no title", "untitled"):
        return None
    title = re.sub(r"<[^>]+>", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if title.isupper():
        words = title.split()
        capitalized_words = []
        for idx, w in enumerate(words):
            if "-" in w and all(part.isupper() for part in w.split("-") if part):
                capitalized_words.append(w)
            elif idx == 0 or (idx > 0 and words[idx - 1].endswith((": ", "?", "!"))):
                capitalized_words.append(w.capitalize())
            else:
                capitalized_words.append(w.lower())
        title = " ".join(capitalized_words)
    title_str = title.rstrip(".") + "."

    # 4. Journal check
    journal = str(paper.get("journal") or "").strip()
    if not journal or journal.lower() in ("unknown", "unknown journal"):
        return None
    journal = re.sub(r"\s+", " ", journal).strip()

    # 5. Volume, Issue, Pages check
    volume = str(paper.get("volume") or "").strip()
    issue = str(paper.get("issue") or "").strip()
    pages = str(paper.get("pages") or "").strip()
    pages = re.sub(r"\s*[-–—]+\s*", "–", pages)

    # In APA 7th journal references, volume and/or pages must be present
    if not volume and not pages:
        return None

    if volume and issue:
        vol_issue = f"{volume}({issue})"
        if pages:
            source_str = f"{journal}, {vol_issue}, {pages}."
        else:
            source_str = f"{journal}, {vol_issue}."
    elif volume:
        if pages:
            source_str = f"{journal}, {volume}, {pages}."
        else:
            source_str = f"{journal}, {volume}."
    elif pages:
        source_str = f"{journal}, {pages}."
    else:
        source_str = f"{journal}."

    # 6. Link check (DOI or direct URL)
    raw_doi = paper.get("doi")
    doi = normalize_doi(raw_doi) if raw_doi else ""
    doi_url = str(paper.get("doi_url") or paper.get("url") or paper.get("oa_url") or "").strip()

    if doi:
        link_str = f"https://doi.org/{doi}"
    elif doi_url and (doi_url.startswith("http://") or doi_url.startswith("https://")):
        link_str = doi_url
    else:
        return None

    return f"{authors_str} {year_str} {title_str} {source_str} {link_str}".strip()

