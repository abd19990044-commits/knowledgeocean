# -*- coding: utf-8 -*-
"""
Canonical Scholarly Record Data Model for Knowledge Ocean.
Supports multi-source provenance, identifier deduplication, and lossless metadata enrichment.
Strictly preserves citation provenance by provider, links preprints to published versions,
and selects metadata based on field quality and source confidence.
"""

import re
import html
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from identifiers import normalize_doi

SOURCE_FIELD_CONFIDENCE = {
    'doi': {'crossref': 1.0, 'pubmed': 1.0, 'europepmc': 0.95, 'openalex': 0.95, 'semanticscholar': 0.90},
    'abstract': {'pubmed': 1.0, 'europepmc': 0.98, 'openalex': 0.95, 'crossref': 0.85, 'arxiv': 0.95, 'semanticscholar': 0.90},
    'title': {'crossref': 0.98, 'pubmed': 1.0, 'openalex': 0.95, 'europepmc': 0.95},
    'journal': {'crossref': 1.0, 'pubmed': 0.98, 'openalex': 0.90, 'elsevier': 0.95},
}

def evaluate_abstract_quality(text: Optional[str]) -> float:
    """Computes an objective quality score (0.0 - 1.0) for an abstract."""
    if not text:
        return 0.0
    t = text.strip()
    if t.lower() in ("no abstract provided in source metadata.", "null", "none", "") or len(t) < 25:
        return 0.0
    
    # Penalize truncation and raw markup
    penalty = 0.0
    if t.endswith('...') or t.endswith('…'):
        penalty += 0.25
    if '<jats:' in t or '<sec>' in t or '&lt;' in t:
        penalty += 0.15
    if t.lower().startswith('abstract') or t.lower().startswith('background'):
        penalty += 0.05

    # Length score: up to 1000 characters is ideal
    length_score = min(1.0, len(t) / 700.0)
    return max(0.1, length_score - penalty)


PREPRINT_DOI_PREFIXES = (
    "10.1101/",   # bioRxiv, medRxiv
    "10.21203/",  # Research Square
    "10.20944/",  # Preprints.org
    "10.26434/",  # ChemRxiv
    "10.2139/",   # SSRN
    "10.48550/",  # arXiv
    "10.31219/",  # OSF Preprints
    "10.31222/",  # MetaArXiv
    "10.31223/",  # EarthArXiv
    "10.31224/",  # EngrXiv
    "10.31234/",  # PsyArXiv
    "10.31235/",  # SocArXiv
    "10.36227/",  # TechRxiv
    "10.22541/",  # Authorea
    "10.14293/",  # ScienceOpen
    "10.7287/",   # PeerJ Preprints
    "10.5281/zenodo.",  # Zenodo uploads
    "10.6084/m9.figshare.", # Figshare uploads
    "10.1590/scielopreprints", # SciELO Preprints
    "10.32388/",  # Qeios
    "10.2196/preprints", # JMIR Preprints
)

PREPRINT_VENUES = (
    "arxiv",
    "biorxiv",
    "medrxiv",
    "chemrxiv",
    "research square",
    "ssrn",
    "preprints.org",
    "techrxiv",
    "engrxiv",
    "psyarxiv",
    "socarxiv",
    "authorea",
    "scielo preprints",
    "osf preprints",
    "repec",
    "research papers in economics",
    "zenodo",
    "figshare",
    "peerj preprints",
    "cambridge open engage",
    "beilstein archives",
    "jmir preprints",
    "ecoevorxiv",
    "agrirxiv",
    "biohackrxiv",
    "edarxiv",
    "mindrxiv",
    "sportrxiv",
    "paleorxiv",
    "fics",
    "vixra",
    "qeios",
    "openrxiv",
)

