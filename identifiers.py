# -*- coding: utf-8 -*-
"""
Centralized scholarly identifier normalization and extraction.
Provides canonical representations for DOIs, PMIDs, PMCIDs, and arXiv IDs.
"""

import re
import urllib.parse
from typing import Optional

DOI_REGEX = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b', re.IGNORECASE)

def normalize_doi(value: Optional[str]) -> Optional[str]:
    """
    Transforms any valid DOI representation into canonical form: 10.xxxx/...
    Handles URL prefixes (http/https, dx.doi.org, doi.org), 'doi:' prefixes,
    URL encoding, whitespace, and trailing punctuation.
    Returns None if value is invalid or empty.
    """
    if not value:
        return None

    s = str(value).strip()
    if not s or s.lower() in ("n/a", "none", "null", ""):
        return None

    try:
        s = urllib.parse.unquote(s)
    except Exception:
        pass

    s = s.replace('\u200b', '').replace('\xa0', ' ').strip()
    s = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', s, flags=re.IGNORECASE).strip()

    match = DOI_REGEX.search(s)
    if match:
        doi = match.group(1).strip()
        doi = re.sub(r'[.,;:)\]>]+$', '', doi)
        return doi.lower()

    return None

def extract_doi(text: Optional[str]) -> Optional[str]:
    """
    Extracts canonical DOI from a text or query string if present.
    """
    if not text:
        return None
    return normalize_doi(text)

def is_doi_query(query: Optional[str]) -> bool:
    """
    Checks if a query is primarily an exact DOI identifier search.
    """
    if not query:
        return False
    q = query.strip()
    doi = extract_doi(q)
    if not doi:
        return False
    q_clean = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', q, flags=re.IGNORECASE).strip()
    return q_clean.lower().startswith(doi) or len(q_clean) <= len(doi) + 4
