# -*- coding: utf-8 -*-
"""
Standardized Academic Provider Integrations for Knowledge Ocean.
Normalizes all provider responses directly into CanonicalPaper instances.
Supports exact DOI routing, pagination, and circuit breaker resilience.
"""

import re
import hashlib
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

from models import CanonicalPaper, is_preprint_record
from identifiers import normalize_doi, extract_doi, is_doi_query
from network import (
    CANCELLED_TASKS,
    safe_get, UNPAYWALL_EMAIL, SEMANTIC_SCHOLAR_API_KEY,
    GOOGLE_API_KEY, ELSEVIER_API_KEY, CORE_API_KEY
)

log = logging.getLogger("AcademicAPI")

def is_task_cancelled(task_id: str) -> bool:
    return bool(task_id and task_id in CANCELLED_TASKS)


def extract_crossref_authors(i: dict) -> List[str]:
    raw_authors = i.get("author") or []
    if not raw_authors:
        # Fallback to editor if author list is empty (e.g., books, collections)
        raw_authors = i.get("editor") or []
    names = []
    for a in raw_authors:
        if not isinstance(a, dict):
            continue
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = (a.get("name") or a.get("literal") or "").strip()
        full = f"{given} {family}".strip() if (given or family) else name
        if full and full.lower() not in ("unknown", "unknown authors", "et al", "et al."):
            names.append(full)
    return names

def extract_crossref_year(i: dict) -> str:
    for field in ("issued", "published-print", "published-online", "published", "created", "deposited"):
        dp = i.get(field, {}).get("date-parts", [])
        if dp and isinstance(dp, list) and len(dp) > 0 and isinstance(dp[0], (list, tuple)) and len(dp[0]) > 0:
            val = dp[0][0]
            if val and str(val).isdigit() and len(str(val)) == 4:
                return str(val)
    return "0000"


def fetch_crossref_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None

    include_ppr = state.get('include_preprint', True)

    # P0.2: Exact DOI Lookup Route
    if doi_query and state.get('offset', 0) == 0:
        try:
            res = safe_get('crossref', f"https://api.crossref.org/works/{doi_query}", task_id, is_guest, params={"mailto": UNPAYWALL_EMAIL}, timeout=8)
            if res and res.status_code == 200:
                i = res.json().get("message", {})
                title_list = i.get("title", [])
                title = title_list[0] if title_list else "No Title"
                year = extract_crossref_year(i)
                container = i.get("container-title") or [""]
                authors = extract_crossref_authors(i)
                raw_type = i.get("type")
                publisher_str = i.get("publisher", "")
                journal_str = container[0] if container else ""
                is_ppr = (raw_type == "posted-content" or i.get("subtype") == "preprint" or is_preprint_record(doi=i.get("DOI"), journal=journal_str, title=title, raw_type=raw_type, publisher=publisher_str))
                if not include_ppr and is_ppr:
                    state['exhausted'] = True
                    return []
                papers.append(CanonicalPaper(
                    doi=i.get("DOI"),
                    title=title,
                    abstract=i.get("abstract", ""),
                    year=year,
                    authors=authors,
                    journal=journal_str,
                    publisher=publisher_str,
                    raw_type=raw_type,
                    is_preprint=is_ppr,
                    sources=["crossref"],
                    field_provenance={"doi": "crossref", "title": "crossref"}
                ))
            state['exhausted'] = True
            return papers
        except Exception as e:
            log.warning(f"CrossRef exact DOI error: {e}")
            state['exhausted'] = True
            return []

    # Standard Search Route
    if mode == "exact" and not clean_k.startswith('"'):
        clean_k = f'"{clean_k}"'
    params = {"rows": batch_size, "offset": state.get('offset', 0), "sort": "relevance", "mailto": UNPAYWALL_EMAIL}
    if mode == "author":
        params["query.author"] = clean_k.replace('"', '')
        if affiliation:
            params["query.affiliation"] = affiliation
    else:
        params["query"] = clean_k

    try:
        res = safe_get('crossref', "https://api.crossref.org/works", task_id, is_guest, params=params, timeout=8)
        if res and res.status_code == 200:
            items = res.json().get("message", {}).get("items", [])
            for i in items:
                title_list = i.get("title", [])
                title = title_list[0] if title_list else "No Title"
                year = extract_crossref_year(i)
                container = i.get("container-title") or [""]
                authors = extract_crossref_authors(i)
                raw_type = i.get("type")
                publisher_str = i.get("publisher", "")
                journal_str = container[0] if container else ""
                is_ppr = (raw_type == "posted-content" or i.get("subtype") == "preprint" or is_preprint_record(doi=i.get("DOI"), journal=journal_str, title=title, raw_type=raw_type, publisher=publisher_str))
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=i.get("DOI"),
                    title=title,
                    abstract=i.get("abstract", ""),
                    year=year,
                    authors=authors,
                    journal=journal_str,
                    publisher=publisher_str,
                    raw_type=raw_type,
                    is_preprint=is_ppr,
                    sources=["crossref"],
                    field_provenance={"doi": "crossref", "title": "crossref"}
                ))
            state['offset'] = state.get('offset', 0) + len(items)
            if len(items) < batch_size or state['offset'] >= 10000:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"CrossRef error: {e}")
        state['exhausted'] = True
    return papers


