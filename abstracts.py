"""Abstract normalization and bounded, identifier-verified batch enrichment."""
import html
import re
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import requests

# Abstract fallback must not inherit the main session's hidden 5xx retries.
_HTTP = requests.Session()
_HTTP.headers["User-Agent"] = "KnowledgeOcean/1.0 (academic abstract metadata)"

MISSING_ABSTRACT = "No abstract provided in source metadata."


class _AbstractText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.split(":")[-1].lower()
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "sec", "title", "br", "div", "abstract"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.split(":")[-1].lower()
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag in ("p", "sec", "title", "div", "abstract"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize_abstract(value):
    if not isinstance(value, str):
        return ""
    text = html.unescape(value).strip()
    parser = _AbstractText()
    parser.feed(text)
    text = "".join(parser.parts)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()]
    text = "\n\n".join(line for line in lines if line)
    if text.casefold().rstrip(".") in {
        "", "null", "none", "no abstract", "abstract not available", "no abstract available",
        "no abstract provided in source metadata", "open access free book (open library)",
    }:
        return ""
    return text


def inverted_abstract(index):
    if not isinstance(index, dict):
        return ""
    positions = {}
    for word, offsets in index.items():
        if isinstance(word, str) and isinstance(offsets, list):
            for pos in offsets:
                if isinstance(pos, int) and 0 <= pos < 100000:
                    positions.setdefault(pos, word)
    return normalize_abstract(" ".join(positions[pos] for pos in sorted(positions)))


def needs_abstract(paper):
    text = normalize_abstract(paper.abstract)
    return len(text) < 30 or text.endswith(("...", "…"))


def enrich_abstracts(papers, task_id, is_guest, deadline, attempted=None):
    """At most three batch calls per round; no title-based abstract substitutions.

    Calls share the search deadline, network cooldowns and cancellation policy.
    Personal Scopus keys are never consumed by this enrichment path.
    """
    from identifiers import normalize_doi
    from models import evaluate_abstract_quality
    from network import safe_get, CANCELLED_TASKS, UNPAYWALL_EMAIL

    attempted = attempted if attempted is not None else set()
    pending = [p for p in papers if needs_abstract(p) and id(p) not in attempted and (p.doi or p.pmid)][:50]
    if not pending or task_id in CANCELLED_TASKS or time.monotonic() >= deadline:
        return 0
    attempted.update(id(p) for p in pending)
    improved = set()

    def apply(paper, text, source):
        text = normalize_abstract(text)
        if len(text) >= 30 and (not paper.has_substantive_abstract or evaluate_abstract_quality(text) > evaluate_abstract_quality(paper.abstract)):
            paper.abstract = text
            paper.field_provenance["abstract"] = source
            if source not in paper.sources:
                paper.sources.append(source)
            improved.add(id(paper))

    def request(source, url, params):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or task_id in CANCELLED_TASKS:
            return None
        return safe_get(source, url, task_id, is_guest, params=params,
                        timeout=max(0.1, min(5, remaining)), request_deadline=deadline, http_session=_HTTP)

    # Known PubMed identifiers require one EFetch call, rather than one call per paper.
    pmids = {str(p.pmid): p for p in pending if p.pmid}
    if pmids:
        try:
            res = request("pubmed", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                          {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "rettype": "abstract", "tool": "KnowledgeOcean", "email": UNPAYWALL_EMAIL})
            if res is not None and res.status_code == 200:
                for article in ET.fromstring(res.content).findall(".//PubmedArticle"):
                    paper = pmids.get(article.findtext(".//MedlineCitation/PMID", ""))
                    if paper:
                        sections = [((el.get("Label") + ": ") if el.get("Label") else "") + "".join(el.itertext()) for el in article.findall(".//Article/Abstract/AbstractText")]
                        apply(paper, "\n".join(sections), "pubmed")
        except (ValueError, ET.ParseError, TypeError):
            pass

    doi_map = {normalize_doi(p.doi): p for p in pending if p.doi and needs_abstract(p)}
    # Small DOI OR groups keep URLs within ordinary proxy limits.
    epmc_dois = list(doi_map)[:25]
    if epmc_dois:
        try:
            res = request("europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                          {"query": " OR ".join('DOI:"' + d.replace('"', '') + '"' for d in epmc_dois), "format": "json", "resultType": "core", "pageSize": 100})
            if res is not None and res.status_code == 200:
                for item in res.json().get("resultList", {}).get("result", []):
                    paper = doi_map.get(normalize_doi(item.get("doi")))
                    if paper:
                        apply(paper, item.get("abstractText"), "europepmc")
        except (ValueError, TypeError, AttributeError):
            pass

    doi_map = {normalize_doi(p.doi): p for p in pending if p.doi and needs_abstract(p)}
    if doi_map:
        try:
            res = request("openalex", "https://api.openalex.org/works",
                          {"filter": "doi:" + "|".join(list(doi_map)[:50]), "per-page": 50, "select": "doi,abstract_inverted_index", "mailto": UNPAYWALL_EMAIL})
            if res is not None and res.status_code == 200:
                for item in res.json().get("results", []):
                    paper = doi_map.get(normalize_doi(item.get("doi")))
                    if paper:
                        apply(paper, inverted_abstract(item.get("abstract_inverted_index")), "openalex")
        except (ValueError, TypeError, AttributeError):
            pass
    return len(improved)
