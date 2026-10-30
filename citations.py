import re
import html
from typing import Tuple

BANNED_JOURNAL_NAMES = {'pubmed', 'ncbi', 'crossref', 'medline', 'europe pmc', 'europepmc', 'scopus', 'arxiv', 'openalex', 'semantic scholar', 'semanticscholar', 'doaj', 'core', 'zenodo', 'scienceopen', 'researchgate'}
LOWERCASE_WORDS = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'with', 'in', 'of', 'via', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'under'}

def clean_journal_name(journal: str) -> str:
    if not journal: return ""
    j = journal.strip()
    return "" if j.lower() in BANNED_JOURNAL_NAMES else j

def clean_title_for_citation(title: str) -> str:
    if not title: return ""
    t = html.unescape(str(title)).strip()
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub(r'\s+', ' ', t).strip().rstrip(" .:,;–—")

def parse_author_name(author_str: str) -> Tuple[str, str]:
    s = re.sub(r'\s+', ' ', str(author_str or "")).strip()
    if not s: return ("Unknown", "")
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        return (parts[0], parts[1])
    parts = s.split(" ")
    if len(parts) == 1: return (parts[0], "")
    compound_prefixes = {"van", "der", "von", "de", "del", "della", "al", "el", "ibn", "bin"}
    idx = len(parts) - 1
    while idx > 0 and parts[idx - 1].lower().strip("-") in compound_prefixes: idx -= 1
    return (" ".join(parts[idx:]), " ".join(parts[:idx]))

def format_author_initials_apa(given_name: str) -> str:
    if not given_name: return ""
    result = []
    for tok in re.split(r'([ \-])', given_name):
        if tok in (" ", "-"): result.append(tok)
        elif tok:
            first = tok.strip(" .")[0].upper() if tok.strip(" .") else ""
            if first: result.append(f"{first}.")
    return "".join(result).strip()

def is_chemical_or_preserved_term(word: str) -> bool:
    clean_w = word.strip("(),;:.[]{}?'\"")
    if not clean_w: return False
    if any(c.isdigit() for c in clean_w) and any(c.isalpha() for c in clean_w): return True
    if len(clean_w) > 1 and clean_w.isupper(): return True
    if any(c.isupper() for c in clean_w[1:]): return True
    if re.search(r'\([IVXLCDM]+\)', word, re.IGNORECASE): return True
    if clean_w.lower() in {"iraq", "mosul", "baghdad", "pubmed", "crossref", "scopus"}: return True
    return False

def to_sentence_case(title: str) -> str:
    t = clean_title_for_citation(title)
    if not t: return ""
    processed = []
    for idx, sec in enumerate(re.split(r'([:?!]\s+)', t)):
        if idx % 2 == 1:
            processed.append(sec)
            continue
        words = sec.split(" ")
        for w_i, word in enumerate(words):
            if not word: continue
            if w_i == 0:
                if not is_chemical_or_preserved_term(word): words[w_i] = word[0].upper() + word[1:]
                continue
            if is_chemical_or_preserved_term(word): continue
            clean_token = word.strip("(),;:.[]{}?'\"")
            if clean_token.lower() in LOWERCASE_WORDS or clean_token.islower() or clean_token.istitle():
                words[w_i] = word.lower()
        processed.append(" ".join(words))
    return "".join(processed).rstrip(" .:,;–—")

def escape_bibtex_text(text: str) -> str:
    if not text: return ""
    s = text
    for char, escaped in {'&': r'\&', '%': r'\%', '_': r'\_', '#': r'\#', '$': r'\$'}.items():
        s = re.sub(r'(?<!\\)' + re.escape(char), escaped, s)
    return s