PREPRINT_PUBLISHERS = (
    "cold spring harbor laboratory",
    "research square",
    "preprints.org",
    "mdpi preprints",
    "center for open science",
    "osf",
    "osf preprints",
    "social science research network",
    "ssrn",
    "authorea",
    "chemrxiv",
    "techrxiv",
    "zenodo",
    "figshare",
    "peerj preprints",
    "cambridge open engage",
    "beilstein archives",
    "arxiv",
    "jmir preprints",
    "biorxiv",
    "medrxiv",
    "edarxiv",
    "biohackrxiv",
    "ecoevorxiv",
    "agrirxiv",
    "repec",
    "federal reserve bank of st. louis",
    "qeios",
    "openrxiv",
)

PEER_REVIEWED_PUBLISHERS = (
    "elsevier",
    "springer",
    "wiley",
    "oxford university press",
    "oup",
    "cambridge university press",
    "cup",
    "ieee",
    "institute of electrical and electronics engineers",
    "acm",
    "association for computing machinery",
    "taylor & francis",
    "taylor and francis",
    "informa",
    "routledge",
    "sage publications",
    "sage",
    "public library of science",
    "plos",
    "frontiers media",
    "frontiers",
    "mdpi",
    "de gruyter",
    "brill",
    "karger",
    "thieme",
    "wolters kluwer",
    "lww",
    "lippincott williams",
    "bmj",
    "the lancet",
    "cell press",
    "nature publishing",
    "nature portfolio",
    "biomed central",
    "bmc",
    "american chemical society",
    "acs publications",
    "royal society of chemistry",
    "rsc",
    "american physical society",
    "american institute of physics",
    "aip publishing",
    "institute of physics",
    "iop publishing",
    "american psychological association",
    "american medical association",
    "jama network",
    "massachusetts medical society",
    "nejm",
    "american society for microbiology",
    "national academy of sciences",
    "pnas",
    "emerald",
    "hindawi",
    "bentham",
    "world scientific",
    "ios press",
    "edp sciences",
    "iwa publishing",
    "royal society publishing",
    "american heart association",
    "american association for cancer research",
    "american association for the advancement of science",
    "aaas",
    "science",
    "american economic association",
    "american mathematical society",
    "siam",
    "asce",
    "asme",
    "aiaa",
    "optica",
    "genetics society of america",
    "embo press",
    "faseb",
)

def is_preprint_publisher(publisher: Optional[str]) -> bool:
    """Detects if publisher string represents a preprint archive, repository, or unreviewed working paper platform."""
    if not publisher:
        return False
    p_lower = str(publisher).strip().lower()
    if any(pp in p_lower for pp in PREPRINT_PUBLISHERS):
        return True
    if re.search(r'\b(preprint|preprints|working\s+paper|working\s+papers|open\s+archive|repository|posted\s+content|unreviewed)\b', p_lower):
        return True
    return False

def is_peer_reviewed_publisher(publisher: Optional[str]) -> bool:
    """Detects if publisher string represents an established peer-reviewed academic publisher or university press."""
    if not publisher:
        return False
    p_lower = str(publisher).strip().lower()
    if is_preprint_publisher(p_lower):
        return False
    if any(prp in p_lower for prp in PEER_REVIEWED_PUBLISHERS):
        return True
    if re.search(r'\b(university\s+press|univ\s+press|academic\s+press|publishing\s+group|scientific\s+publishing|scholarly\s+publishing)\b', p_lower):
        return True
    return False

