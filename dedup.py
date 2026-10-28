# -*- coding: utf-8 -*-
"""
Multi-tier Record Linkage & Deduplication for Knowledge Ocean.
Supports exact identifier matching, bibliographic normalization, and lossless metadata merging.
Enforces author/year corroboration on title matches and maintains distinct linked records
for preprints vs published journal articles.
"""

import re
import hashlib
from typing import Dict, List, Optional, Set
from models import CanonicalPaper
from identifiers import normalize_doi

# Regex for explicit erratum/retraction notice prefixes
RETRACTION_PREFIX_RE = re.compile(
    r'^(?:(?:author\s+|publisher\s+)?correction(?:\s*to\b|\s*:|\s+notice\b)|erratum(?:\s*to\b|\s*:|\s+notice\b)?|corrigendum(?:\s*to\b|\s*:|\s+notice\b)?|retraction(?:\s*note\b|\s*notice\b|\s*:|\s+to\b))\s*',
    re.IGNORECASE
)

def is_banned_publication(title: Optional[str], doc_type: Optional[str] = None) -> bool:
    """
    Checks if a document is an erratum, retraction notice, or withdrawn item.
    Distinguishes publication status from legitimate scientific terms like 'Error Correction' or 'Retraction mechanisms'.
    """
    if doc_type and str(doc_type).lower() in ('erratum', 'corrigendum', 'retraction', 'retracted-publication'):
        return True
    if not title:
        return True
    t_clean = title.strip().lower()
    if t_clean in ("no title", "null", "", "retraction", "erratum", "corrigendum"):
        return True
    if 'meeting abstract' in t_clean or 'cheminform' in t_clean:
        return True
    if re.search(r'\bwithdrawn\b', t_clean):
        return True
    if RETRACTION_PREFIX_RE.match(t_clean):
        return True
    return False

def normalize_title(title: Optional[str]) -> str:
    """Normalizes title by removing punctuation, extra spaces, and converting to lowercase."""
    if not title:
        return ""
    t = str(title).lower().strip()
    t = t.replace('α', 'alpha').replace('β', 'beta').replace('γ', 'gamma').replace('δ', 'delta')
    t = re.sub(r'<[^>]+>', '', t)
    clean = re.sub(r'[^a-z0-9\u0600-\u06FF]', '', t)
    return clean

def get_title_hash(title: Optional[str]) -> str:
    norm = normalize_title(title)
    if not norm:
        return ""
    return hashlib.sha256(norm.encode('utf-8')).hexdigest()

def extract_author_tokens(authors: List[str]) -> Set[str]:
    """Extracts lowercase surname or name tokens from author list."""
    tokens = set()
    for a in authors:
        if not a or a.lower() in ("unknown authors", "et al", "et al."):
            continue
        parts = re.split(r'[, ]+', a.strip().lower())
        for part in parts:
            if len(part) >= 3:
                tokens.add(part)
    return tokens

def have_bibliographic_corroboration(p1: CanonicalPaper, p2: CanonicalPaper) -> bool:
    """
    Strict validation to ensure two records sharing a title are actually the same work.
    Requires author overlap and/or publication year tolerance.
    """
    a1 = extract_author_tokens(p1.authors)
    a2 = extract_author_tokens(p2.authors)

    # If both have known authors, they MUST overlap on at least one author token
    if a1 and a2:
        if not (a1 & a2):
            return False

    # Publication year tolerance: max 1 year difference
    if p1.year and p2.year and p1.year != "0000" and p2.year != "0000":
        try:
            if abs(int(p1.year) - int(p2.year)) > 1:
                return False
        except ValueError:
            pass

    # If neither record has author information, check journal or require substantial title length
    if not a1 and not a2:
        if p1.journal and p2.journal:
            j1 = normalize_title(p1.journal)
            j2 = normalize_title(p2.journal)
            if not (j1 in j2 or j2 in j1):
                return False
        elif len(p1.title.strip()) < 25:
            # Short generic titles (e.g. 'Introduction', 'Editorial') without authors cannot be safely merged
            return False

    return True


class ScholarlyPaperIndex:
    """
    Maintains index of scholarly papers across multiple identifiers and titles.
    Performs lossless record linkage and establishes bidirectional links
    between preprints and published journal articles without blind merges.
    """
    def __init__(self):
        self.papers: List[CanonicalPaper] = []
        self.doi_map: Dict[str, CanonicalPaper] = {}
        self.pmid_map: Dict[str, CanonicalPaper] = {}
        self.pmcid_map: Dict[str, CanonicalPaper] = {}
        self.arxiv_map: Dict[str, CanonicalPaper] = {}
        self.title_map: Dict[str, List[CanonicalPaper]] = {}

    def add_or_merge(self, paper: CanonicalPaper) -> CanonicalPaper:
        """
        Attempts to link incoming paper to an existing record.
        If a match is found between preprint and published version, links them bidirectionally.
        If a match is found between homogeneous versions, merges metadata losslessly.
        Otherwise, stores the new paper.
        """
        existing = self._find_existing(paper)
        if existing is not None:
            # Constraint 5: Keep preprint and published version as linked records, do not merge blindly
            if paper.is_preprint != existing.is_preprint:
                if paper.is_preprint:
                    existing.linked_preprint_id = paper.id
                    paper.linked_published_id = existing.id
                else:
                    existing.linked_published_id = paper.id
                    paper.linked_preprint_id = existing.id
                self.papers.append(paper)
                self._index_paper(paper)
                return paper
            else:
                existing.merge(paper)
                self._index_paper(existing)
                return existing

        self.papers.append(paper)
        self._index_paper(paper)
        return paper

    def _find_existing(self, p: CanonicalPaper) -> Optional[CanonicalPaper]:
        # Level 1: Strong exact identifiers
        if p.doi and p.doi in self.doi_map:
            return self.doi_map[p.doi]
        if p.pmcid and p.pmcid.upper() in self.pmcid_map:
            return self.pmcid_map[p.pmcid.upper()]
        if p.pmid and p.pmid in self.pmid_map:
            return self.pmid_map[p.pmid]
        if p.arxiv_id and p.arxiv_id in self.arxiv_map:
            return self.arxiv_map[p.arxiv_id]

        # Level 2: Title matching with strict bibliographic corroboration (Constraint 4)
        th = get_title_hash(p.title)
        if th and th in self.title_map:
            for candidate in self.title_map[th]:
                if have_bibliographic_corroboration(p, candidate):
                    return candidate

        return None

    def _index_paper(self, p: CanonicalPaper):
        if p.doi:
            self.doi_map[p.doi] = p
        if p.pmcid:
            self.pmcid_map[p.pmcid.upper()] = p
        if p.pmid:
            self.pmid_map[p.pmid] = p
        if p.arxiv_id:
            self.arxiv_map[p.arxiv_id] = p
        th = get_title_hash(p.title)
        if th and len(p.title.strip()) >= 10:
            if th not in self.title_map:
                self.title_map[th] = []
            if p not in self.title_map[th]:
                self.title_map[th].append(p)

    def get_all(self) -> List[CanonicalPaper]:
        return self.papers

    def get_all_papers(self) -> List[CanonicalPaper]:
        return self.papers

    def __len__(self) -> int:
        return len(self.papers)