def protect_bibtex_title(title: str) -> str:
    t = escape_bibtex_text(title.strip().rstrip(" .:,;–—"))
    words = []
    for w in t.split(" "):
        clean_w = w.strip("(),;:.[]{}?'\"")
        if is_chemical_or_preserved_term(clean_w) and not (w.startswith("{") and w.endswith("}")):
            prefix, suffix = re.match(r'^[(\[{]*', w).group(0), re.search(r'[)\]}:,;.]*$', w).group(0)
            core = w[len(prefix):len(w)-len(suffix)] if (len(w)-len(suffix) >= len(prefix)) else clean_w
            words.append(f"{prefix}{{{core}}}{suffix}")
        else: words.append(w)
    return " ".join(words)

def format_apa_7th(paper: dict, bold_volume: bool = False, output_format: str = "markdown") -> str:
    formatted_authors = []
    for a in paper.get('authors') or []:
        last, given = parse_author_name(str(a))
        if last.lower() in ("unknown", "unknown authors", "et al", "et al."): continue
        ini = format_author_initials_apa(given)
        formatted_authors.append(f"{last}, {ini}" if ini else last)

    if not formatted_authors: authors_clause = "Unknown Author."
    elif len(formatted_authors) == 1: authors_clause = formatted_authors[0] if formatted_authors[0].endswith('.') else f"{formatted_authors[0]}."
    elif len(formatted_authors) <= 20: authors_clause = f"{', '.join(formatted_authors[:-1])}, & {formatted_authors[-1].rstrip('.') + '.'}"
    else: authors_clause = f"{', '.join(formatted_authors[:19])}, ... {formatted_authors[-1].rstrip('.') + '.'}"

    y_str = str(paper.get('year') or '').strip()
    year = y_str if (y_str.isdigit() and len(y_str) == 4 and y_str != "0000") else "n.d."
    title = to_sentence_case(paper.get('title') or "Untitled document")
    title_clause = title if title.endswith(('?', '!', '.')) else f"{title}."
    
    journal = clean_journal_name(paper.get('journal') or "")
    volume = str(paper.get('volume') or '').strip()
    issue = str(paper.get('issue') or paper.get('number') or '').strip()
    pages = str(paper.get('pages') or paper.get('page') or paper.get('article_number') or paper.get('article_no') or '').strip()
    doi = str(paper.get('doi') or '').strip()

    if output_format == "html":
        # Metadata is untrusted (Crossref/OpenAlex/etc.); escape before adding our HTML tags.
        authors_clause = html.escape(authors_clause, quote=True)
        year = html.escape(year, quote=True)
        title_clause = html.escape(title_clause, quote=True)
        journal = html.escape(journal, quote=True)
        volume = html.escape(volume, quote=True)
        issue = html.escape(issue, quote=True)
        pages = html.escape(pages, quote=True)
        doi = html.escape(doi, quote=True)

    if volume:
        volume = re.sub(r'^(?:vol(?:ume)?|v)?[\s.:#]*', '', volume, flags=re.IGNORECASE).strip()

    if issue:
        issue = issue.strip("()")
        issue = re.sub(r'^(?:issue|no|number|n[o°]|iss)?[\s.:#]*', '', issue, flags=re.IGNORECASE).strip()

    if pages:
        pages = re.sub(r'^(?:pp?|pages?)?[\s.:#]*', '', pages, flags=re.IGNORECASE).strip()
        pages = re.sub(r'[-–—]+', '–', pages)

    journal_clause = ""
    if journal:
        if output_format == "html":
            journal_clause = f'<i style="font-style: italic;">{journal}</i>'
            if volume:
                vol_str = f'<b style="font-weight: bold;">{volume}</b>' if bold_volume else f'<i style="font-style: italic;">{volume}</i>'
                journal_clause += f", {vol_str}"
                if issue:
                    journal_clause += f"({issue})"
            elif issue:
                journal_clause += f", ({issue})"
        elif output_format == "plain":
            journal_clause = journal
            if volume:
                journal_clause += f", {volume}"
                if issue:
                    journal_clause += f"({issue})"
            elif issue:
                journal_clause += f", ({issue})"
        else:
            journal_clause = f"*{journal}*"
            if volume:
                journal_clause += f", **{volume}**" if bold_volume else f", *{volume}*"
                if issue:
                    journal_clause += f"({issue})"
            elif issue:
                journal_clause += f", ({issue})"

        if pages:
            journal_clause += f", {pages}"
        journal_clause += "."
    elif paper.get('is_preprint'):
        if output_format == "html":
            journal_clause = f'<i style="font-style: italic;">Preprint</i>, {paper.get("publisher") or "Archive Repository"}.'
        elif output_format == "plain":
            journal_clause = f"Preprint, {paper.get('publisher') or 'Archive Repository'}."
        else:
            journal_clause = f"*Preprint*, {paper.get('publisher') or 'Archive Repository'}."
    elif paper.get('publisher'):
        journal_clause = f"{paper.get('publisher')}."

    if output_format == "html":
        doi_clause = f' <a href="https://doi.org/{doi}" style="color: #0563C1; text-decoration: underline;">https://doi.org/{doi}</a>' if (doi and doi != "N/A") else ""
        return f'<p style="font-family: \'Times New Roman\', Times, serif; font-size: 14pt; color: #000000; line-height: 1.5; margin: 0; padding: 0;">{authors_clause} ({year}). {title_clause} {journal_clause}{doi_clause}</p>'.strip()
    else:
        doi_clause = f" https://doi.org/{doi}" if (doi and doi != "N/A") else ""
        return f"{authors_clause} ({year}). {title_clause} {journal_clause}{doi_clause}".strip()