def fetch_pubmed_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None

    if doi_query:
        term = f"{doi_query}[LocationID]"
    elif mode == "author":
        clean_author = clean_k.replace('"', '')
        term = f"{clean_author}[Author]"
        if affiliation:
            term += f" AND {affiliation}[Affiliation]"
    elif mode == "exact" and not clean_k.startswith('"'):
        term = f'"{clean_k}"[Title/Abstract]'
    else:
        term = clean_k

    try:
        if state.get('pmids') is None:
            want_ids = min(500, max(batch_size * 4, 60))
            es = safe_get('pubmed', "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", task_id, is_guest,
                          params={"db": "pubmed", "term": term, "retmax": want_ids, "retstart": 0, "retmode": "json", "tool": "KnowledgeOcean", "email": UNPAYWALL_EMAIL}, timeout=8)
            if es and es.status_code == 200:
                ids = es.json().get("esearchresult", {}).get("idlist", [])
                state['pmids'] = ids
                state['idx'] = 0
            else:
                state['pmids'] = []
                state['exhausted'] = True
                return []

        ids = state.get('pmids', [])
        idx = state.get('idx', 0)
        chunk = ids[idx:idx + batch_size]
        if not chunk:
            state['exhausted'] = True
            return []

        ef = safe_get('pubmed', "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", task_id, is_guest,
                      params={"db": "pubmed", "id": ",".join(chunk), "rettype": "abstract", "retmode": "xml", "tool": "KnowledgeOcean", "email": UNPAYWALL_EMAIL}, timeout=10)
        if ef and ef.status_code == 200:
            root = ET.fromstring(ef.content)
            for art in root.findall('.//PubmedArticle'):
                t_el = art.find('.//ArticleTitle')
                title = ''.join(t_el.itertext()).strip() if t_el is not None else "No Title"
                abs_parts = [f"{a.get('Label', '')}: {''.join(a.itertext()).strip()}" if a.get('Label', '') else ''.join(a.itertext()).strip() for a in art.findall('.//AbstractText') if ''.join(a.itertext()).strip()]
                abs_text = " ".join(abs_parts) if abs_parts else ""
                year = art.findtext('.//PubDate/Year', '0000')
                if year == '0000':
                    m = re.search(r'(\d{4})', art.findtext('.//PubDate/MedlineDate', '') or '')
                    if m:
                        year = m.group(1)
                authors = [f"{a.findtext('ForeName', '')} {a.findtext('LastName', '')}".strip() for a in art.findall('.//AuthorList/Author') if f"{a.findtext('ForeName', '')} {a.findtext('LastName', '')}".strip()]
                pmc = next((aid.text for aid in art.findall('.//PubmedData/ArticleIdList/ArticleId') if aid.get('IdType') == 'pmc'), None)
                pmid = next((aid.text for aid in art.findall('.//PubmedData/ArticleIdList/ArticleId') if aid.get('IdType') == 'pubmed'), None)
                doi = next((aid.text for aid in art.findall('.//PubmedData/ArticleIdList/ArticleId') if aid.get('IdType') == 'doi'), None)
                oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}/" if pmc else ""

                pub_types = [pt.text for pt in art.findall('.//PublicationType') if pt is not None and pt.text]
                papers.append(CanonicalPaper(
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmc,
                    title=title,
                    abstract=abs_text,
                    year=year,
                    authors=authors,
                    journal=art.findtext('.//Journal/Title', ''),
                    publication_types=pub_types,
                    is_oa=bool(pmc),
                    oa_url=oa_url,
                    sources=["pubmed"],
                    field_provenance={"title": "pubmed", "abstract": "pubmed", "pmcid": "pubmed"}
                ))

        state['idx'] = idx + len(chunk)
        if state['idx'] >= len(ids):
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"PubMed batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_europepmc_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None
    include_ppr = state.get('include_preprint', True)

    if doi_query:
        query = f'DOI:"{doi_query}"'
    elif mode == "author":
        clean_author = clean_k.replace('"', '')
        query = f'AUTH:"{clean_author}"'
        if affiliation:
            query += f' AND AFFILIATIONS:"{affiliation}"'
    elif mode == "exact" and not clean_k.startswith('"'):
        query = f'"{clean_k}"'
    else:
        query = clean_k

    if not include_ppr:
        query = f"({query}) AND NOT (SRC:PPR)"

    try:
        res = safe_get('europepmc', "https://www.ebi.ac.uk/europepmc/webservices/rest/search", task_id, is_guest,
                       params={"query": query, "format": "json", "resultType": "core", "pageSize": min(100, batch_size), "cursorMark": state.get('cursor', '*')}, timeout=8)
        if res and res.status_code == 200:
            data = res.json()
            items = data.get("resultList", {}).get("result", [])
            for item in items:
                authors = [a.get("fullName") or f"{a.get('firstName', '')} {a.get('lastName', '')}".strip() for a in item.get("authorList", {}).get("author", [])]
                authors = [a for a in authors if a]
                if not authors and item.get("authorString"):
                    authors = [a.strip() for a in item["authorString"].split(",") if a.strip()]

                pmcid = item.get("pmcid")
                oa_url = f"https://europepmc.org/articles/{pmcid}" if pmcid else ""
                epmc_pub = item.get("bookOrReportDetails", {}).get("publisher") or item.get("publisher", "") or ""
                journal_title = item.get("journalInfo", {}).get("journal", {}).get("title", "")
                raw_t = item.get("pubType")
                is_ppr = (item.get("source") == "PPR" or str(raw_t or "").lower() == "preprint" or is_preprint_record(doi=item.get("doi"), journal=journal_title, title=item.get("title"), raw_type=raw_t, publisher=epmc_pub))
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=item.get("doi"),
                    pmcid=pmcid,
                    pmid=item.get("pmid"),
                    title=item.get("title", "No Title"),
                    abstract=item.get("abstractText", ""),
                    year=str(item.get("pubYear", "0000")),
                    authors=authors,
                    journal=journal_title,
                    publisher=epmc_pub,
                    raw_type=raw_t,
                    is_oa=bool(item.get("isOpenAccess") == "Y" or pmcid),
                    oa_url=oa_url,
                    citation_count=item.get("citedByCount", 0),
                    is_preprint=is_ppr,
                    sources=["europepmc"],
                    field_provenance={"title": "europepmc", "abstract": "europepmc", "oa_url": "europepmc"}
                ))
            nxt = data.get("nextCursorMark")
            if not nxt or nxt == state.get('cursor') or len(items) < min(100, batch_size):
                state['exhausted'] = True
            state['cursor'] = nxt
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"EuropePMC batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_openalex_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None
    include_ppr = state.get('include_preprint', True)

    # P0.2: Exact DOI Direct Lookup
    if doi_query and state.get('page', 1) == 1:
        try:
            res = safe_get('openalex', f"https://api.openalex.org/works/https://doi.org/{doi_query}", task_id, is_guest, params={"mailto": UNPAYWALL_EMAIL}, timeout=8)
            if res and res.status_code == 200:
                item = res.json()
                inv = item.get("abstract_inverted_index")
                abs_text = " ".join(w for _, w in sorted((pos, word) for word, poss in inv.items() for pos in poss)) if inv else ""
                authors = [a.get("author", {}).get("display_name", "").strip() for a in item.get("authorships", []) if a.get("author", {}).get("display_name", "").strip()]
                loc = item.get("primary_location") or {}
                source = (loc.get("source") or {}) if isinstance(loc, dict) else {}
                journal = source.get("display_name", "") or ""
                oa_pub = source.get("host_organization_name", "") or (item.get("host_venue") or {}).get("publisher", "") or ""
                oa = item.get("open_access") or {}
                oa_url = (oa.get("oa_url", "") or "") if isinstance(oa, dict) and oa.get("is_oa") else ""
                raw_doi = normalize_doi(item.get("doi")) or doi_query
                pub_yr = str(item.get("publication_year") or (item.get("publication_date") or "")[:4] or "0000")
                raw_t = item.get("type")
                is_ppr = (raw_t in ("preprint", "posted-content")) or is_preprint_record(doi=raw_doi, journal=journal, title=item.get("display_name") or item.get("title"), raw_type=raw_t, publisher=oa_pub)
                if not include_ppr and is_ppr:
                    state['exhausted'] = True
                    return []
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=item.get("display_name") or item.get("title", "No Title"),
                    abstract=abs_text,
                    year=pub_yr,
                    authors=authors,
                    journal=journal,
                    publisher=oa_pub,
                    raw_type=raw_t,
                    is_oa=bool(item.get("open_access", {}).get("is_oa")),
                    oa_url=oa_url,
                    citation_count=item.get("cited_by_count", 0),
                    is_preprint=is_ppr,
                    sources=["openalex"],
                    field_provenance={"doi": "openalex", "title": "openalex", "abstract": "openalex"}
                ))
            state['exhausted'] = True
            return papers
        except Exception as e:
            log.warning(f"OpenAlex exact DOI error: {e}")
            state['exhausted'] = True
            return []

    params = {"per_page": min(100, batch_size), "page": state.get('page', 1), "mailto": UNPAYWALL_EMAIL}
    if not include_ppr:
        if mode == "author":
            params["filter"] = f"type:!preprint,authorships.author.display_name.search:{clean_k.replace(chr(34), '')}"
        else:
            params["filter"] = "type:!preprint"
            params["search"] = clean_k
    else:
        if mode == "author":
            params["filter"] = f"authorships.author.display_name.search:{clean_k.replace(chr(34), '')}"
        else:
            params["search"] = clean_k

    try:
        res = safe_get('openalex', "https://api.openalex.org/works", task_id, is_guest, params=params, timeout=8)
        if res and res.status_code == 200:
            results = res.json().get("results", [])
            for item in results:
                inv = item.get("abstract_inverted_index")
                abs_text = " ".join(w for _, w in sorted((pos, word) for word, poss in inv.items() for pos in poss)) if inv else ""
                authors = [a.get("author", {}).get("display_name", "").strip() for a in item.get("authorships", []) if a.get("author", {}).get("display_name", "").strip()]
                loc = item.get("primary_location") or {}
                source = (loc.get("source") or {}) if isinstance(loc, dict) else {}
                journal = source.get("display_name", "") or ""
                oa_pub = source.get("host_organization_name", "") or (item.get("host_venue") or {}).get("publisher", "") or ""
                oa = item.get("open_access") or {}
                oa_url = (oa.get("oa_url", "") or "") if isinstance(oa, dict) and oa.get("is_oa") else ""
                raw_doi = normalize_doi(item.get("doi"))
                pub_yr = str(item.get("publication_year") or (item.get("publication_date") or "")[:4] or "0000")
                raw_t = item.get("type")
                is_ppr = (raw_t in ("preprint", "posted-content")) or is_preprint_record(doi=raw_doi, journal=journal, title=item.get("display_name") or item.get("title"), raw_type=raw_t, publisher=oa_pub)
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=item.get("display_name") or item.get("title", "No Title"),
                    abstract=abs_text,
                    year=pub_yr,
                    authors=authors,
                    journal=journal,
                    publisher=oa_pub,
                    raw_type=raw_t,
                    is_oa=bool(item.get("open_access", {}).get("is_oa")),
                    oa_url=oa_url,
                    citation_count=item.get("cited_by_count", 0),
                    is_preprint=is_ppr,
                    sources=["openalex"],
                    field_provenance={"doi": "openalex", "title": "openalex", "abstract": "openalex"}
                ))
            state['page'] = state.get('page', 1) + 1
            if len(results) < min(100, batch_size) or state['page'] * 100 >= 10000:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"OpenAlex batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_doaj_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None

    if doi_query:
        q = f'bibjson.identifier.id:"{doi_query}"'
    elif mode == "author":
        q = f"bibjson.author.name:{clean_k.replace(chr(34), '')}"
    elif mode == "exact" and not clean_k.startswith('"'):
        q = f'"{clean_k}"'
    else:
        q = clean_k

    try:
        res = safe_get('doaj', f"https://doaj.org/api/search/articles/{q}", task_id, is_guest, params={"page": state.get('page', 1), "pageSize": min(100, batch_size)}, timeout=8)
        if res and res.status_code == 200:
            results = res.json().get("results", [])
            for item in results:
                bib = item.get("bibjson", {})
                doi = next((ident.get("id") for ident in bib.get("identifier", []) if ident.get("type") == "doi"), None)
                oa_url = next((link.get("url") for link in bib.get("link", []) if link.get("type") == "fulltext"), "")
                doaj_pub = (bib.get("publisher") or {}).get("name", "") or (bib.get("journal") or {}).get("publisher", "") or ""
                papers.append(CanonicalPaper(
                    doi=doi,
                    title=bib.get("title", "No Title"),
                    abstract=bib.get("abstract", ""),
                    year=str(bib.get("year", "0000")),
                    authors=[a["name"] for a in bib.get("author", []) if a.get("name")],
                    journal=bib.get("journal", {}).get("title", ""),
                    publisher=doaj_pub,
                    is_oa=True,
                    oa_url=oa_url,
                    sources=["doaj"],
                    field_provenance={"doi": "doaj", "title": "doaj", "abstract": "doaj"}
                ))
            state['page'] = state.get('page', 1) + 1
            if len(results) < min(100, batch_size):
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"DOAJ batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_arxiv_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    if mode == "exact" and not clean_k.startswith('"'):
        clean_k = f'"{clean_k}"'
    sq = f"au:{clean_k.replace(chr(34), '')}" if mode == "author" else f"all:{clean_k}"
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
    try:
        res = safe_get('arxiv', "http://export.arxiv.org/api/query", task_id, is_guest,
                       params={"search_query": sq, "start": state.get('offset', 0), "max_results": min(100, batch_size), "sortBy": "relevance"}, timeout=12)
        if res and res.status_code == 200:
            root = ET.fromstring(res.content)
            entries = root.findall('atom:entry', ns)
            for entry in entries:
                doi_el = entry.find('arxiv:doi', ns)
                aid = entry.findtext('atom:id', '', ns)
                pdf_url = f"https://arxiv.org/pdf/{aid.replace('http://arxiv.org/abs/', '').replace('https://arxiv.org/abs/', '')}" if aid else ""
                papers.append(CanonicalPaper(
                    doi=doi_el.text.strip() if doi_el is not None and doi_el.text else None,
                    arxiv_id=aid,
                    title=entry.findtext('atom:title', 'No Title', ns).strip().replace('\n', ' '),
                    abstract=entry.findtext('atom:summary', '', ns).strip().replace('\n', ' '),
                    year=(entry.findtext('atom:published', '', ns)[:4] or '0000'),
                    authors=[a.findtext('atom:name', '', ns).strip() for a in entry.findall('atom:author', ns) if a.findtext('atom:name', '', ns).strip()],
                    journal="arXiv (Preprint)",
                    publisher="arXiv",
                    is_preprint=True,
                    is_oa=True,
                    oa_url=pdf_url,
                    sources=["arxiv"],
                    field_provenance={"title": "arxiv", "abstract": "arxiv", "oa_url": "arxiv"}
                ))
            state['offset'] = state.get('offset', 0) + len(entries)
            if len(entries) < min(100, batch_size):
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"arXiv batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_zenodo_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    include_ppr = state.get('include_preprint', True)
    q = f'creators.name:"{clean_k.replace(chr(34), "")}"' if mode == "author" else clean_k
    req_size = min(50, batch_size)
    try:
        res = safe_get('zenodo', "https://zenodo.org/api/records", task_id, is_guest, params={"q": q, "size": req_size, "page": state.get('page', 1), "type": "publication", "sort": "bestmatch"}, timeout=8)
        if res and res.status_code == 200:
            hits = (res.json().get("hits") or {}).get("hits") or []
            for it in hits:
                md = it.get("metadata") or {}
                oa_url = ""
                for fobj in (it.get("files") or []):
                    link = (fobj.get("links") or {}).get("self", "") or fobj.get("links", {}).get("download", "")
                    if link:
                        oa_url = link
                        if str(fobj.get("key", "")).lower().endswith(".pdf"):
                            break
                if not oa_url:
                    oa_url = (it.get("links") or {}).get("self_html", "") or ""
                zenodo_pub = md.get("publisher") or "Zenodo"
                raw_doi = it.get("doi") or md.get("doi")
                pub_title = md.get("title", "No Title")
                journal_title = (md.get("journal") or {}).get("title", "") or "Zenodo"
                raw_t = (md.get("publication_type") or md.get("upload_type") or "").lower()
                is_ppr = is_preprint_record(doi=raw_doi, journal=journal_title, title=pub_title, raw_type=raw_t, publisher=zenodo_pub)
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=pub_title,
                    abstract=md.get("description", ""),
                    year=str(md.get("publication_date") or "")[:4] if str(md.get("publication_date") or "")[:4].isdigit() else "0000",
                    authors=[c.get("name", "").strip() for c in (md.get("creators") or []) if c.get("name")],
                    journal=journal_title,
                    publisher=zenodo_pub,
                    raw_type=raw_t,
                    is_preprint=is_ppr,
                    is_oa=bool(oa_url),
                    oa_url=oa_url,
                    sources=["zenodo"],
                    field_provenance={"doi": "zenodo", "title": "zenodo", "abstract": "zenodo"}
                ))
            state['page'] = state.get('page', 1) + 1
            if len(hits) < req_size:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"Zenodo batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_semanticscholar_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    include_ppr = state.get('include_preprint', True)
    headers = {}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    doi_query = extract_doi(clean_k) if is_doi_query(clean_k) else None
    if doi_query and state.get('offset', 0) == 0:
        try:
            s2_url = f"https://api.semanticscholar.org/graph/v1/paper/{doi_query}"
            res = safe_get('semanticscholar', s2_url, task_id, is_guest, headers=headers,
                           params={"fields": "title,abstract,year,externalIds,authors,venue,publicationVenue,openAccessPdf,citationCount,publicationTypes"}, timeout=8)
            if res and res.status_code == 200:
                item = res.json()
                oa = (item.get("openAccessPdf") or {}).get("url", "") or ""
                pub_types = item.get("publicationTypes") or []
                ext_ids = item.get("externalIds") or {}
                raw_doi = ext_ids.get("DOI") or doi_query
                authors = [a["name"].strip() for a in item.get("authors", []) if a.get("name") and a["name"].strip()]
                s2_pub = (item.get("publicationVenue") or {}).get("name", "") or ""
                raw_t = pub_types[0] if pub_types else None
                venue_str = item.get("venue", "")
                is_ppr = "Preprint" in pub_types or bool(ext_ids.get("ArXiv")) or is_preprint_record(doi=raw_doi, journal=venue_str, title=item.get("title"), raw_type=raw_t, publisher=s2_pub)
                if not include_ppr and is_ppr:
                    state['exhausted'] = True
                    return []
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=item.get("title", "No Title"),
                    abstract=item.get("abstract", ""),
                    year=str(item.get("year") or "0000"),
                    authors=authors,
                    journal=venue_str,
                    publisher=s2_pub,
                    raw_type=raw_t,
                    publication_types=pub_types,
                    is_oa=bool(oa),
                    oa_url=oa,
                    citation_count=item.get("citationCount", 0),
                    is_preprint=is_ppr,
                    sources=["semanticscholar"],
                    field_provenance={"doi": "semanticscholar", "title": "semanticscholar", "abstract": "semanticscholar"}
                ))
            state['exhausted'] = True
            return papers
        except Exception as e:
            log.warning(f"S2 exact DOI error: {e}")
            state['exhausted'] = True
            return []

    try:
        res = safe_get('semanticscholar', "https://api.semanticscholar.org/graph/v1/paper/search", task_id, is_guest,
                       headers=headers, params={"query": clean_k, "offset": state.get('offset', 0), "limit": min(100, batch_size), "fields": "title,abstract,year,externalIds,authors,venue,publicationVenue,openAccessPdf,citationCount,publicationTypes"}, timeout=10)
        if res and res.status_code == 200:
            items = res.json().get('data', [])
            for item in items:
                oa = (item.get("openAccessPdf") or {}).get("url", "") or ""
                pub_types = item.get("publicationTypes") or []
                ext_ids = item.get("externalIds") or {}
                raw_doi = ext_ids.get("DOI")
                authors = [a["name"].strip() for a in item.get("authors", []) if a.get("name") and a["name"].strip()]
                s2_pub = (item.get("publicationVenue") or {}).get("name", "") or ""
                raw_t = pub_types[0] if pub_types else None
                venue_str = item.get("venue", "")
                is_ppr = "Preprint" in pub_types or bool(ext_ids.get("ArXiv")) or is_preprint_record(doi=raw_doi, journal=venue_str, title=item.get("title"), raw_type=raw_t, publisher=s2_pub)
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=item.get("title", "No Title"),
                    abstract=item.get("abstract", ""),
                    year=str(item.get("year", "0000")),
                    authors=authors,
                    journal=venue_str,
                    publisher=s2_pub,
                    raw_type=raw_t,
                    publication_types=pub_types,
                    is_oa=bool(oa),
                    oa_url=oa,
                    citation_count=item.get("citationCount", 0),
                    is_preprint=is_ppr,
                    sources=["semanticscholar"],
                    field_provenance={"title": "semanticscholar", "abstract": "semanticscholar"}
                ))
            nxt = res.json().get("next")
            if nxt is None or state.get('offset', 0) + len(items) >= 1000 or len(items) < min(100, batch_size):
                state['exhausted'] = True
            state['offset'] = nxt or (state.get('offset', 0) + len(items))
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"S2 batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_googlebooks_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    q = f'inauthor:"{clean_k.replace(chr(34), "")}"' if mode == "author" else clean_k
    req_batch = min(40, batch_size)
    params = {"q": q, "startIndex": state.get('offset', 0), "maxResults": req_batch, "printType": "books", "filter": "free-ebooks"}
    if GOOGLE_API_KEY:
        params["key"] = GOOGLE_API_KEY

    try:
        res = safe_get('googlebooks', "https://www.googleapis.com/books/v1/volumes", task_id, is_guest,
                       params=params, timeout=8)
        if res and res.status_code == 200:
            results = res.json().get("items", [])
            for item in results:
                vol = item.get("volumeInfo", {})
                title = vol.get("title", "No Title")
                if vol.get("subtitle"):
                    title += f": {vol.get('subtitle')}"
                raw_authors = vol.get("authors", [])
                clean_auths = [a.strip() for a in raw_authors if a and a.strip()]
                papers.append(CanonicalPaper(
                    title=title,
                    abstract=vol.get("description", ""),
                    year=(vol.get("publishedDate", "")[:4] if vol.get("publishedDate", "") else "0000"),
                    authors=clean_auths,
                    journal="Book",
                    publisher=vol.get("publisher", ""),
                    raw_type="book",
                    publication_types=["Book"],
                    is_oa=True,
                    oa_url=vol.get("previewLink", ""),
                    sources=["googlebooks"],
                    field_provenance={"title": "googlebooks", "abstract": "googlebooks"}
                ))
            state['offset'] = state.get('offset', 0) + len(results)
            if len(results) < req_batch:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"Google Books batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_openlibrary_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    papers = []
    if is_task_cancelled(task_id):
        return []
    clean_k = keywords.strip()
    params = {"page": state.get('page', 1), "limit": min(100, batch_size)}
    if mode == "author":
        params["author"] = clean_k.replace('"', '')
    else:
        params["q"] = clean_k

    try:
        res = safe_get('openlibrary', "https://openlibrary.org/search.json", task_id, is_guest, params=params, timeout=8)
        if res and res.status_code == 200:
            results = res.json().get("docs", [])
            for item in results:
                title = item.get("title", "No Title")
                if item.get("subtitle"):
                    title += f": {item.get('subtitle')}"
                oa_url = f"https://openlibrary.org{item['key']}" if item.get("key") else ""
                raw_authors = item.get("author_name", [])
                clean_auths = [a.strip() for a in raw_authors if a and a.strip()]
                papers.append(CanonicalPaper(
                    title=title,
                    abstract="Open Access Free Book (Open Library)",
                    year=str(item.get("first_publish_year", "0000")),
                    authors=clean_auths,
                    journal="Book",
                    publisher="Open Library",
                    raw_type="book",
                    publication_types=["Book"],
                    is_oa=bool(oa_url),
                    oa_url=oa_url,
                    sources=["openlibrary"],
                    field_provenance={"title": "openlibrary"}
                ))
            state['page'] = state.get('page', 1) + 1
            if len(results) < min(100, batch_size):
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"OpenLibrary batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_elsevier_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int, *, api_key: Optional[str] = None) -> List[CanonicalPaper]:
    if is_task_cancelled(task_id):
        return []
    if is_guest:
        state['exhausted'] = True
        return []
    personal_key = (api_key or "").strip()
    api_key = personal_key or os.environ.get("ELSEVIER_API_KEY", "").strip() or ELSEVIER_API_KEY
    if not api_key:
        state['exhausted'] = True
        return []
    papers = []
    clean_k = keywords.strip()
    query = f'AUTH("{clean_k.replace(chr(34), "")}")' if mode == "author" else f'TITLE-ABS-KEY({clean_k})'
    if mode == "author" and affiliation:
        query += f' AND AFFIL("{affiliation}")'
    req_count = min(25, batch_size)
    try:
        res = safe_get('elsevier', "https://api.elsevier.com/content/search/scopus", task_id, is_guest,
                       headers={"X-ELS-APIKey": api_key, "Accept": "application/json"},
                       circuit_key="elsevier:" + hashlib.sha256(api_key.encode()).hexdigest() if personal_key else "elsevier",
                       params={"query": query, "count": req_count, "start": state.get('offset', 0)}, timeout=15)
        if res and res.status_code == 200:
            entries = [e for e in res.json().get("search-results", {}).get("entry", []) if 'error' not in e]
            for e in entries:
                cover = e.get("prism:coverDate", "")
                year = cover.split("-")[0] if cover else "0000"
                papers.append(CanonicalPaper(
                    doi=e.get("prism:doi"),
                    title=e.get("dc:title", "No Title"),
                    abstract=e.get("dc:description", ""),
                    year=year,
                    authors=[a.strip() for a in str(e.get("dc:creator", "")).split(',') if a.strip()],
                    journal=e.get("prism:publicationName", ""),
                    publisher="Elsevier",
                    sources=["elsevier"],
                    field_provenance={"doi": "elsevier", "title": "elsevier", "abstract": "elsevier"}
                ))
            state['offset'] = state.get('offset', 0) + len(entries)
            if len(entries) < req_count:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"Scopus batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_core_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    if is_task_cancelled(task_id):
        return []
    if not CORE_API_KEY:
        state['exhausted'] = True
        return []
    papers = []
    clean_k = keywords.strip()
    include_ppr = state.get('include_preprint', True)
    q = f'authors:"{clean_k.replace(chr(34), "")}"' if mode == "author" else clean_k
    req_size = min(50, batch_size)
    try:
        res = safe_get('core', "https://api.core.ac.uk/v3/search/works", task_id, is_guest, headers={"Authorization": f"Bearer {CORE_API_KEY}"}, params={"q": q, "limit": req_size, "offset": state.get('offset', 0)}, timeout=8)
        if res and res.status_code == 200:
            results = res.json().get("results") or []
            for it in results:
                core_pub = str(it.get("publisher", "") or "")
                raw_doi = it.get("doi")
                core_title = it.get("title", "No Title")
                is_ppr = is_preprint_record(doi=raw_doi, journal=core_pub, title=core_title, publisher=core_pub)
                if not include_ppr and is_ppr:
                    continue
                papers.append(CanonicalPaper(
                    doi=raw_doi,
                    title=core_title,
                    abstract=it.get("abstract", ""),
                    year=str(it.get("yearPublished") or "0000"),
                    authors=[a.get("name", "").strip() for a in (it.get("authors") or []) if a.get("name")],
                    journal=core_pub,
                    publisher=core_pub,
                    is_preprint=is_ppr,
                    is_oa=bool(it.get("downloadUrl")),
                    oa_url=it.get("downloadUrl") or "",
                    sources=["core"],
                    field_provenance={"doi": "core", "title": "core", "abstract": "core"}
                ))
            state['offset'] = state.get('offset', 0) + len(results)
            if len(results) < req_size:
                state['exhausted'] = True
        else:
            state['exhausted'] = True
    except Exception as e:
        log.warning(f"CORE batch error: {e}")
        state['exhausted'] = True
    return papers


