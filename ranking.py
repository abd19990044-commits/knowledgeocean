# -*- coding: utf-8 -*-
"""
Tuned Hybrid Academic Ranking Engine for Knowledge Ocean.
Ranks canonical scholarly records based on:
1. Exact Identifier Match (Highest priority)
2. Exact Title Match
3. Title Query Coverage
4. Abstract Query Coverage
5. Exact Phrase Matching
6. Moderate Citation Bonus (logarithmic)
7. Recency
"""

import re
import math
import html
import unicodedata
import difflib
from typing import List, Optional
from models import CanonicalPaper
from identifiers import extract_doi, is_doi_query
from query_parser import matches_boolean_query, is_explicit_boolean_query, normalize_boolean_query

def normalize_title_for_matching(t: str) -> str:
    """Normalizes a paper title by unescaping HTML, stripping tags, accents, and punctuation."""
    if not t:
        return ""
    t = html.unescape(str(t))
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.lower()
    t = unicodedata.normalize("NFKD", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def calculate_accurate_title_similarity(target_title: str, candidate_title: str) -> int:
    """Calculates a robust title match confidence score (0-100) taking order, subtitles, and token overlap into account."""
    t1 = normalize_title_for_matching(target_title)
    t2 = normalize_title_for_matching(candidate_title)
    if not t1 or not t2:
        return 0
    if t1 == t2:
        return 100

    w1 = t1.split()
    w2 = t2.split()
    if not w1 or not w2:
        return 0

    # 1. Exact main-title check (e.g., stripping subtitle by colon, dash, pipe)
    raw1_parts = re.split(r'[:\-–—|]', target_title or "", maxsplit=1)
    raw2_parts = re.split(r'[:\-–—|]', candidate_title or "", maxsplit=1)

    main1 = normalize_title_for_matching(raw1_parts[0])
    main2 = normalize_title_for_matching(raw2_parts[0])

    if main1 and main2:
        if main1 == t2:  # target has subtitle, candidate is exact main title
            return 98
        if t1 == main2:  # candidate has subtitle, target is exact main title
            sub_len = len(w2) - len(main2.split())
            return max(90, 97 - min(7, sub_len))
        if main1 == main2 and len(main1.split()) >= 3:
            return 95

    # 2. Token sequence similarity (strictly order-sensitive)
    token_sm = difflib.SequenceMatcher(None, w1, w2)
    token_ratio = token_sm.ratio()

    # Character sequence similarity
    char_sm = difflib.SequenceMatcher(None, t1, t2)
    char_ratio = char_sm.ratio()

    # Content words (non-stopwords) overlap and sequence
    stopwords = {'a', 'an', 'the', 'in', 'on', 'of', 'for', 'to', 'with', 'at', 'by', 'from', 'and', 'or', 'is', 'are', 'was', 'were'}
    cw1 = [w for w in w1 if w not in stopwords]
    cw2 = [w for w in w2 if w not in stopwords]

    # Normalize simple plural 's' at end of words longer than 4 chars for content matching
    def _norm_plural(w: str) -> str:
        return w[:-1] if (len(w) > 4 and w.endswith('s') and not w.endswith('ss')) else w

    cw1_norm = [_norm_plural(w) for w in cw1]
    cw2_norm = [_norm_plural(w) for w in cw2]

    if cw1 and cw2:
        cw_sm = difflib.SequenceMatcher(None, cw1_norm, cw2_norm)
        cw_ratio = cw_sm.ratio()
        cw_set1 = set(cw1_norm)
        cw_set2 = set(cw2_norm)
        missing_cw = cw_set1 - cw_set2
        cw_overlap = len(cw_set1 & cw_set2) / max(1, len(cw_set1))
    else:
        cw_ratio = token_ratio
        cw_overlap = len(set(w1) & set(w2)) / max(1, len(set(w1)))
        missing_cw = set()

    # Compute blended score with heavy weight on token ordering and content words
    base_sim = (token_ratio * 0.45) + (cw_ratio * 0.35) + (char_ratio * 0.20)

    # Substring handling with plural tolerance
    t1_norm_p = " ".join(_norm_plural(w) for w in w1)
    t2_norm_p = " ".join(_norm_plural(w) for w in w2)

    has_sub = (t1 in t2) or (t1_norm_p in t2_norm_p)
    has_rev_sub = (t2 in t1) or (t2_norm_p in t1_norm_p)

    if has_sub:
        extra_words = len(w2) - len(w1)
        if t2.startswith(t1) or t2_norm_p.startswith(t1_norm_p):
            boosted = max(base_sim, 0.95 - (extra_words * 0.025))
        elif t2.endswith(t1) or t2_norm_p.endswith(t1_norm_p):
            # Target phrase is at the end, preceded by lead-in (e.g. 'Development and validation of ...')
            boosted = max(base_sim, 0.94 - min(0.04, extra_words * 0.005))
        else:
            boosted = max(base_sim, 0.88 - (extra_words * 0.025))
        base_sim = max(base_sim, boosted)
    elif has_rev_sub:
        extra_words = len(w1) - len(w2)
        boosted = max(base_sim, 0.93 - (extra_words * 0.03))
        base_sim = max(base_sim, boosted)
    else:
        # Crucial penalty: if target has content words missing in candidate (e.g. user typed Naproxen, but paper is about Azelnidipine)
        if missing_cw:
            penalty = len(missing_cw) * 0.18
            base_sim = max(0.0, base_sim - penalty)
        elif cw_overlap >= 0.95 and len(cw1) >= 4:
            base_sim = max(base_sim, 0.90 * cw_ratio)

    return min(100, max(0, int(round(base_sim * 100))))

def extract_query_terms(query: str) -> List[str]:
    """Extracts non-operator, non-stopword search terms from query."""
    q = query.lower()
    phrases = re.findall(r'"([^"]+)"', q)
    remaining = re.sub(r'"[^"]+"', ' ', q)
    remaining = re.sub(r'[()\[\]{}:,;]', ' ', remaining)
    stopwords = {'and', 'or', 'not', 'the', 'in', 'of', 'for', 'a', 'an', 'to', 'on', 'by', 'with', 'at', 'from'}
    words = [w.strip() for w in remaining.split() if len(w.strip()) >= 2 and w.strip() not in stopwords]
    return phrases + words

def matches_target_query(query: str, title: str, abstract: str = "", require_title: bool = False, doi: Optional[str] = None) -> bool:
    """
    Evaluates whether document matches the query.
    If query is an exact DOI search, verifies DOI identifier directly.
    If query has explicit Boolean operators (AND, OR, NOT, quotes, parens), evaluates Boolean AST.
    Otherwise (natural query), checks if at least 40% of substantive terms match (or all if short).
    """
    if not query or not query.strip():
        return True

    # P0.2 & Constraint 9: Exact DOI matching takes top priority
    doi_in_q = extract_doi(query)
    if doi_in_q and is_doi_query(query):
        if doi and doi_in_q.lower() == doi.lower():
            return True

    t_clean = (title or "").lower().strip()
    a_clean = (abstract or "").lower().strip()
    target_text = t_clean if require_title else f"{t_clean} {a_clean}"

    if not query or not query.strip():
        return True

    # If user provided Boolean operators (case-insensitive) or grouping, evaluate with Boolean parser
    norm_q = normalize_boolean_query(query)
    if is_explicit_boolean_query(norm_q):
        return matches_boolean_query(norm_q, target_text)

    # Natural Language Query handling
    terms = extract_query_terms(query)
    if not terms:
        return True

    matched = 0
    for term in terms:
        t_low = term.lower()
        if t_low in target_text:
            matched += 1
        elif len(t_low) >= 7 and t_low[:6] in target_text:
            matched += 1

    if require_title:
        # Strict Title matching: require high term coverage in title (at least 60% or all if short)
        if len(terms) <= 2:
            return matched == len(terms)
        elif len(terms) <= 4:
            return matched >= len(terms) - 1
        else:
            return (matched / len(terms)) >= 0.60

    if len(terms) <= 2:
        return matched == len(terms)
    elif len(terms) <= 4:
        return matched >= len(terms) - 1
    else:
        # Long query: require at least 3 substantive matching terms or 35% coverage
        return matched >= 3 or (matched / len(terms)) >= 0.35


def score_paper_relevance(a, b) -> int:
    """
    Computes hybrid relevance score (0 - 1000).
    Accepts (query, paper) or (paper, query).
    Exact DOI match = 1000.
    Exact Title match = 500+.
    Topical relevance = up to 300.
    Citation bonus = up to 20.
    """
    if isinstance(a, CanonicalPaper):
        paper, query = a, str(b)
    else:
        query, paper = str(a), b

    q_clean = query.strip()
    doi_in_q = extract_doi(q_clean)

    # 1. Exact DOI Identifier match -> Top Priority (1000)
    if doi_in_q and paper.doi and doi_in_q.lower() == paper.doi.lower():
        return 1000

    title_low = (paper.title or "").lower().strip()
    abstract_low = (paper.abstract or "").lower().strip()
    score = 0

    # 2. Exact / Normalized Title match (High priority +500 points)
    norm_q = normalize_title_for_matching(q_clean)
    norm_t = normalize_title_for_matching(paper.title)
    if norm_q and norm_t:
        if norm_q == norm_t:
            score += 500
        elif norm_q in norm_t or norm_t in norm_q:
            score += 350
        elif difflib.SequenceMatcher(None, norm_q, norm_t).ratio() >= 0.88:
            score += 300

    # 3. Term coverage
    terms = extract_query_terms(query)
    if terms:
        title_hits = sum(1 for t in terms if t in title_low or (len(t) >= 7 and t[:6] in title_low))
        abstract_hits = sum(1 for t in terms if t in abstract_low or (len(t) >= 7 and t[:6] in abstract_low))

        # Title coverage is weighted heavily (up to 120 pts)
        title_ratio = title_hits / len(terms)
        score += int(title_ratio * 120)

        # Abstract coverage (up to 60 pts)
        abstract_ratio = abstract_hits / len(terms)
        score += int(abstract_ratio * 60)

        # Complete coverage bonus
        if title_hits == len(terms):
            score += 80
        elif (title_hits + abstract_hits) >= len(terms):
            score += 40

    # 4. Moderate citation tie-breaker bonus (logarithmic, max 15 points)
    # Does not displace higher topical relevance
    if paper.citation_count > 0:
        score += min(15, int(math.log1p(paper.citation_count) * 2.0))

    # 5. Recency tie-breaker bonus (max 5 points)
    if str(paper.year).isdigit() and len(str(paper.year)) == 4:
        y = int(paper.year)
        if y >= 2020:
            score += min(5, (y - 2019))

    return max(0, score)


def compute_oa_score(paper: CanonicalPaper) -> int:
    """
    Independent accessibility score (0 - 100).
    Decoupled from topical relevance to prevent boosting irrelevant papers.
    """
    if paper.pdf_urls or paper.pdf_url:
        return 100
    if paper.is_oa or paper.oa_url:
        return 60
    return 0


def rank_papers(papers: List[CanonicalPaper], query: str, max_results: int = 50) -> List[CanonicalPaper]:
    """
    Ranks papers primarily by topical relevance score.
    Uses OA accessibility score and citations strictly as tie-breakers.
    """
    for p in papers:
        p._relevance = score_paper_relevance(query, p)
        p._oa_score = compute_oa_score(p)

    sorted_papers = sorted(
        papers,
        key=lambda p: (
            p._relevance,
            p._oa_score,
            p.citation_count,
            int(p.year) if str(p.year).isdigit() else 0
        ),
        reverse=True
    )
    return sorted_papers[:max_results]


def rank_and_deduplicate(papers: List[CanonicalPaper], query: str, max_results: int = 50) -> List[CanonicalPaper]:
    """Alias for rank_papers that scores and ranks paper results."""
    return rank_papers(papers, query, max_results)

def matches_doc_type_filter(paper_dict_or_obj, doc_type_filter: str) -> bool:
    """
    Checks whether a paper matches the requested document type filter.
    Options:
    - 'all': matches all documents
    - 'review': matches reviews and meta-analyses
    - 'meta_analysis': matches meta-analyses only
    - 'research': matches original research and journal articles
    - 'book': matches books and book chapters
    - 'conference': matches conference proceedings and symposium papers
    """
    if not doc_type_filter or doc_type_filter.lower() in ("all", "any", ""):
        return True
    
    dt = getattr(paper_dict_or_obj, "doc_type", None) or (paper_dict_or_obj.get("doc_type") if isinstance(paper_dict_or_obj, dict) else "")
    part = getattr(paper_dict_or_obj, "doc_partition", None) or (paper_dict_or_obj.get("doc_partition") if isinstance(paper_dict_or_obj, dict) else "")
    
    req = doc_type_filter.lower().strip()
    if req == "review":
        return dt in ("review", "meta_analysis") or part == "review"
    if req == "meta_analysis":
        return dt == "meta_analysis"
    if req in ("book", "books", "book_chapter"):
        return dt == "book" or part == "book"
    if req in ("research", "journal_article", "article"):
        return dt in ("research", "conference") or part == "research"
    if req in ("conference", "proceedings"):
        return dt == "conference"
    return dt == req


def matches_search_scope(paper_dict_or_obj, search_scope: str) -> bool:
    """
    Filters papers based on broad publication scope:
    - 'all': comprehensive (both research papers and books)
    - 'papers': academic research papers only (excludes standalone books)
    - 'books': books and book chapters only
    """
    if not search_scope or search_scope.lower() in ("all", "comprehensive", ""):
        return True
    
    scope = search_scope.lower().strip()
    dt = getattr(paper_dict_or_obj, "doc_type", None) or (paper_dict_or_obj.get("doc_type") if isinstance(paper_dict_or_obj, dict) else "")
    part = getattr(paper_dict_or_obj, "doc_partition", None) or (paper_dict_or_obj.get("doc_partition") if isinstance(paper_dict_or_obj, dict) else "")
    sources = getattr(paper_dict_or_obj, "sources", None) or (paper_dict_or_obj.get("sources") if isinstance(paper_dict_or_obj, dict) else [])
    sources_set = set(str(s).lower() for s in (sources or []))

    if scope in ("books", "book"):
        return dt == "book" or part == "book" or bool(sources_set & {"googlebooks", "openlibrary"})
    if scope in ("papers", "research"):
        # Exclude standalone books / book repositories
        if dt == "book" or part == "book" or bool(sources_set & {"googlebooks", "openlibrary"}):
            return False
        return True
    return True