def is_preprint_record(
    doi: Optional[str] = None,
    journal: Optional[str] = None,
    title: Optional[str] = None,
    raw_type: Optional[str] = None,
    publisher: Optional[str] = None,
    is_preprint: bool = False
) -> bool:
    """
    Robust scholarly detection for preprint vs peer-reviewed records across all bibliographic dimensions.
    Incorporates publisher authority, DOI registries, journal venues, and publication types.
    """
    if is_preprint:
        return True
    if raw_type:
        rt = raw_type.strip().lower()
        if any(tok in rt for tok in ("posted-content", "preprint", "ppr", "working-paper", "working_paper")):
            return True
    if doi:
        clean_doi = doi.strip().lower()
        if any(clean_doi.startswith(pfx) or f"/{pfx}" in clean_doi for pfx in PREPRINT_DOI_PREFIXES):
            return True
    if journal:
        j_lower = journal.strip().lower()
        if any(v in j_lower for v in PREPRINT_VENUES):
            return True
        if "preprint" in j_lower or "working paper" in j_lower:
            return True
    if publisher:
        if is_preprint_publisher(publisher):
            return True
        if is_peer_reviewed_publisher(publisher):
            return False
    if title:
        t_lower = title.strip().lower()
        if "[preprint]" in t_lower or "(preprint)" in t_lower or t_lower.startswith("preprint:") or t_lower.endswith("(preprint)") or t_lower.endswith("[preprint]"):
            return True
        if re.search(r'\b(not peer reviewed|not peer-reviewed|awaiting peer review|pre-print)\b', t_lower):
            return True
    return False


DOC_TYPE_LABELS = {
    "review": {"en": "Review Article", "ar": "مقال مرجعي / مراجعة شاملة"},
    "meta_analysis": {"en": "Meta-Analysis", "ar": "تحليل تجميعي إحصائي"},
    "book": {"en": "Book / Chapter", "ar": "كتاب / فصل في كتاب"},
    "conference": {"en": "Conference Paper", "ar": "ورقة مؤتمر علمي"},
    "research": {"en": "Original Research", "ar": "بحث علمي أصيل"},
    "preprint": {"en": "Preprint", "ar": "مسودة غير محكّمة"},
}

DOC_TYPE_PARTITIONS = {
    "review": "review",
    "meta_analysis": "review",
    "book": "book",
    "conference": "research",
    "research": "research",
    "preprint": "preprint",
}