def format_apa_7th_html(paper: dict, bold_volume: bool = False) -> str:
    return format_apa_7th(paper, bold_volume=bold_volume, output_format="html")

def format_apa_7th_plain(paper: dict) -> str:
    return format_apa_7th(paper, bold_volume=False, output_format="plain")

def apa_to_html(apa_md: str) -> str:
    if not apa_md: return ""
    apa_md = html.escape(apa_md, quote=True)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b style="font-weight: bold;">\1</b>', apa_md)
    s = re.sub(r'\*(.+?)\*', r'<i style="font-style: italic;">\1</i>', s)
    s = re.sub(r'(https?://doi\.org/[^\s]+)', r'<a href="\1" style="color: #0563C1; text-decoration: underline;">\1</a>', s)
    return f'<p style="font-family: \'Times New Roman\', Times, serif; font-size: 14pt; color: #000000; line-height: 1.5; margin: 0; padding: 0;">{s}</p>'

def apa_to_plain(apa_md: str) -> str:
    if not apa_md: return ""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', apa_md)
    s = re.sub(r'\*(.+?)\*', r'\1', s)
    return s

def generate_bibtex_entry(paper: dict, index: int = 1) -> str:
    authors = paper.get('authors') or []
    cite_author = re.sub(r'[^a-zA-Z0-9]', '', parse_author_name(str(authors[0]))[0]).lower() if authors else "author"
    y_str = str(paper.get('year') or '').strip()
    year = y_str if (y_str.isdigit() and len(y_str) == 4 and y_str != "0000") else "2026"
    title_slug = re.sub(r'[^a-zA-Z0-9]', '', (paper.get('title') or 'paper').lower())[:8] or "paper"
    cite_key = f"{cite_author}{year}{title_slug}_{index}"
    
    entry_type = "misc" if bool(paper.get('is_preprint')) else "article"
    bib_authors = []
    for a in authors:
        last, given = parse_author_name(str(a))
        if last.lower() not in ("unknown", "unknown authors", "et al", "et al."):
            bib_authors.append(f"{last}, {given}" if given else last)
    authors_str = " and ".join(bib_authors) if bib_authors else "Unknown Authors"

    entry = [f"@{entry_type}{{{cite_key},"]
    if authors_str != "Unknown Authors": entry.append(f"  author    = {{{escape_bibtex_text(authors_str)}}},")
    entry.append(f"  title     = {{{protect_bibtex_title(paper.get('title') or 'paper')}}},")
    
    journal = clean_journal_name(paper.get('journal') or "")
    if journal: entry.append(f"  journal   = {{{escape_bibtex_text(journal)}}},")
    elif entry_type == "misc": entry.append("  howpublished = {Preprint},")
    if year != "n.d.": entry.append(f"  year      = {{{year}}},")
    if paper.get('volume'): entry.append(f"  volume    = {{{paper['volume']}}},")
    if paper.get('issue') or paper.get('number'): entry.append(f"  number    = {{{paper.get('issue') or paper.get('number')}}},")
    pg_val = paper.get('pages') or paper.get('page') or paper.get('article_number')
    if pg_val: entry.append(f"  pages     = {{{re.sub(r'[-–—]+', '--', str(pg_val))}}},")
    if paper.get('publisher'): entry.append(f"  publisher = {{{escape_bibtex_text(paper['publisher'] )}}},")
    
    doi, oa = str(paper.get('doi') or '').strip(), str(paper.get('oa_url') or '').strip()
    if doi and doi != "N/A":
        entry.append(f"  doi       = {{{doi}}},")
        entry.append(f"  url       = {{https://doi.org/{doi}}},")
    elif oa: entry.append(f"  url       = {{{oa}}},")
    
    abstract = paper.get('abstract') or ''
    if abstract and abstract != "No abstract provided in source metadata.":
        clean_abs = escape_bibtex_text(re.sub(r'[\r\n\t]+', ' ', abstract)[:600]).replace('{', '').replace('}', '')
        entry.append(f"  abstract  = {{{clean_abs}}}")
    
    if entry[-1].endswith(','): entry[-1] = entry[-1][:-1]
    entry.append("}")
    return "\n".join(entry)