def fetch_verified_batch(keywords: str, state: dict, mode: str, affiliation: str, task_id: str, is_guest: bool, batch_size: int) -> List[CanonicalPaper]:
    if is_task_cancelled(task_id):
        return []
    if state.get('exhausted'):
        return []
    papers = []
    clean_k = keywords.strip()
    include_ppr = state.get('include_preprint', True)
    try:
        from scholarly_registry import search_verified_registry, load_verified_registry
        records = search_verified_registry(clean_k, min_similarity=65.0)
        if not records:
            all_papers = load_verified_registry()
            k_low = clean_k.lower()
            for p in all_papers:
                t_low = (p.get("title") or "").lower()
                a_low = " ".join(p.get("authors") or []).lower()
                if k_low in t_low or k_low in a_low:
                    records.append(p)

        for rec in records:
            raw_doi = normalize_doi(rec.get("doi"))
            is_ppr = bool(rec.get("is_preprint", False))
            if not include_ppr and is_ppr:
                continue
            papers.append(CanonicalPaper(
                doi=raw_doi,
                title=rec.get("title", ""),
                abstract=rec.get("abstract", ""),
                year=str(rec.get("year") or "0000"),
                authors=rec.get("authors", []),
                journal=rec.get("journal", ""),
                publisher=rec.get("publisher", ""),
                is_preprint=is_ppr,
                is_oa=bool(rec.get("url") or rec.get("oa_url")),
                oa_url=rec.get("oa_url") or rec.get("url") or "",
                sources=["verified_literature"],
                field_provenance={"title": "verified_registry", "url": "verified_registry"}
            ))
    except Exception as e:
        log.warning(f"Verified registry batch error: {e}")
    state['exhausted'] = True
    return papers


FETCH_BATCH_MAP = {
    'verified_literature': fetch_verified_batch,
    'crossref': fetch_crossref_batch,
    'pubmed': fetch_pubmed_batch,
    'elsevier': fetch_elsevier_batch,
    'europepmc': fetch_europepmc_batch,
    'openalex': fetch_openalex_batch,
    'semanticscholar': fetch_semanticscholar_batch,
    'arxiv': fetch_arxiv_batch,
    'doaj': fetch_doaj_batch,
    'core': fetch_core_batch,
    'zenodo': fetch_zenodo_batch,
    'googlebooks': fetch_googlebooks_batch,
    'openlibrary': fetch_openlibrary_batch,
}