def classify_document_type(
    doi: Optional[str] = None,
    journal: Optional[str] = None,
    title: Optional[str] = None,
    abstract: Optional[str] = None,
    raw_type: Optional[str] = None,
    publication_types: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    publisher: Optional[str] = None,
    is_preprint: bool = False
) -> str:
    """
    Robust scholarly classifier for document types across all major bibliographic dimensions.
    Relies directly on source database publication types (PubMed, Crossref, OpenAlex, Europe PMC, Semantic Scholar)
    and publisher metadata to classify into peer-reviewed vs unreviewed partitions.
    Returns one of: 'meta_analysis', 'review', 'book', 'conference', 'preprint', 'research'.
    """
    clean_t = (title or "").strip().lower()
    clean_j = (journal or "").strip().lower()
    clean_a = (abstract or "").strip().lower()
    sources_list = [s.lower() for s in (sources or [])]

    # Build normalized list of all type tags from raw_type and publication_types
    all_type_tokens: List[str] = []
    if raw_type:
        for part in re.split(r'[;,/|]', str(raw_type)):
            p = part.strip().lower()
            if p:
                all_type_tokens.append(p)
    if publication_types:
        for pt in publication_types:
            for part in re.split(r'[;,/|]', str(pt)):
                p = part.strip().lower()
                if p:
                    all_type_tokens.append(p)

    # 0. Preprint / Unreviewed (Highest Priority: preprints must never be falsely marked as peer-reviewed reviews or books)
    if is_preprint or is_preprint_publisher(publisher) or is_preprint_record(doi=doi, journal=journal, title=title, raw_type=raw_type, publisher=publisher) or any(tok in ("preprint", "posted-content", "working-paper", "ppr") for tok in all_type_tokens) or any(s in ("arxiv",) for s in sources_list):
        return "preprint"

    # 1. Meta-Analysis (Highest specificity among peer-reviewed)
    if any(re.search(r'\b(meta[-_ ]?analysis|meta[-_ ]?analytic|meta[-_ ]?analyses|meta[-_ ]?regression)\b', tok) for tok in all_type_tokens):
        return "meta_analysis"
    if re.search(r'\b(meta[- ]?analysis|meta[- ]?analytic|meta[- ]?analyses|meta[- ]?regression)\b', clean_t):
        return "meta_analysis"
    if re.search(r'\b(we conducted a meta[- ]analysis|performed a meta[- ]analysis|systematic review and meta[- ]analysis)\b', clean_a):
        return "meta_analysis"

    # 2. Review Articles / Systematic Reviews
    if any(re.search(r'\b(review|systematic[-_ ]?review|scoping[-_ ]?review|literature[-_ ]?review|critical[-_ ]?review|narrative[-_ ]?review|review[-_ ]?article|overview|integrative[-_ ]?review)\b', tok) for tok in all_type_tokens):
        return "review"
    if re.search(r'\b(systematic\s+review|scoping\s+review|literature\s+review|critical\s+review|narrative\s+review|state[- ]of[- ]the[- ]art\s+review|umbrella\s+review)\b', clean_t):
        return "review"
    if re.search(r'\b(a\s+review\s+of|an\s+overview\s+of|recent\s+advances\s+in|critical\s+overview\s+of|perspectives\s+on)\b', clean_t):
        return "review"
    if clean_t.endswith(": a review") or clean_t.endswith(" - a review") or "a systematic review" in clean_t:
        return "review"
    if any(v in clean_j for v in ("annual review", "nature reviews", "trends in", "critical reviews in", "current opinion in", "systematic reviews")):
        return "review"
    if re.search(r'\b(this|our)\s+(systematic|scoping|literature)?\s*review\s+(summarizes|aims|synthesizes|examines|provides|evaluates)\b', clean_a):
        return "review"

    # 3. Book / Book Chapter / Monographs
    if any(s in ("googlebooks", "openlibrary") for s in sources_list):
        return "book"
    if any(re.search(r'\b(book|book[-_ ]?chapter|book[-_ ]?part|monograph|edited[-_ ]?book|reference[-_ ]?book|books and documents|handbook|encyclopedia|book[-_ ]?series)\b', tok) for tok in all_type_tokens):
        return "book"
    if any(v in clean_j for v in ("handbook of", "encyclopedia of", "in book:", "book chapter")):
        return "book"

    # 4. Conference Paper
    if any(re.search(r'\b(proceedings|proceedings[-_ ]article|conference|conference[-_ ]paper|symposium|workshop)\b', tok) for tok in all_type_tokens):
        return "conference"
    if re.search(r'\b(proceedings\s+of|conference\s+on|international\s+symposium|workshop\s+on|ieee\s+conf|acm\s+conf|annual\s+meeting)\b', clean_j):
        return "conference"

    # 5. Default: Original Research Article
    return "research"