def generate_ris_entry(paper: dict) -> str:
    """Generates a standard RIS citation entry for a paper."""
    lines = ["TY  - JOUR"]
    title = clean_title_for_citation(paper.get('title') or 'No Title')
    lines.append(f"TI  - {title}")
    authors = paper.get('authors') or []
    for a in authors:
        last, given = parse_author_name(str(a))
        if last.lower() not in ("unknown", "unknown authors", "et al", "et al."):
            lines.append(f"AU  - {last}, {given}" if given else f"AU  - {last}")
    journal = clean_journal_name(paper.get('journal') or "")
    if journal:
        lines.append(f"JO  - {journal}")
    y_str = str(paper.get('year') or '').strip()
    if y_str.isdigit() and len(y_str) == 4 and y_str != "0000":
        lines.append(f"PY  - {y_str}")
    if paper.get('volume'):
        lines.append(f"VL  - {paper['volume']}")
    if paper.get('issue') or paper.get('number'):
        lines.append(f"IS  - {paper.get('issue') or paper.get('number')}")
    raw_pages = str(paper.get('pages') or paper.get('page') or paper.get('article_number') or '').strip()
    if raw_pages:
        parts = re.split(r'[-–—]+', raw_pages)
        if len(parts) >= 2 and parts[0] and parts[1]:
            lines.append(f"SP  - {parts[0].strip()}")
            lines.append(f"EP  - {parts[1].strip()}")
        elif parts and parts[0]:
            lines.append(f"SP  - {parts[0].strip()}")
    doi = str(paper.get('doi') or '').strip()
    if doi and doi != "N/A":
        lines.append(f"DO  - {doi}")
        lines.append(f"UR  - https://doi.org/{doi}")
    elif paper.get('oa_url'):
        lines.append(f"UR  - {paper['oa_url']}")
    abstract = paper.get('abstract') or ''
    if abstract and abstract != "No abstract provided in source metadata.":
        clean_abs = re.sub(r'[\r\n\t]+', ' ', abstract)[:600]
        lines.append(f"AB  - {clean_abs}")
    lines.append("ER  -")
    return "\n".join(lines)