@dataclass
class CanonicalPaper:
    # Primary Identifiers
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Bibliographic fields
    title: str = "No Title"
    authors: List[str] = field(default_factory=list)
    year: str = "0000"
    journal: str = ""
    publisher: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""

    # Content
    abstract: str = ""
    is_preprint: bool = False
    is_retracted: bool = False
    raw_type: Optional[str] = None
    publication_types: List[str] = field(default_factory=list)
    doc_type: str = "research"
    doc_partition: str = "research" 

    # Linked versions (preprints <-> peer-reviewed published articles)
    linked_preprint_id: Optional[str] = None
    linked_published_id: Optional[str] = None

    # Metrics and Access
    citation_count: int = 0
    citations_by_source: Dict[str, int] = field(default_factory=dict)
    is_oa: bool = False
    oa_url: str = ""
    landing_urls: List[str] = field(default_factory=list)
    pdf_urls: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    citations: Optional[int] = None

    # Tracking, Provenance & Audit
    sources: List[str] = field(default_factory=list)
    field_provenance: Dict[str, str] = field(default_factory=dict)
    raw_records: List[Dict[str, Any]] = field(default_factory=list)
    _relevance: int = 0
    _oa_score: int = 0

    def __post_init__(self):
        if self.citations is not None and not self.citation_count:
            self.citation_count = self.citations
        if self.doi:
            self.doi = normalize_doi(self.doi)
        if not self.abstract or len(self.abstract.strip()) < 15:
            self.abstract = "No abstract provided in source metadata."
        if self.pdf_url and self.pdf_url not in self.pdf_urls:
            self.pdf_urls.append(self.pdf_url)
        if self.oa_url and self.oa_url not in self.pdf_urls:
            self.pdf_urls.append(self.oa_url)
        if not self.pdf_url and self.pdf_urls:
            self.pdf_url = self.pdf_urls[0]

        # Ensure authors list contains clean non-empty names
        if self.authors:
            self.authors = [a.strip() for a in self.authors if a and a.strip()]

        # Automatic detection of preprint status from DOI, journal, title, publisher, raw_type, or arxiv_id
        if self.arxiv_id:
            self.is_preprint = True
        elif not self.is_preprint:
            self.is_preprint = is_preprint_record(
                doi=self.doi,
                journal=self.journal,
                title=self.title,
                raw_type=self.raw_type,
                publisher=self.publisher
            )

        # Automatic classification of document type
        if self.is_preprint:
            self.doc_type = "preprint"
            self.doc_partition = "preprint"
        else:
            self.doc_type = classify_document_type(
                doi=self.doi,
                journal=self.journal,
                title=self.title,
                abstract=self.abstract,
                raw_type=self.raw_type,
                publication_types=self.publication_types,
                sources=self.sources,
                publisher=self.publisher,
                is_preprint=self.is_preprint
            )
            self.doc_partition = DOC_TYPE_PARTITIONS.get(self.doc_type, "research")

        # Record initial citation count under primary source
        if self.citation_count > 0 and self.sources:
            src = self.sources[0]
            if src not in self.citations_by_source:
                self.citations_by_source[src] = self.citation_count

    @property
    def is_peer_reviewed(self) -> bool:
        return not self.is_preprint

    @property
    def id(self) -> str:
        if self.doi:
            return f"doi:{self.doi}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.pmcid:
            return f"pmcid:{self.pmcid}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        import hashlib, re
        norm_t = re.sub(r'[^a-z0-9]', '', (self.title or "").lower())
        h = hashlib.sha256(norm_t.encode('utf-8')).hexdigest()[:16]
        return f"title:{h}"

    @property
    def has_substantive_abstract(self) -> bool:
        return bool(self.abstract and self.abstract != "No abstract provided in source metadata." and len(self.abstract.strip()) >= 30)

    def merge(self, incoming: 'CanonicalPaper') -> None:
        """
        Lossless metadata enrichment based on field quality and source confidence.
        Preserves citations by source and tracks provenance per field.
        """
        inc_src = incoming.sources[0] if incoming.sources else 'unknown'
        for src in incoming.sources:
            if src not in self.sources:
                self.sources.append(src)

        # Retain reference to incoming source record for auditability
        self.raw_records.append({
            "source": inc_src,
            "title": incoming.title,
            "doi": incoming.doi,
            "citations": incoming.citation_count
        })

        # Identifiers
        if not self.doi and incoming.doi:
            self.doi = incoming.doi
            self.field_provenance['doi'] = inc_src
        if not self.pmcid and incoming.pmcid:
            self.pmcid = incoming.pmcid
            self.field_provenance['pmcid'] = inc_src
        if not self.pmid and incoming.pmid:
            self.pmid = incoming.pmid
            self.field_provenance['pmid'] = inc_src
        if not self.arxiv_id and incoming.arxiv_id:
            self.arxiv_id = incoming.arxiv_id
            self.field_provenance['arxiv_id'] = inc_src

        # Linked versions
        if incoming.linked_preprint_id and not self.linked_preprint_id:
            self.linked_preprint_id = incoming.linked_preprint_id
        if incoming.linked_published_id and not self.linked_published_id:
            self.linked_published_id = incoming.linked_published_id

        # Quality and confidence-aware abstract merge
        curr_q = evaluate_abstract_quality(self.abstract) * SOURCE_FIELD_CONFIDENCE.get('abstract', {}).get(self.field_provenance.get('abstract', ''), 0.85)
        inc_q = evaluate_abstract_quality(incoming.abstract) * SOURCE_FIELD_CONFIDENCE.get('abstract', {}).get(inc_src, 0.85)
        if inc_q > curr_q or not self.has_substantive_abstract:
            if incoming.has_substantive_abstract:
                self.abstract = incoming.abstract
                self.field_provenance['abstract'] = inc_src

        # Title enrichment: prefer substantive titles over generic placeholders or DOI strings
        curr_title_placeholder = (not self.title or self.title in ("No Title", "Untitled") or self.title.startswith("Paper ("))
        inc_title_substantive = bool(incoming.title and incoming.title not in ("No Title", "Untitled") and not incoming.title.startswith("Paper ("))
        if curr_title_placeholder and inc_title_substantive:
            self.title = incoming.title
            self.field_provenance['title'] = inc_src

        # Authors enrichment: prefer structured, non-empty lists over generic placeholders
        def _clean_auth_list(auths):
            return [a.strip() for a in (auths or []) if a and a.strip() and a.strip().lower() not in ("unknown authors", "unknown", "et al", "et al.")]

        curr_clean_authors = _clean_auth_list(self.authors)
        inc_clean_authors = _clean_auth_list(incoming.authors)

        if not curr_clean_authors and inc_clean_authors:
            self.authors = inc_clean_authors
            self.field_provenance['authors'] = inc_src
        elif curr_clean_authors and inc_clean_authors and len(inc_clean_authors) > len(curr_clean_authors):
            self.authors = inc_clean_authors
            self.field_provenance['authors'] = inc_src
        elif not self.authors and incoming.authors:
            self.authors = inc_clean_authors or incoming.authors

        # Year enrichment: prefer valid 4-digit year over "0000" or empty
        curr_year_valid = bool(self.year and self.year != "0000" and str(self.year).isdigit() and len(str(self.year)) == 4)
        inc_year_valid = bool(incoming.year and incoming.year != "0000" and str(incoming.year).isdigit() and len(str(incoming.year)) == 4)
        if not curr_year_valid and inc_year_valid:
            self.year = incoming.year
            self.field_provenance['year'] = inc_src

        # Journal / Venue
        if not self.journal and incoming.journal:
            self.journal = incoming.journal
            self.field_provenance['journal'] = inc_src

        # Publisher enrichment: prefer verified publisher string
        if not self.publisher and incoming.publisher:
            self.publisher = incoming.publisher
            self.field_provenance['publisher'] = inc_src

        # Volume / Issue / Pages enrichment
        if not self.volume and incoming.volume:
            self.volume = incoming.volume
            self.field_provenance['volume'] = inc_src
        if not self.issue and incoming.issue:
            self.issue = incoming.issue
            self.field_provenance['issue'] = inc_src
        if not self.pages and incoming.pages:
            self.pages = incoming.pages
            self.field_provenance['pages'] = inc_src

        # Re-evaluate preprint / peer-reviewed status with enriched metadata
        incoming_is_ppr = incoming.is_preprint or is_preprint_record(
            doi=incoming.doi,
            journal=incoming.journal,
            title=incoming.title,
            raw_type=incoming.raw_type,
            publisher=incoming.publisher
        )
        if incoming_is_ppr:
            self.is_preprint = True
            self.doc_type = "preprint"
            self.doc_partition = "preprint"
        elif not self.is_preprint:
            self.is_preprint = is_preprint_record(
                doi=self.doi,
                journal=self.journal,
                title=self.title,
                raw_type=self.raw_type,
                publisher=self.publisher
            )
            if self.is_preprint:
                self.doc_type = "preprint"
                self.doc_partition = "preprint"

        # Citations: preserve provenance by provider
        for src, cnt in incoming.citations_by_source.items():
            self.citations_by_source[src] = max(self.citations_by_source.get(src, 0), cnt)
        if incoming.citation_count > 0 and incoming.sources:
            self.citations_by_source[inc_src] = max(self.citations_by_source.get(inc_src, 0), incoming.citation_count)
        
        # Overall citation_count is maximum across verified sources
        if self.citations_by_source:
            self.citation_count = max(self.citations_by_source.values())
        elif incoming.citation_count > self.citation_count:
            self.citation_count = incoming.citation_count

        # OA status and URLs
        if incoming.is_oa:
            self.is_oa = True
        if not self.oa_url and incoming.oa_url:
            self.oa_url = incoming.oa_url
            self.field_provenance['oa_url'] = inc_src

        for u in incoming.landing_urls:
            if u and u not in self.landing_urls:
                self.landing_urls.append(u)
        for u in incoming.pdf_urls:
            if u and u not in self.pdf_urls:
                self.pdf_urls.append(u)

        if not self.pdf_url and self.pdf_urls:
            self.pdf_url = self.pdf_urls[0]

        # Retraction flag
        if incoming.is_retracted:
            self.is_retracted = True

        # Merge raw_type and publication_types
        if incoming.raw_type and not self.raw_type:
            self.raw_type = incoming.raw_type
        for pt in incoming.publication_types:
            if pt not in self.publication_types:
                self.publication_types.append(pt)

        # Re-classify document type with merged metadata
        self.doc_type = classify_document_type(
            doi=self.doi,
            journal=self.journal,
            title=self.title,
            abstract=self.abstract,
            raw_type=self.raw_type,
            publication_types=self.publication_types,
            sources=self.sources,
            publisher=self.publisher,
            is_preprint=self.is_preprint
        )
        self.doc_partition = DOC_TYPE_PARTITIONS.get(self.doc_type, "research")

    def to_dict(self) -> dict:
        """
        Converts CanonicalPaper to backward-compatible dictionary with full provenance details.
        """
        return {
            "title": self.title,
            "doi": self.doi or "N/A",
            "abstract": self.abstract,
            "year": self.year,
            "authors": self.authors,
            "source_db": self.sources[0] if self.sources else "unknown",
            "sources": self.sources,
            "is_preprint": self.is_preprint,
            "linked_preprint_id": self.linked_preprint_id,
            "linked_published_id": self.linked_published_id,
            "pmcid": self.pmcid,
            "pmid": self.pmid,
            "arxiv_id": self.arxiv_id,
            "journal": self.journal,
            "publisher": self.publisher,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "is_peer_reviewed": not self.is_preprint,
            "peer_review_status": "محكم (Peer-Reviewed)" if not self.is_preprint else "غير محكم / مسودة (Preprint / Unreviewed)",
            "peer_review_status_en": "Peer-Reviewed" if not self.is_preprint else "Preprint / Unreviewed",
            "oa_url": self.oa_url,
            "pdf_url": self.pdf_url,
            "pdf_urls": self.pdf_urls,
            "citation_count": self.citation_count,
            "citations_by_source": self.citations_by_source,
            "is_retracted": self.is_retracted,
            "field_provenance": self.field_provenance,
            "_relevance": self._relevance,
            "relevance_score": self._relevance,
            "_oa_score": self._oa_score,
            "raw_type": self.raw_type,
            "publication_types": self.publication_types,
            "doc_type": self.doc_type,
            "doc_type_label": DOC_TYPE_LABELS.get(self.doc_type, {}).get("en", "Original Research"),
            "doc_type_label_ar": DOC_TYPE_LABELS.get(self.doc_type, {}).get("ar", "بحث علمي أصيل"),
            "doc_partition": self.doc_partition,
        }
