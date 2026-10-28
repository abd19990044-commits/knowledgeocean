# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
 🌊 Knowledge Ocean — Advanced Academic Explorer v1.0 (Canonical Edition)
═══════════════════════════════════════════════════════════════════════════
 • استرجاع أكاديمي موحد متعدد المصادر (Unified Multi-Source Academic Retrieval)
 • كشف وتوجيه فوري لمعرفات الـ DOI بدقة 100% (Exact DOI Routing)
 • محلل استعلامات بولياني متقدم (Boolean Query Parser: AND, OR, NOT, Groups)
 • دمج السجلات الوصفي دون فقدان للملخصات (Lossless Metadata Enrichment)
 • حماية واستقرار ضد معدلات الحظر (HTTP 429 Resilience & Circuit Breaker)
 • قاعدة بيانات خفيفة لحفظ المهام والاستخدام (SQLite Persistence)
 • تنظيف تلقائي للملفات بعد 48 ساعة
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import re
import time
import uuid
import json
from typing import Optional, List, Dict, Any, Union, Tuple, Set
import html
import shutil
import zipfile
import hashlib
import logging
import threading
import hmac
import unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shlex
import difflib
import urllib.parse
import requests
import xml.etree.ElementTree as ET

from fastapi import FastAPI, Form, Request, HTTPException
from access_control import issue_session, revoke_session, session_owner, require_owner, require_same_origin
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# Modular components
from citations import (
    format_apa_7th, format_apa_7th_html, format_apa_7th_plain,
    apa_to_html, apa_to_plain,
    generate_bibtex_entry, generate_ris_entry,
    clean_title_for_citation, clean_journal_name
)
from identifiers import normalize_doi, extract_doi, is_doi_query
from query_parser import matches_boolean_query, is_explicit_boolean_query, normalize_boolean_query
from models import CanonicalPaper, is_preprint_record
from dedup import ScholarlyPaperIndex, is_banned_publication
from ranking import matches_target_query, score_paper_relevance, normalize_title_for_matching, calculate_accurate_title_similarity, matches_doc_type_filter, matches_search_scope
from scholarly_registry import search_verified_registry, format_strict_apa_7th
from config_loader import load_local_config, kill_port_occupants

load_local_config()
from network import (
    HTTP, safe_get, trip_engine_circuit, is_engine_in_cooldown,
    GUESTS_CAN_RUN, CANCELLED_TASKS, TASKS, TASKS_LOCK,
    UNPAYWALL_EMAIL, SEMANTIC_SCHOLAR_API_KEY, GOOGLE_API_KEY,
    ELSEVIER_API_KEY, CORE_API_KEY
)
from providers import FETCH_BATCH_MAP, extract_crossref_authors, extract_crossref_year
from database import (
    init_db, db_set_task, db_get_task, db_check_rate_limit,
    db_get_remaining_quota, db_reset_quota, db_refund_quota,
    db_get_tasks_for_guest, get_baghdad_today, get_baghdad_now,
    db_cleanup_old_usage, BAGHDAD_TZ,
    db_check_ip_ban, db_record_auth_attempt, db_reset_ip_ban
)

# ─────────────────────────────────────────────────────────────────────────
# الإعدادات والثوابت
# ─────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("AcademicAPI")
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

RAW_PASSWORDS = os.environ.get("APP_PASSWORD", "").strip()
if not RAW_PASSWORDS:
    APP_PASSWORDS = set()
    log.warning("APP_PASSWORD not configured: VIP access and Scopus searches are disabled until a secret is set.")
else:
    APP_PASSWORDS = {p for p in re.split(r"[,،;؛\r\n]+", RAW_PASSWORDS) if (p := p.strip())}

# Secondary auto-renewing password (other_password) allowing 250 daily quota in standard queue
DEFAULT_OTHER_PASSWORDS = set()  # Legacy constant: no built-in secondary access codes
RAW_OTHER_PASSWORDS = os.environ.get("OTHER_PASSWORD", "").strip() or os.environ.get("OTHER_PASUARD", "").strip()
if not RAW_OTHER_PASSWORDS:
    OTHER_PASSWORDS = set()
else:
    OTHER_PASSWORDS = {p for p in re.split(r"[,،;؛\r\n]+", RAW_OTHER_PASSWORDS) if (p := p.strip())}

def verify_password(pwd: str) -> bool:
    """Safe constant-time password verification strictly prioritizing secrets over default 123."""
    if not pwd:
        return False
    raw_passwords = os.environ.get("APP_PASSWORD", "").strip()
    if raw_passwords:
        passwords = {p for p in re.split(r"[,،;؛\r\n]+", raw_passwords) if (p := p.strip())}
    else:
        passwords = set()
    clean_pwd = pwd.strip().encode('utf-8')
    return any(hmac.compare_digest(clean_pwd, p.encode('utf-8')) for p in passwords)

def verify_other_password(pwd: str) -> bool:
    """Verifies secondary auto-renewing password (OTHER_PASSWORD) granting 250 daily quota in standard queue."""
    if not pwd:
        return False
    clean_pwd = pwd.strip().encode('utf-8')
    return any(hmac.compare_digest(clean_pwd, p.encode('utf-8')) for p in OTHER_PASSWORDS)

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
FONT_DIR = os.environ.get("FONT_DIR", "fonts")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

FILE_TTL_SECONDS = 48 * 3600

from starlette.middleware.gzip import GZipMiddleware

class CachedStaticFiles(StaticFiles):
    """Static file handler with aggressive caching for assets but no-cache for app.js so updates load immediately."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            if path.endswith("app.js") or path.endswith(".js"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            else:
                response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
        return response

app = FastAPI(title="Knowledge Ocean - Advanced Academic Explorer v1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = Jinja2Templates(directory=".")

if os.path.exists("static"):
    app.mount("/static", CachedStaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────────────────────────────────
# نظام إدارة الطابور والتحكم بالحصة المجانية
# ─────────────────────────────────────────────────────────────────────────
GUEST_QUEUE = []
ACTIVE_GUESTS = set()
QUEUE_LOCK = threading.Lock()
PREMIUM_USERS_COUNT = 0
PREMIUM_LOCK = threading.Lock()
GUEST_SEARCH_QUOTA = 50       # 50 standard searches or 25 with summaries for guests without password
SECONDARY_SEARCH_QUOTA = 250  # 250 standard searches or 125 with summaries for secondary password users, renewed daily

def get_fingerprint(request: Request):
    client_host = request.client.host if request.client else "127.0.0.1"
    # Only accept proxy-forwarded client addresses from explicitly trusted peers.
    trusted = {x.strip() for x in os.environ.get("TRUSTED_PROXY_IPS", "").split(",") if x.strip()}
    raw_ip = client_host
    if client_host in trusted:
        raw_ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for") or client_host
    ip = raw_ip.split(",")[0].strip()
    ua = request.headers.get("user-agent", "")
    al = request.headers.get("accept-language", "")
    ae = request.headers.get("accept-encoding", "")
    browser_fp = hashlib.sha256(f"{ua}_{al}_{ae}".encode('utf-8')).hexdigest()
    return ip, browser_fp

def check_guest_search_quota(ip: str, browser_fp: str, units_to_consume: int = 1, is_other: bool = False, auto_renew: bool = False, guest_token: str = "") -> tuple[bool, int]:
    """
    Checks and consumes search quota units:
    - Normal guests without password: 50 searches standard OR 25 searches with summaries daily.
    - Secondary password (other_password) holders: 250 searches standard OR 125 searches with summaries daily.
    - Both quotas automatically renew at 12:00 AM (midnight) Baghdad time (UTC+3) every day.
    - Tracked primarily by persistent guest_token and browser_fp to prevent CGNAT / shared IP lockout.
    - IP has a high safety threshold against malicious bots.
    Returns (is_limited, remaining_units).
    """
    is_sec = is_other or auto_renew
    limit = SECONDARY_SEARCH_QUOTA if is_sec else GUEST_SEARCH_QUOTA
    today = get_baghdad_today()
    prefix = "sec_" if is_sec else ""

    # High threshold IP protection against bots without locking innocent shared users
    ip_safety_limit = limit * 20
    lim_safety, _ = db_check_rate_limit(f"safety_{prefix}ip_{ip}", today, units_to_consume, ip_safety_limit)
    if lim_safety:
        return True, 0

    tok_key = f"{prefix}tok_{guest_token}" if guest_token else ""
    fp_key = f"{prefix}fp_{browser_fp}"

    if tok_key:
        # Independent browser tokens must not share a single user quota merely
        # because their User-Agent / language headers match.
        lim_tok, rem_tok = db_check_rate_limit(tok_key, today, units_to_consume, limit)
        return lim_tok, rem_tok
    else:
        lim_fp, rem_fp = db_check_rate_limit(fp_key, today, units_to_consume, limit)
        if lim_fp:
            return True, rem_fp
        return False, rem_fp

def get_guest_remaining_quota(ip: str, browser_fp: str, is_other: bool = False, guest_token: str = "") -> int:
    """Returns current remaining quota units without consuming any, based on Baghdad date."""
    today = get_baghdad_today()
    limit = SECONDARY_SEARCH_QUOTA if is_other else GUEST_SEARCH_QUOTA
    prefix = "sec_" if is_other else ""

    tok_key = f"{prefix}tok_{guest_token}" if guest_token else ""
    fp_key = f"{prefix}fp_{browser_fp}"

    if tok_key:
        return db_get_remaining_quota(tok_key, today, limit)
    else:
        return db_get_remaining_quota(fp_key, today, limit)

def refund_guest_search_quota(ip: str, browser_fp: str, refund_units: int, is_other: bool = False, guest_token: str = ""):
    """Refunds unconsumed units back to user daily quota (e.g. if fewer papers were found)."""
    if refund_units <= 0:
        return
    today = get_baghdad_today()
    prefix = "sec_" if is_other else ""
    keys = [f"{prefix}tok_{guest_token}"] if guest_token else [f"{prefix}fp_{browser_fp}"]
    db_refund_quota(keys, today, refund_units)

def is_rate_limited(ip: str, browser_fp: str, requested_units: int = 1, guest_token: str = ""):
    return check_guest_search_quota(ip, browser_fp, requested_units, guest_token=guest_token)

def _baghdad_midnight_rollover_worker():
    """
    Background daemon worker that monitors Baghdad timezone and logs daily quota renewals
    at 12:00 AM midnight (UTC+3) while maintaining clean SQLite usage records.
    """
    last_day = get_baghdad_today()
    log.info(f"🕒 Baghdad Quota Renewal Watcher active. Current Baghdad date: {last_day}")
    while True:
        try:
            time.sleep(60)
            current_day = get_baghdad_today()
            if current_day != last_day:
                log.info(f"🌅 12:00 AM Midnight reached in Baghdad ({current_day})! Daily search quotas for guests (50) and secondary passwords (250) have automatically renewed.")
                last_day = current_day
                cleaned = db_cleanup_old_usage(keep_days=7)
                if cleaned > 0:
                    log.info(f"🧹 Cleaned {cleaned} old usage records from database.")
        except Exception as e:
            log.warning(f"Error in baghdad rollover worker: {e}")
            time.sleep(60)

_rollover_thread = threading.Thread(target=_baghdad_midnight_rollover_worker, daemon=True, name="BaghdadRolloverWorker")
_rollover_thread.start()

def is_local_instance(request: Optional[Request] = None) -> bool:
    """
    Returns True if running as a local standalone deployment on user's machine,
    False if deployed to Hugging Face Spaces or public cloud.
    """
    if os.environ.get("SPACE_ID") or os.environ.get("HF_SPACE"):
        return False
    if os.environ.get("LOCAL_INSTANCE", "0") != "1" and os.environ.get("IS_LOCAL", "0") != "1":
        return False
    if os.environ.get("LOCAL_INSTANCE", "0") == "1" or os.environ.get("IS_LOCAL", "0") == "1":
        return True
    if request and request.client:
        host = request.client.host
        if host in ("127.0.0.1", "::1", "localhost", "testclient"):
            return True
    return False

tasks = TASKS

def check_rate_limit(client_ip: str, is_vip: bool = False, requested: int = 1) -> tuple[bool, int]:
    """Helper for checking rate limits; VIPs have high limit, guests have daily limit."""
    if is_vip:
        return True, 200
    limited, remaining = is_rate_limited(client_ip, "test_fp", requested)
    return not limited, remaining

CPU_CORES = os.cpu_count() or 1
_NO_CEILING = 10 ** 12
UNLIMITED_CAP = _NO_CEILING

SOURCE_PRIORITY = {
    'pubmed': 9, 'elsevier': 8, 'crossref': 7, 'europepmc': 7, 'core': 7,
    'doaj': 6, 'openalex': 5, 'semanticscholar': 4, 'zenodo': 4, 'googlebooks': 3, 'openlibrary': 2, 'arxiv': 1,
}

DB_NAMES = {
    'all': 'شامل (جميع المحركات)', 'crossref': 'CrossRef', 'elsevier': 'Scopus',
    'pubmed': 'PubMed', 'europepmc': 'Europe PMC', 'openalex': 'OpenAlex',
    'semanticscholar': 'Semantic Scholar', 'arxiv': 'arXiv', 'doaj': 'DOAJ',
    'core': 'CORE (Open Access)', 'zenodo': 'Zenodo (Open Access)',
    'googlebooks': 'Google Books', 'openlibrary': 'Open Library',
    'books': 'مكتبات الكتب (Google Books, Open Library)'
}

# ─────────────────────────────────────────────────────────────────────────
# الخطوط وأدوات النصوص
# ─────────────────────────────────────────────────────────────────────────
_AMIRI_SYS = ["/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf", "/usr/share/fonts/truetype/hosny-amiri/Amiri-Regular.ttf", "/usr/share/fonts/amiri/Amiri-Regular.ttf"]
_AMIRI_BOLD_SYS = ["/usr/share/fonts/truetype/amiri/Amiri-Bold.ttf", "/usr/share/fonts/truetype/hosny-amiri/Amiri-Bold.ttf", "/usr/share/fonts/amiri/Amiri-Bold.ttf"]
_DEJAVU_SYS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]
_DEJAVU_BOLD_SYS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]
_AMIRI_URLS = {"": "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf", "B": "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf"}
_DEJAVU_URLS = {"": "https://github.com/matplotlib/matplotlib/raw/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf", "B": "https://github.com/matplotlib/matplotlib/raw/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"}

FONT_REGULAR = FONT_BOLD = FONT_DEJA = FONT_DEJA_BOLD = None

def _first_existing(paths, min_size=50_000):
    for p in paths:
        if os.path.exists(p) and os.path.getsize(p) > min_size:
            return p
    return None

def _download_font(url, dest, min_size=50_000):
    if os.path.exists(dest) and os.path.getsize(dest) > min_size:
        return dest
    try:
        r = HTTP.get(url, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        if os.path.getsize(dest) > min_size:
            return dest
    except Exception:
        pass
    return None

def init_fonts():
    global FONT_REGULAR, FONT_BOLD, FONT_DEJA, FONT_DEJA_BOLD
    FONT_REGULAR = _first_existing(_AMIRI_SYS) or _download_font(_AMIRI_URLS[""], os.path.join(FONT_DIR, "Amiri-Regular.ttf"), 100_000)
    FONT_BOLD = _first_existing(_AMIRI_BOLD_SYS) or _download_font(_AMIRI_URLS["B"], os.path.join(FONT_DIR, "Amiri-Bold.ttf"), 100_000)
    if FONT_REGULAR and not FONT_BOLD:
        FONT_BOLD = FONT_REGULAR
    FONT_DEJA = _first_existing(_DEJAVU_SYS) or _download_font(_DEJAVU_URLS[""], os.path.join(FONT_DIR, "DejaVuSans.ttf"))
    FONT_DEJA_BOLD = _first_existing(_DEJAVU_BOLD_SYS) or _download_font(_DEJAVU_URLS["B"], os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
    if FONT_DEJA and not FONT_DEJA_BOLD:
        FONT_DEJA_BOLD = FONT_DEJA

_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
def has_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text or ""))

def rtl(text: str) -> str:
    if not text or not has_arabic(text):
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text

def clean_text(text) -> str:
    if not text:
        return ""
    text = html.unescape(str(text))
    try:
        text = unicodedata.normalize('NFKC', text)
    except Exception:
        pass
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'jats:\w+', '', text)
    for k, v in {'\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'", '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u00ad': '', '\ufeff': ''}.items():
        text = text.replace(k, v)
    text = text.replace('\r', '')
    paragraphs = text.split('\n\n')
    cleaned = [re.sub(r'\s+', ' ', p).strip() for p in paragraphs]
    return "\n\n".join(p for p in cleaned if p).strip()

def sanitize_filename(name: str) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "", str(name))
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:50] or "research"

def format_authors(authors_list, max_display=15):
    clean = [a.strip() for a in (authors_list or []) if a and a.strip() and a.strip().lower() not in ("unknown", "unknown authors", "et al", "et al.")]
    if not clean:
        return "Unknown Authors"
    if len(clean) <= max_display:
        return ", ".join(clean)
    return ", ".join(clean[:max_display]) + f" et al. (+{len(clean) - max_display})"

def user_hash_for(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()[:16]

# ─────────────────────────────────────────────────────────────────────────
# توليد المستندات
# ─────────────────────────────────────────────────────────────────────────
class AcademicPDF(FPDF):
    def __init__(self, doc_header=""):
        super().__init__(format="A4")
        self.doc_header = doc_header
        self.set_auto_page_break(auto=True, margin=18)
        global FONT_REGULAR, FONT_BOLD, FONT_DEJA, FONT_DEJA_BOLD
        if not FONT_REGULAR:
            init_fonts()
        if FONT_REGULAR:
            try:
                self.add_font("Amiri", "", FONT_REGULAR)
                self.add_font("Amiri", "B", FONT_BOLD or FONT_REGULAR)
                self.add_font("Amiri", "I", FONT_REGULAR)
                self.add_font("Amiri", "BI", FONT_BOLD or FONT_REGULAR)
                self.font_family_used = "Amiri"
            except Exception:
                self.font_family_used = "Helvetica"
        else:
            self.font_family_used = "Helvetica"

        try:
            if FONT_DEJA:
                bold = FONT_DEJA_BOLD or FONT_DEJA
                self.add_font("DejaVu", "", FONT_DEJA)
                self.add_font("DejaVu", "B", bold)
                self.add_font("DejaVu", "I", FONT_DEJA)
                self.add_font("DejaVu", "BI", bold)
                if hasattr(self, "set_fallback_fonts"):
                    self.set_fallback_fonts(["DejaVu"])
        except Exception:
            pass

        self.set_font(self.font_family_used, "", 10)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(self.font_family_used, "I" if self.font_family_used == "Amiri" else "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, rtl(self.doc_header[:100]), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font(self.font_family_used, "I" if self.font_family_used == "Amiri" else "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Page {self.page_no()} / {{nb}}", align="C")
        self.set_text_color(0, 0, 0)

    def write_block(self, text, size=10, style="", color=(0, 0, 0), align=None, h=6):
        self.set_font(self.font_family_used, style, size)
        self.set_text_color(*color)
        for para in clean_text(text).split("\n"):
            if not para.strip():
                self.ln(2)
                continue
            a = align or ("R" if has_arabic(para) else "L")
            self.multi_cell(0, h, rtl(para), align=a, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def field(self, label, value, value_color=(0, 0, 0), link=None):
        self.set_font(self.font_family_used, "B", 10)
        self.set_text_color(60, 60, 60)
        self.cell(42, 6, f"{label}:", new_x="RIGHT", new_y="TOP")
        self.set_font(self.font_family_used, "", 10)
        self.set_text_color(*value_color)
        val = clean_text(str(value))
        if link:
            self.set_font(self.font_family_used, "U", 10)
            self.multi_cell(0, 6, val, link=link, new_x="LMARGIN", new_y="NEXT")
        else:
            # Align L keeps the value directly adjacent to the label, even when containing shaped Arabic
            self.multi_cell(0, 6, rtl(val), align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)


def generate_documents(query, papers, pdf_path, md_path=None, db_source="all", doc_type="Peer-Reviewed", is_guest=False, include_abstracts=True, is_other=False):
    papers = [p.to_dict() if hasattr(p, 'to_dict') else p for p in papers]
    db_label = DB_NAMES.get(db_source, db_source)
    today = get_baghdad_today()

    doc_title_en = "ACADEMIC LITERATURE COMPILATION" if include_abstracts else "COMPREHENSIVE LITERATURE INDEX"
    doc_title_ar = "ملف مجمّع للملخصات والأبحاث — جاهز للتحليل والفهرسة" if include_abstracts else "فهرس شامل ومفصل للأوراق والكتب البحثية"
    doc_header_str = f"Knowledge Ocean - {clean_text(query)[:60]}"

    pdf = AcademicPDF(doc_header=doc_header_str)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.ln(18)
    pdf.write_block(doc_title_en, size=20, style="B", align="C")
    pdf.ln(2)
    pdf.write_block(doc_title_ar, size=12, align="C", color=(90, 90, 90))
    pdf.ln(6)
    pdf.set_draw_color(50, 50, 220)
    pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(8)

    years = [int(p['year']) for p in papers if str(p.get('year', '')).isdigit() and p['year'] != "0000"]
    
    # Partition papers into Reviews, Books, Research Articles, and Preprints
    review_papers = [p for p in papers if p.get('doc_partition') == 'review' or p.get('doc_type') in ('review', 'meta_analysis')]
    book_papers = [p for p in papers if p.get('doc_partition') == 'book' or p.get('doc_type') == 'book']
    research_papers = [p for p in papers if p not in review_papers and p not in book_papers and not p.get('is_preprint')]
    preprint_papers = [p for p in papers if p.get('is_preprint') and p not in review_papers and p not in book_papers]

    # Chronologically sort papers inside each section from newest to oldest
    def _sort_by_year_desc(p):
        y_str = str(p.get('year') or '').strip()
        if y_str.isdigit() and len(y_str) == 4 and y_str != "0000":
            return (0, -int(y_str), -int(p.get('citation_count') or 0))
        return (1, 0, -int(p.get('citation_count') or 0))

    review_papers.sort(key=_sort_by_year_desc)
    book_papers.sort(key=_sort_by_year_desc)
    research_papers.sort(key=_sort_by_year_desc)
    preprint_papers.sort(key=_sort_by_year_desc)

    pdf.field("Document Type", f"{doc_type} Structured Research Dossier")
    pdf.field("Research Topic", query)
    pdf.field("Databases / Engines", db_label)
    pdf.field("Total Records Extracted", f"{len(papers)}")
    pdf.field("Publication Years", f"{min(years)} - {max(years)}" if years else "N/A")
    pdf.field("Compiled On", today)

    pdf.ln(4)
    pdf.set_draw_color(220, 220, 240)
    pdf.set_fill_color(245, 247, 252)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, 25, "DF")
    pdf.set_y(pdf.get_y() + 2)
    pdf.write_block("DOCUMENT TYPES BREAKDOWN  ·  توزيع أصناف الوثائق الأكاديمية", size=10, style="B", color=(40, 40, 140), align="C")
    pdf.ln(1)
    
    breakdown_en = []
    breakdown_ar = []
    if review_papers:
        breakdown_en.append(f"Reviews & Meta-Analyses: {len(review_papers)}")
        breakdown_ar.append(f"مراجعات وتحليلات: {len(review_papers)}")
    if book_papers:
        breakdown_en.append(f"Books & Chapters: {len(book_papers)}")
        breakdown_ar.append(f"كتب ومراجع: {len(book_papers)}")
    if research_papers:
        breakdown_en.append(f"Original Research: {len(research_papers)}")
        breakdown_ar.append(f"أبحاث أصيلة: {len(research_papers)}")
    if preprint_papers:
        breakdown_en.append(f"Preprints: {len(preprint_papers)}")
        breakdown_ar.append(f"مسودات: {len(preprint_papers)}")
    
    b_en_str = "   ·   ".join(breakdown_en) if breakdown_en else f"Total Records: {len(papers)}"
    b_ar_str = "   ·   ".join(breakdown_ar) if breakdown_ar else f"إجمالي السجلات: {len(papers)}"
    pdf.write_block(b_en_str, size=9.5, color=(50, 50, 50), align="C")
    pdf.write_block(b_ar_str, size=9.5, color=(70, 70, 70), align="C")
    pdf.set_y(pdf.get_y() + 5)

    # Build partitioned groups with separate English and Arabic section titles and academic descriptions
    groups = []
    if review_papers:
        groups.append((
            "SECTION 1: REVIEWS & META-ANALYSES",
            "قسم المراجعات العلمية والتحليلات الشاملة",
            "Systematic literature reviews and comprehensive quantitative meta-analyses.",
            "مراجعات منهجية وتحليلات إحصائية تجميعية شاملة لأحدث الدراسات المنشورة",
            review_papers,
            (109, 40, 217)  # Royal Purple
        ))
    if book_papers:
        groups.append((
            "SECTION 2: BOOKS & BOOK CHAPTERS",
            "قسم الكتب العلمية وفصول المراجع",
            "Scholarly monographs, authoritative handbook chapters, and academic reference works.",
            "كتب أكاديمية، فصول ومراجع تخصصية، وموسوعات علمية معتمدة من دور النشر",
            book_papers,
            (16, 149, 108)  # Forest / Emerald Green
        ))
    if research_papers:
        groups.append((
            "SECTION 3: ORIGINAL RESEARCH ARTICLES",
            "قسم الأبحاث والمقالات العلمية الأصيلة",
            "Peer-reviewed primary research articles, clinical studies, and empirical papers.",
            "أبحاث علمية محكّمة وتجارب مخبرية وسريرية وميدانية أصيلة من الدوريات العالمية",
            research_papers,
            (29, 78, 216)  # Deep Academic Blue
        ))
    if preprint_papers:
        groups.append((
            "SECTION 4: PREPRINTS & WORKING PAPERS",
            "قسم المسودات العلمية غير المحكّمة",
            "Preliminary working papers and preprints from scholarly archives awaiting peer review.",
            "مسودات علمية أولية مودعة في مستودعات المسودات بانتظار استكمال التحكيم",
            preprint_papers,
            (194, 65, 12)  # Amber / Ochre
        ))
    if not groups:
        groups.append((
            "COLLECTED PAPERS",
            "مجموعة الأوراق البحثية",
            "Scholarly records collected from academic databases.",
            "مجموعة السجلات البحثية المستخرجة من قواعد البيانات العلمية",
            papers,
            (40, 40, 150)
        ))

    # Table of Contents / Index for non-guests or comprehensive reports
    if not is_guest or len(papers) > 10:
        pdf.add_page()
        pdf.write_block("TABLE OF CONTENTS | فهرس الوثائق والأبحاث", size=14, style="B")
        pdf.ln(3)
        global_idx = 1
        for grp_en, grp_ar, grp_desc_en, grp_desc_ar, grp_items, grp_color in groups:
            pdf.ln(2)
            if FONT_BOLD:
                pdf.set_font("Amiri", "B", 11)
            pdf.set_text_color(*grp_color)
            toc_hdr = f"{grp_en} ({len(grp_items)} Items)   ·   {rtl(grp_ar)}"
            pdf.cell(0, 7, toc_hdr, new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            if FONT_REGULAR:
                pdf.set_font("Amiri", "", 8.5)
            for p in grp_items:
                yr = str(p.get('year') or '0000')
                yr_disp = yr if (yr.isdigit() and len(yr) == 4 and yr != "0000") else "N/A"
                d_lbl = p.get('doc_type_label') or "Research"
                raw_t = p.get('title') or 'No Title'
                clean_t = re.sub(r'<[^>]+>', ' ', raw_t).strip()
                clean_t = re.sub(r'\s+', ' ', clean_t) or 'No Title'
                line = f"{global_idx}. [{d_lbl}] ({yr_disp}) {clean_t[:105]}"
                pdf.multi_cell(0, 5.2, rtl(line), align=("R" if has_arabic(line) else "L"), new_x="LMARGIN", new_y="NEXT")
                global_idx += 1

    # Detailed Paper Cards partitioned by section
    global_idx = 1
    total_records = sum(len(g[4]) for g in groups)
    for grp_en, grp_ar, grp_desc_en, grp_desc_ar, grp_items, grp_color in groups:
        # Distinct Section Divider Header & Meta Box
        pdf.add_page()
        pdf.ln(12)
        pdf.set_fill_color(grp_color[0], grp_color[1], grp_color[2])
        if FONT_BOLD:
            pdf.set_font("Amiri", "B", 13)
        pdf.set_text_color(255, 255, 255)
        divider_title = f"  {grp_en}   ·   {rtl(grp_ar)}  "
        pdf.cell(0, 12, divider_title, fill=True, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)

        grp_years = [int(p['year']) for p in grp_items if str(p.get('year', '')).isdigit() and p['year'] != "0000"]
        yr_range = f"{min(grp_years)} - {max(grp_years)}" if grp_years else "N/A"
        pdf.set_fill_color(246, 248, 253)
        pdf.set_draw_color(grp_color[0], grp_color[1], grp_color[2])
        pdf.set_line_width(0.4)
        info_h = 17
        pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, info_h, "DF")
        pdf.set_line_width(0.2)
        pdf.set_y(pdf.get_y() + 2)

        s_info_en = f"Section Records: {len(grp_items)} Papers   ·   Publication Years: {yr_range}   ·   {grp_desc_en}"
        s_info_ar = f"أبحاث القسم: {len(grp_items)}   ·   سنوات النشر: {yr_range}   ·   {grp_desc_ar}"
        pdf.write_block(s_info_en, size=8.5, color=(40, 40, 60), align="C")
        pdf.write_block(s_info_ar, size=8.5, color=(70, 70, 90), align="C")
        pdf.ln(6)

        for p in grp_items:
            is_separate_page = bool(include_abstracts and (is_other or not is_guest))
            if is_separate_page:
                pdf.add_page()
            else:
                if pdf.get_y() > (pdf.h - 55):
                    pdf.add_page()
                    if FONT_BOLD:
                        pdf.set_font("Amiri", "B", 11)
                    pdf.set_text_color(*grp_color)
                    pdf.cell(0, 7, f"{grp_en}   ·   {rtl(grp_ar)}", new_x="LMARGIN", new_y="NEXT", align="L")
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(3)

            doc_lbl_en = p.get('doc_type_label') or "Original Research"
            doc_lbl_ar = p.get('doc_type_label_ar') or "بحث علمي أصيل"

            pdf.set_fill_color(242, 244, 252)
            if FONT_REGULAR:
                pdf.set_font("Amiri", "B", 10 if is_separate_page else 9)
            pdf.set_text_color(grp_color[0], grp_color[1], grp_color[2])
            sec_tag = grp_en.split(':')[0].strip()
            badge_card_str = f"ITEM {global_idx} OF {total_records}   ·   [{sec_tag}: {doc_lbl_en.upper()}  |  {rtl(doc_lbl_ar)}]"
            pdf.cell(0, 8.5 if is_separate_page else 7.5, badge_card_str, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            raw_t = p.get('title') or 'No Title'
            clean_t = re.sub(r'<[^>]+>', ' ', raw_t).strip()
            clean_t = re.sub(r'\s+', ' ', clean_t) or 'No Title'
            pdf.write_block(clean_t, size=12.5 if is_separate_page else 11.5, style="B")
            pdf.ln(1)

            clean_auths = [a.strip() for a in p.get('authors', []) if a and a.strip() and a.strip().lower() not in ("unknown", "unknown authors", "et al", "et al.")]
            yr = str(p.get('year') or '0000')
            yr_disp = yr if (yr.isdigit() and len(yr) == 4 and yr != "0000") else "Date Unspecified / تاريخ غير محدد"
            pdf.field("Document Type", f"{doc_lbl_en} ({doc_lbl_ar})", value_color=grp_color)
            pdf.field("Authors", format_authors(clean_auths), value_color=(70, 70, 70))
            pdf.field("Year", yr_disp)
            if p.get('journal'):
                pdf.field("Journal / Venue", p['journal'])
            if p.get('publisher'):
                pdf.field("Publisher", p['publisher'])

            sources_list = p.get('sources', [p.get('source_db', 'Unknown')])
            sources_disp = " · ".join(DB_NAMES.get(s, s) for s in sources_list)
            pdf.field("Sources", sources_disp)

            cites = p.get('citations_by_source') or {}
            if cites:
                cites_str = " · ".join(f"{src}: {cnt}" for src, cnt in cites.items())
                pdf.field("Citations", cites_str)
            elif p.get('citation_count'):
                pdf.field("Citations", str(p['citation_count']))

            status_str = "PREPRINT (not peer-reviewed) / مسودة غير محكمة" if p.get('is_preprint') else "Peer-Reviewed Publication / منشور محكم"
            if not p.get('is_preprint') and p.get('publisher'):
                status_str += f" [{p['publisher']}]"
            pdf.field("Review Status", status_str, value_color=(180, 90, 0) if p.get('is_preprint') else (0, 120, 0))
            if p.get('doi') and p['doi'] != "N/A":
                pdf.field("DOI", f"https://doi.org/{p['doi']}", value_color=(0, 0, 255), link=f"https://doi.org/{p['doi']}")
            if p.get('pmcid'):
                pdf.field("PMCID", p['pmcid'], value_color=(0, 120, 0))
            if p.get('oa_url'):
                pdf.field("Open Access URL", p['oa_url'][:100], value_color=(0, 120, 0), link=p['oa_url'])

            abstract_text = (p.get('abstract') or '').strip()
            if include_abstracts and abstract_text:
                pdf.ln(2.5)
                pdf.write_block("ABSTRACT", size=10.5, style="B", color=(40, 40, 150))
                pdf.write_block(abstract_text, size=9.5)
            pdf.ln(2)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(2.5)
            global_idx += 1

    pdf.output(pdf_path)

def generate_all_papers_index(query, papers, pdf_path, title_prefix=""):
    papers = [p.to_dict() if hasattr(p, 'to_dict') else p for p in papers]
    def _year_desc_key(p):
        y = str(p.get('year') or '').strip()
        return (0, -int(y), -int(p.get('citation_count') or 0)) if (y.isdigit() and len(y) == 4 and y != "0000") else (1, 0, -int(p.get('citation_count') or 0))

    # Partition papers into Reviews, Books, Research Articles, and Preprints
    rev_p = [p for p in papers if p.get('doc_partition') == 'review' or p.get('doc_type') in ('review', 'meta_analysis')]
    book_p = [p for p in papers if p.get('doc_partition') == 'book' or p.get('doc_type') == 'book']
    res_p = [p for p in papers if p not in rev_p and p not in book_p and not p.get('is_preprint')]
    pre_p = [p for p in papers if p.get('is_preprint') and p not in rev_p and p not in book_p]

    rev_p.sort(key=_year_desc_key)
    book_p.sort(key=_year_desc_key)
    res_p.sort(key=_year_desc_key)
    pre_p.sort(key=_year_desc_key)

    groups = []
    if rev_p:
        groups.append(("SECTION 1: REVIEWS & META-ANALYSES", "قسم المراجعات العلمية والتحليلات الشاملة", rev_p, (109, 40, 217)))
    if book_p:
        groups.append(("SECTION 2: BOOKS & BOOK CHAPTERS", "قسم الكتب العلمية وفصول المراجع", book_p, (16, 149, 108)))
    if res_p:
        groups.append(("SECTION 3: ORIGINAL RESEARCH ARTICLES", "قسم الأبحاث والمقالات العلمية الأصيلة", res_p, (29, 78, 216)))
    if pre_p:
        groups.append(("SECTION 4: PREPRINTS & WORKING PAPERS", "قسم المسودات العلمية غير المحكّمة", pre_p, (194, 65, 12)))
    if not groups:
        sorted_all = sorted(papers, key=_year_desc_key)
        groups.append(("COLLECTED PAPERS", "مجموعة الأوراق البحثية", sorted_all, (40, 40, 150)))

    pdf = AcademicPDF(doc_header=f"Knowledge Ocean Index {title_prefix} - {clean_text(query)[:50]}")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.ln(16)
    pdf.write_block(f"INDEX OF PAPERS {title_prefix}", size=20, style="B", align="C")
    pdf.ln(2)
    pdf.write_block("فهرس الأوراق والكتب المستخرجة المفصل", size=13, align="C", color=(90, 90, 90))
    pdf.ln(6)
    pdf.set_draw_color(50, 50, 220)
    pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(10)
    years = [int(p['year']) for p in papers if str(p.get('year', '')).isdigit() and p['year'] != "0000"]
    pdf.field("Research Topic", query)
    pdf.field("Compiled On", datetime.now().strftime("%Y-%m-%d"))
    pdf.field("Total Papers", f"{len(papers)}")
    if years:
        pdf.field("Publication Years", f"{min(years)} - {max(years)}")
    pdf.ln(4)

    if not papers:
        pdf.ln(6)
        pdf.write_block("لم يُعثر على أي أوراق.", size=12, style="B", align="C", color=(180, 60, 0))
        pdf.output(pdf_path)
        return 0

    global_i = 1
    total_recs = sum(len(g[2]) for g in groups)
    for grp_en, grp_ar, grp_items, grp_color in groups:
        pdf.add_page()
        pdf.ln(10)
        pdf.set_fill_color(grp_color[0], grp_color[1], grp_color[2])
        if FONT_BOLD:
            pdf.set_font("Amiri", "B", 12.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 11, f"  {grp_en} ({len(grp_items)} Items)   ·   {rtl(grp_ar)}  ", fill=True, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        for p in grp_items:
            if pdf.get_y() > (pdf.h - 45):
                pdf.add_page()
            yr = str(p.get('year') or '0000')
            yr_disp = yr if (yr.isdigit() and len(yr) == 4 and yr != "0000") else "Date Unspecified / تاريخ غير محدد"
            is_preprint = bool(p.get('is_preprint')) or 'preprint' in (p.get('title') or '').lower()
            if FONT_REGULAR:
                pdf.set_font("Amiri", "B", 11)
            pdf.set_text_color(180, 90, 0) if is_preprint else pdf.set_text_color(grp_color[0], grp_color[1], grp_color[2])
            raw_t = p.get('title') or 'No Title'
            clean_t = re.sub(r'<[^>]+>', ' ', raw_t).strip()
            clean_t = re.sub(r'\s+', ' ', clean_t) or 'No Title'
            title_line = f"{global_i}. {clean_t}"
            pdf.multi_cell(0, 6, rtl(title_line), align=("R" if has_arabic(title_line) else "L"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.field("Year", yr_disp)
            clean_auths = [a.strip() for a in p.get('authors', []) if a and a.strip() and a.strip().lower() not in ("unknown", "unknown authors", "et al", "et al.")]
            if clean_auths:
                pdf.field("Authors", format_authors(clean_auths), value_color=(70, 70, 70))
            if p.get('journal'):
                pdf.field("Journal / Venue", p['journal'])
            if p.get('publisher'):
                pdf.field("Publisher", p['publisher'])
            sources_list = p.get('sources', [p.get('source_db', 'Unknown')])
            sources_disp = " · ".join(DB_NAMES.get(s, s) for s in sources_list)
            pdf.field("Sources", sources_disp)
            cites = p.get('citations_by_source') or {}
            if cites:
                cites_str = " · ".join(f"{src}: {cnt}" for src, cnt in cites.items())
                pdf.field("Citations", cites_str)
            elif p.get('citation_count'):
                pdf.field("Citations", str(p['citation_count']))
            status_str = "PREPRINT (not peer-reviewed) / مسودة غير محكمة" if is_preprint else "Peer-Reviewed Publication / منشور محكم"
            if not is_preprint and p.get('publisher'):
                status_str += f" [{p['publisher']}]"
            pdf.field("Review Status", status_str, value_color=(180, 90, 0) if is_preprint else (0, 120, 0))
            if p.get('doi') and p['doi'] != "N/A":
                pdf.field("DOI", f"https://doi.org/{p['doi']}", value_color=(0, 0, 255), link=f"https://doi.org/{p['doi']}")
            oa = (p.get('oa_url') or '').strip()
            if oa:
                pdf.field("Open Access", oa[:110] + ("…" if len(oa) > 110 else ""), value_color=(0, 120, 0), link=oa)
            pdf.ln(1)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(2)
            global_i += 1
    pdf.output(pdf_path)
    return len(papers)


def generate_bibtex_file(papers: List[dict], filepath: str):
    used_keys: Set[str] = set()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("% Knowledge Ocean - Academic Bibliography (BibTeX)\n")
        f.write(f"% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for idx, p in enumerate(papers, start=1):
            p_dict = p.to_dict() if hasattr(p, 'to_dict') else p
            try:
                f.write(generate_bibtex_entry(p_dict, index=idx) + "\n\n")
            except Exception as e:
                log.warning(f"BibTeX entry skipped: {e}")

def generate_ris_file(papers: List[dict], filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        for p in papers:
            p_dict = p.to_dict() if hasattr(p, 'to_dict') else p
            try:
                f.write(generate_ris_entry(p_dict) + "\n\n")
            except Exception as e:
                log.warning(f"RIS entry skipped: {e}")


def build_zip(zip_path, file_paths, task_id=""):
    if task_id and task_id in CANCELLED_TASKS:
        return None
    real = [p for p in file_paths if (isinstance(p, tuple) and os.path.exists(p[0])) or (isinstance(p, str) and os.path.exists(p))]
    if not real:
        return None
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in real:
            if task_id and task_id in CANCELLED_TASKS:
                break
            if isinstance(p, tuple):
                zf.write(p[0], arcname=p[1])
            else:
                zf.write(p, arcname=os.path.basename(p))
    if task_id and task_id in CANCELLED_TASKS:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass
        return None
    return zip_path


def find_active_task_for_key(password: str = "", uh: str = "", guest_token: str = ""):
    """Finds any running, queued, or stopping search task associated with this access key, user hash, or guest token."""
    clean_pwd = password.strip()
    target_code_hash = hashlib.sha256(clean_pwd.encode("utf-8")).hexdigest()[:24] if clean_pwd else ""
    clean_gt = guest_token.strip() if guest_token else ""
    with TASKS_LOCK:
        for tid, t in TASKS.items():
            status = t.get("status")
            if status in ("queued", "processing", "stopping"):
                if target_code_hash and t.get("code_hash") == target_code_hash:
                    return {
                        "has_active_task": True,
                        "task_id": tid,
                        "status": status,
                        "progress": t.get("progress", 0),
                        "message": t.get("message", ""),
                        "query": t.get("query", ""),
                        "mode": t.get("mode", "keyword")
                    }
                if not target_code_hash:
                    if clean_gt and t.get("guest_token") == clean_gt:
                        return {
                            "has_active_task": True,
                            "task_id": tid,
                            "status": status,
                            "progress": t.get("progress", 0),
                            "message": t.get("message", ""),
                            "query": t.get("query", ""),
                            "mode": t.get("mode", "keyword")
                        }
                    if uh and t.get("user_hash") == uh:
                        return {
                            "has_active_task": True,
                            "task_id": tid,
                            "status": status,
                            "progress": t.get("progress", 0),
                            "message": t.get("message", ""),
                            "query": t.get("query", ""),
                            "mode": t.get("mode", "keyword")
                        }
    return {"has_active_task": False}

def _set_task(task_id, **kwargs):
    with TASKS_LOCK:
        cur = TASKS.get(task_id, {})
        cur.update(kwargs)
        if kwargs.get("status") in ("completed", "error"):
            cur["_done_at"] = time.time()
        TASKS[task_id] = cur
    try:
        db_set_task(task_id, **kwargs)
    except Exception:
        pass

def _check_cancelled(task_id):
    if task_id in CANCELLED_TASKS:
        raise ValueError("تم إلغاء البحث بناءً على طلبك.")

def _cleanup_task_files(user_space, safe_query="", ts="", pdf_files=None, pdf_zip=None):
    """حذف فوري لكافة الملفات الوسيطة والأبحاث وأي حزمة ZIP تم إنشاؤها عند إلغاء المهمة أو حدوث خطأ."""
    if pdf_files:
        for temp_f in pdf_files:
            try:
                actual_p = temp_f[0] if isinstance(temp_f, tuple) else temp_f
                if actual_p and os.path.isfile(actual_p):
                    os.remove(actual_p)
            except Exception:
                pass

    if pdf_zip and os.path.isfile(pdf_zip):
        try:
            os.remove(pdf_zip)
        except Exception:
            pass

    # حذف أي ملفات أو حزم ZIP مؤقتة مرتبطة بهذه المهمة في مجلد المستخدم
    if user_space and os.path.isdir(user_space) and ts:
        try:
            for fname in os.listdir(user_space):
                if ts in fname:
                    p = os.path.join(user_space, fname)
                    if os.path.isfile(p):
                        os.remove(p)
        except Exception:
            pass

    if user_space:
        fulltext_dir = os.path.join(user_space, "FullText_PDFs")
        if os.path.isdir(fulltext_dir):
            try:
                shutil.rmtree(fulltext_dir, ignore_errors=True)
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────────────────
# خط المعالجة وإدارة الطابور
# ─────────────────────────────────────────────────────────────────────────
def managed_pipeline_wrapper(query, mode, db_source, limit, affiliation, uh, task_id, require_title, year_from, year_to, include_preprint, is_guest, include_abstracts=False, download_fulltext=False, guest_ip="", guest_fp="", is_other=False, guest_token="", search_scope="all", doc_type_filter="all", **kwargs):
    if query:
        query = normalize_boolean_query(query.strip())
    global PREMIUM_USERS_COUNT
    if not is_guest:
        with PREMIUM_LOCK:
            PREMIUM_USERS_COUNT += 1
            if PREMIUM_USERS_COUNT > 0:
                GUESTS_CAN_RUN.clear()
    else:
        with QUEUE_LOCK:
            if len(GUEST_QUEUE) >= 100:
                _set_task(task_id, status="error", error="الطابور ممتلئ حالياً (100 مستخدم في الانتظار). يرجى المحاولة لاحقاً.")
                return
            if task_id not in GUEST_QUEUE and task_id not in ACTIVE_GUESTS:
                if len(ACTIVE_GUESTS) < 5 and PREMIUM_USERS_COUNT == 0 and len(GUEST_QUEUE) == 0:
                    ACTIVE_GUESTS.add(task_id)
                else:
                    GUEST_QUEUE.append(task_id)

        while True:
            if task_id in CANCELLED_TASKS:
                with QUEUE_LOCK:
                    if task_id in GUEST_QUEUE:
                        GUEST_QUEUE.remove(task_id)
                    if task_id in ACTIVE_GUESTS:
                        ACTIVE_GUESTS.remove(task_id)
                return

            with QUEUE_LOCK:
                if task_id in ACTIVE_GUESTS:
                    break
                pos = GUEST_QUEUE.index(task_id) + 1 if task_id in GUEST_QUEUE else 0
                if pos == 1 and PREMIUM_USERS_COUNT == 0 and len(ACTIVE_GUESTS) < 5:
                    ACTIVE_GUESTS.add(task_id)
                    GUEST_QUEUE.remove(task_id)
                    break
                elif pos > 0:
                    _set_task(task_id, status="queued", message=f"في الطابور (موقعك: {pos} من 100)...")
            time.sleep(1)

    try:
        with_abstracts = bool(include_abstracts or download_fulltext)
        process_pipeline(query, mode, db_source, limit, affiliation, uh, task_id, require_title, year_from, year_to, include_preprint, is_guest, include_abstracts=with_abstracts, guest_ip=guest_ip, guest_fp=guest_fp, guest_token=guest_token, is_other=is_other, search_scope=search_scope, doc_type_filter=doc_type_filter)
    finally:
        if not is_guest:
            with PREMIUM_LOCK:
                PREMIUM_USERS_COUNT -= 1
                if PREMIUM_USERS_COUNT == 0:
                    GUESTS_CAN_RUN.set()
        else:
            with QUEUE_LOCK:
                if task_id in ACTIVE_GUESTS:
                    ACTIVE_GUESTS.remove(task_id)
                elif task_id in GUEST_QUEUE:
                    GUEST_QUEUE.remove(task_id)


def process_pipeline(query, mode="keyword", db_source="all", limit=10, affiliation="", uh="default", task_id="", require_title=False, year_from=None, year_to=None, include_preprint=True, is_guest=False, include_abstracts=False, download_fulltext=False, guest_ip="", guest_fp="", is_other=False, search_scope="all", doc_type_filter="all", **kwargs):
    guest_token = kwargs.get("guest_token", "")
    with_abstracts = bool(include_abstracts or download_fulltext or kwargs.get("with_abstracts", False))
    if query:
        query = normalize_boolean_query(query.strip())
    if "max_results" in kwargs:
        limit = kwargs["max_results"]
    if not task_id and "task_id" in kwargs:
        task_id = kwargs["task_id"]
    if "is_vip" in kwargs:
        is_guest = not bool(kwargs["is_vip"])
    try:
        _check_cancelled(task_id)
        _set_task(task_id, status="processing", progress=15, message="بدء مسح وتدقيق الأبحاث عبر المحركات الأكاديمية...")

        is_include_preprint = str(include_preprint).lower() in ("true", "1", "yes", "on") if isinstance(include_preprint, (str, bool)) else bool(include_preprint)
        user_space = os.path.join(DOWNLOAD_DIR, uh)
        os.makedirs(user_space, exist_ok=True)
        safe_query = sanitize_filename(query)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        unlimited = int(limit) >= 999999
        target_limit = UNLIMITED_CAP if unlimited else int(limit)

        # Constraint 9 & P0.2: Exact DOI Direct Lookup Routing
        is_exact_doi = is_doi_query(query)
        exact_doi_val = extract_doi(query) if is_exact_doi else None

        if is_exact_doi:
            active = [k for k in ['crossref', 'openalex', 'europepmc', 'pubmed', 'semanticscholar'] if k in FETCH_BATCH_MAP]
            target_limit = 1
        elif search_scope == 'books' or db_source == 'books':
            book_priority = ['googlebooks', 'openlibrary', 'crossref', 'openalex']
            active = [k for k in book_priority if k in FETCH_BATCH_MAP]
        elif db_source == 'all':
            fast_priority = ['verified_literature', 'pubmed', 'crossref', 'openalex', 'europepmc', 'doaj', 'semanticscholar', 'core', 'zenodo']
            # The licensed Elsevier API is included in comprehensive searches only for VIP.
            if not is_guest and (os.environ.get('ELSEVIER_API_KEY', '').strip() or ELSEVIER_API_KEY):
                fast_priority.append('elsevier')
            if search_scope != 'papers':
                fast_priority.extend(['googlebooks', 'openlibrary'])
            if is_include_preprint:
                fast_priority.append('arxiv')
            active = [k for k in fast_priority if k in FETCH_BATCH_MAP]
        else:
            active = [db_source] if db_source in FETCH_BATCH_MAP else ['crossref']

        if search_scope == 'papers':
            active = [k for k in active if k not in ('googlebooks', 'openlibrary')]

        if is_guest and 'elsevier' in active:
            active.remove('elsevier')
        if not is_include_preprint and 'arxiv' in active:
            active.remove('arxiv')
        if not active:
            active = ['crossref']

        engine_states = {
            name: {'offset': 0, 'page': 1, 'cursor': '*', 'exhausted': False, 'include_preprint': is_include_preprint}
            for name in active
        }

        # Determine batch sizes
        if target_limit <= 10:
            batch_size = 10
            initial_engines = active
        else:
            batch_size = 25 if target_limit <= 50 else (50 if target_limit <= 250 else 100)
            initial_engines = active

        txt_filename = f"COLLECTED_PAPERS_{safe_query}_{ts}.txt"
        txt_path = os.path.join(user_space, txt_filename)

        # P1: ScholarlyPaperIndex for lossless record linkage and deduplication
        paper_index = ScholarlyPaperIndex()
        provider_diagnostics = {}

        y_from = int(year_from) if str(year_from or '').strip().isdigit() else None
        y_to = int(year_to) if str(year_to or '').strip().isdigit() else None

        def _year_in_range(p_year):
            try:
                y = int(str(p_year))
                if y == 0:
                    return True
                if y_from and y < y_from:
                    return False
                if y_to and y > y_to:
                    return False
                return True
            except Exception:
                return True

        round_no = 0
        search_started = time.monotonic()
        search_max_seconds = max(30, min(150, int(os.environ.get("SEARCH_MAX_SECONDS", "90"))))
        max_search_rounds = max(2, min(8, int(os.environ.get("SEARCH_MAX_ROUNDS", "4"))))
        rounds_without_new_papers = 0
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(f"Knowledge Ocean Exploration Log\nTopic: {query}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "="*70 + "\n\n")

            while len(paper_index) < target_limit:
                if round_no >= max_search_rounds or time.monotonic() - search_started >= search_max_seconds:
                    log.warning("Search budget reached for task %s: %s rounds, %s papers", task_id, round_no, len(paper_index))
                    break
                before_count = len(paper_index)
                round_no += 1
                if task_id in CANCELLED_TASKS:
                    log.info(f"Task {task_id} cancellation detected in loop. Stopping search with {len(paper_index)} papers.")
                    break

                engines_to_run = initial_engines if (round_no == 1 and target_limit <= 10) else active
                active_this_round = [name for name in engines_to_run if not engine_states[name]['exhausted'] and not is_engine_in_cooldown(name)]
                if not active_this_round:
                    active_this_round = [name for name in active if not engine_states[name]['exhausted'] and not is_engine_in_cooldown(name)]
                    if not active_this_round:
                        break

                remaining_seconds = search_max_seconds - (time.monotonic() - search_started)
                if remaining_seconds <= 0:
                    break
                executor = ThreadPoolExecutor(max_workers=min(6, len(active_this_round)))
                futures = {
                    executor.submit(FETCH_BATCH_MAP[name], query, engine_states[name], mode, affiliation, task_id, is_guest, batch_size): name
                    for name in active_this_round
                }

                try:
                    for fut in as_completed(futures, timeout=min(12 if target_limit <= 10 else 22, max(1, remaining_seconds))):
                        if task_id in CANCELLED_TASKS:
                            log.info(f"Task {task_id} cancellation detected in futures. Breaking out.")
                            break
                        eng_name = futures[fut]
                        try:
                            batch_papers = fut.result()
                            provider_diagnostics[eng_name] = {
                                "returned": provider_diagnostics.get(eng_name, {}).get("returned", 0) + len(batch_papers or []),
                                "status": "responded"
                            }
                            for p in batch_papers:
                                if not isinstance(p, CanonicalPaper):
                                    continue
                                if task_id in CANCELLED_TASKS:
                                    break

                                # P0.4: Safe retraction check
                                if is_banned_publication(p.title):
                                    continue
                                if (y_from or y_to) and not _year_in_range(p.year):
                                    continue
                                if not is_include_preprint and (p.is_preprint or p.arxiv_id or p.doc_type == 'preprint' or p.doc_partition == 'preprint' or is_preprint_record(doi=p.doi, journal=p.journal, title=p.title, raw_type=p.raw_type, publisher=p.publisher)):
                                    continue

                                # P0.3 & P2: Boolean and natural query matching
                                if mode != "author" and not matches_target_query(query, p.title, p.abstract, require_title=require_title, doi=p.doi):
                                    continue

                                # P1.3 & P1.4: Add or merge into canonical index
                                canonical = paper_index.add_or_merge(p)

                                txt_entry = f"[{len(paper_index)}] ({canonical.year}) {canonical.title}\n"
                                txt_entry += f"    Authors: {format_authors(canonical.authors)}\n"
                                txt_entry += f"    Sources: {', '.join(canonical.sources)} | DOI: {canonical.doi or 'N/A'}\n"
                                if canonical.abstract:
                                    txt_entry += f"    Abstract: {clean_text(canonical.abstract)[:250]}...\n\n"
                                else:
                                    txt_entry += "    Abstract: [No abstract provided in source metadata]\n\n"
                                txt_file.write(txt_entry)
                                txt_file.flush()

                                if (len(paper_index) >= target_limit and not is_exact_doi) or task_id in CANCELLED_TASKS:
                                    break
                        except Exception as e:
                            provider_diagnostics[eng_name] = {"status": "error", "error_type": type(e).__name__}
                            log.exception("Engine %s batch error in task %s", eng_name, task_id)

                        if task_id in CANCELLED_TASKS:
                            break
                except TimeoutError:
                    pending = [name for future, name in futures.items() if not future.done()]
                    for name in pending:
                        provider_diagnostics[name] = {"status": "timeout"}
                    log.warning("Search task %s timed out waiting for providers: %s", task_id, pending)
                except Exception:
                    log.exception("Search task %s failed during provider collection", task_id)
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                if task_id in CANCELLED_TASKS:
                    log.info(f"Task {task_id} cancellation detected after batch. Exiting search loop with {len(paper_index)} papers.")
                    break

                if len(paper_index) >= target_limit:
                    break
                if len(paper_index) <= before_count:
                    rounds_without_new_papers += 1
                else:
                    rounds_without_new_papers = 0
                if rounds_without_new_papers >= 2:
                    log.warning("Stopping task %s: two search rounds without new papers", task_id)
                    break

                pct = min(75, 15 + int((len(paper_index) / target_limit) * 60)) if not unlimited else min(75, 15 + round_no * 10)
                _set_task(task_id, progress=pct, message=f"تم جمع وتدقيق {len(paper_index)} من أصل {target_limit} بحث...")

        all_canonical = paper_index.get_all()
        if not all_canonical:
            if task_id in CANCELLED_TASKS:
                raise ValueError("تم إيقاف البحث بناءً على طلبك (لم يتم العثور على أبحاث بعد).")
            detail = ", ".join(f"{name}: {info.get('status', 'unknown')} ({info.get('returned', 0)})" for name, info in sorted(provider_diagnostics.items()))
            log.warning("Task %s returned no qualifying papers. Providers: %s", task_id, detail or "no providers returned")
            raise ValueError("لم يتم استرجاع أوراق علمية مطابقة. قد تكون قواعد البيانات غير متاحة أو شروط البحث شديدة التقييد. راجع سجلات المزودين. / No matching papers retrieved; provider errors or restrictive filters may be responsible.")

        # Ensure exact DOI result has enriched authors, real year, and substantive title
        if is_exact_doi and all_canonical:
            p_first = all_canonical[0]
            clean_first_authors = [a.strip() for a in p_first.authors if a and a.strip() and a.strip().lower() not in ("unknown", "unknown authors", "et al", "et al.")]
            c_doi = p_first.doi or exact_doi_val
            if c_doi and (not clean_first_authors or p_first.year == "0000" or p_first.title in ("No Title", "Untitled") or p_first.title.startswith("Paper (")):
                try:
                    r_oa = safe_get('openalex', f"https://api.openalex.org/works/https://doi.org/{c_doi}", task_id, is_guest, params={"mailto": UNPAYWALL_EMAIL}, timeout=5)
                    if r_oa and r_oa.status_code == 200:
                        oa_item = r_oa.json()
                        oa_auths = [a.get("author", {}).get("display_name", "").strip() for a in oa_item.get("authorships", []) if a.get("author", {}).get("display_name", "").strip()]
                        if oa_auths and not clean_first_authors:
                            p_first.authors = oa_auths
                            clean_first_authors = oa_auths
                        if p_first.year == "0000":
                            p_first.year = str(oa_item.get("publication_year") or (oa_item.get("publication_date") or "")[:4] or "0000")
                        if (not p_first.title or p_first.title in ("No Title", "Untitled") or p_first.title.startswith("Paper (")) and oa_item.get("title"):
                            p_first.title = oa_item.get("title")
                except Exception:
                    pass
                if not clean_first_authors and c_doi:
                    try:
                        r_dc = safe_get('datacite', f"https://api.datacite.org/dois/{c_doi}", task_id, is_guest, timeout=5)
                        if r_dc and r_dc.status_code == 200:
                            dc_attrs = r_dc.json().get("data", {}).get("attributes", {})
                            dc_creators = dc_attrs.get("creators") or []
                            dc_auths = [c.get("name") or f"{c.get('givenName', '')} {c.get('familyName', '')}".strip() for c in dc_creators]
                            dc_auths = [a.strip() for a in dc_auths if a and a.strip()]
                            if dc_auths:
                                p_first.authors = dc_auths
                            if p_first.year == "0000" and dc_attrs.get("publicationYear"):
                                p_first.year = str(dc_attrs["publicationYear"])
                            if (not p_first.title or p_first.title in ("No Title", "Untitled") or p_first.title.startswith("Paper (")):
                                dc_titles = dc_attrs.get("titles") or []
                                if dc_titles and dc_titles[0].get("title"):
                                    p_first.title = dc_titles[0]["title"]
                    except Exception:
                        pass

        # P3: Hybrid ranking score calculation
        # Filter papers by search_scope (all, papers, books) and doc_type_filter (all, review, meta_analysis, book, research, conference)
        filtered_canonical = []
        for p in all_canonical:
            if not matches_search_scope(p, search_scope):
                continue
            if not matches_doc_type_filter(p, doc_type_filter):
                continue
            if not is_include_preprint and (p.is_preprint or p.arxiv_id or p.doc_type == 'preprint' or p.doc_partition == 'preprint' or is_preprint_record(doi=p.doi, journal=p.journal, title=p.title, raw_type=p.raw_type, publisher=p.publisher)):
                continue
            filtered_canonical.append(p)

        # Fallback if strict filter returned 0 but some papers matched broadly
        if not filtered_canonical and all_canonical and doc_type_filter == 'all' and search_scope == 'all':
            if is_include_preprint:
                filtered_canonical = all_canonical
            else:
                filtered_canonical = [
                    p for p in all_canonical
                    if not (p.is_preprint or p.arxiv_id or p.doc_type == 'preprint' or p.doc_partition == 'preprint' or is_preprint_record(doi=p.doi, journal=p.journal, title=p.title, raw_type=p.raw_type, publisher=p.publisher))
                ]

        for p in filtered_canonical:
            p._relevance = score_paper_relevance(query, p)

        filtered_canonical.sort(
            key=lambda x: (
                x._relevance,
                SOURCE_PRIORITY.get(x.sources[0] if x.sources else '', 0),
                int(x.year) if str(x.year).isdigit() else 0
            ),
            reverse=True
        )

        final_canonical = filtered_canonical[:target_limit] if not unlimited else filtered_canonical
        final_papers = [p.to_dict() for p in final_canonical]
        if not with_abstracts:
            for p_dict in final_papers:
                p_dict['abstract'] = ""
                p_dict['has_abstract'] = False

        if not is_include_preprint:
            peer = [
                p for p in final_papers
                if not (p.get('is_preprint') or p.get('arxiv_id') or p.get('doc_type') == 'preprint' or p.get('doc_partition') == 'preprint' or is_preprint_record(doi=p.get('doi'), journal=p.get('journal'), title=p.get('title'), raw_type=p.get('raw_type'), publisher=p.get('publisher')))
            ]
            preprints = []
            final_papers = peer
        else:
            peer = [p for p in final_papers if not p.get('is_preprint')]
            preprints = [p for p in final_papers if p.get('is_preprint')]

        if not final_papers:
            raise ValueError("No papers remain after document-type and scope filtering; broaden filters.")

        if is_guest and len(final_papers) < target_limit and guest_ip and guest_fp:
            unused_papers = target_limit - len(final_papers)
            refund_guest_search_quota(guest_ip, guest_fp, unused_papers * (2 if with_abstracts else 1), is_other=is_other, guest_token=guest_token if "guest_token" in locals() else "")

        pdf_files = []
        is_stopped = bool(task_id in CANCELLED_TASKS)
        status_prefix = "تم إيقاف البحث — " if is_stopped else ""
        _set_task(task_id, progress=85, message=f"{status_prefix}تم فرز {len(final_papers)} بحث — جاري توليد ملفات PDF...")

        if is_guest:
            _set_task(task_id, progress=90, message=f"{status_prefix}جاري إعداد وتنسيق ملف الأبحاث بصيغة PDF ({len(final_papers)} بحث)...")
            pdf_filename = f"Academic_Report_{safe_query}_{ts}.pdf"
            single_pdf_p = os.path.join(user_space, pdf_filename)
            generate_documents(query, final_papers, single_pdf_p, None, db_source, "Academic Report", is_guest=is_guest, include_abstracts=with_abstracts, is_other=is_other)

            if os.path.exists(txt_path):
                try:
                    os.remove(txt_path)
                except Exception:
                    pass

            abs_pdf_path = os.path.abspath(single_pdf_p)
            pdf_url = f"/download/{uh}/{pdf_filename}" if os.path.exists(single_pdf_p) else ""

            # Save companion .json metadata file for history and preview
            json_filename = f"Academic_Report_{safe_query}_{ts}.json"
            json_p = os.path.join(user_space, json_filename)
            try:
                with open(json_p, "w", encoding="utf-8") as jf:
                    json.dump({
                        "query": query,
                        "timestamp": ts,
                        "count": len(final_papers),
                        "papers": final_papers,
                        "filename": pdf_filename,
                        "pdf_url": pdf_url,
                        "download_url": pdf_url,
                        "save_path": abs_pdf_path,
                        "with_abstracts": with_abstracts,
                        "user_hash": uh,
                        "guest_ip": guest_ip,
                        "guest_fp": guest_fp,
                        "guest_token": guest_token,
                        "is_guest": is_guest,
                        "stopped": is_stopped
                    }, jf, ensure_ascii=False)
            except Exception as je:
                log.warning(f"Failed to save companion JSON: {je}")

            comp_msg = f"تم إيقاف البحث بنجاح! تم إعداد ملف الأبحاث بما تم جمعه ({len(peer)} بحث محكّم، {len(preprints)} مسودة)" if is_stopped else f"اكتمل الاستخراج بنجاح! تم إعداد ملف الأبحاث ({len(peer)} بحث محكّم، {len(preprints)} مسودة)"
            _set_task(task_id, status="completed", progress=100,
                      message=comp_msg,
                      papers=final_papers,
                      include_abstracts=with_abstracts,
                      with_abstracts=with_abstracts,
                      has_abstracts=with_abstracts,
                      pdf_url=pdf_url,
                      file_type="pdf",
                      is_zip=False,
                      filename=pdf_filename,
                      pdf_zip="",
                      md_url="", md_zip="",
                      save_path=abs_pdf_path,
                      local_path=abs_pdf_path,
                      file_path=abs_pdf_path,
                      user_hash=uh,
                      guest_ip=guest_ip,
                      guest_fp=guest_fp,
                      guest_token=guest_token,
                      is_guest=is_guest,
                      counts={"peer": len(peer), "preprints": len(preprints), "batches": 1, "unlimited": False, "stopped": is_stopped})
            return

        if peer:
            chunks = [peer[i:i+500] for i in range(0, len(peer), 500)] if unlimited or len(peer) > 500 else [peer]
            for idx, chunk in enumerate(chunks, start=1):
                pdf_p = os.path.join(user_space, f"{idx:02d}_{safe_query}_{ts}_PeerReviewed.pdf")
                try:
                    generate_documents(query, chunk, pdf_p, None, db_source, "Peer-Reviewed", is_guest=is_guest, include_abstracts=with_abstracts, is_other=is_other)
                    pdf_files.append(pdf_p)
                except Exception as e:
                    log.warning(f"chunk peer {idx} failed: {e}")
            try:
                all_peer_pdf = os.path.join(user_space, f"INDEX_PeerReviewed_{safe_query}_{ts}.pdf")
                generate_all_papers_index(query, peer, all_peer_pdf, title_prefix="(Peer-Reviewed)")
                pdf_files.append(all_peer_pdf)
            except Exception as e:
                log.warning(f"ALL peer failed: {e}")

        if preprints:
            chunks_pre = [preprints[i:i+500] for i in range(0, len(preprints), 500)] if unlimited or len(preprints) > 500 else [preprints]
            for idx, chunk in enumerate(chunks_pre, start=1):
                pdf_p = os.path.join(user_space, f"{idx:02d}_{safe_query}_{ts}_Preprints.pdf")
                try:
                    generate_documents(query, chunk, pdf_p, None, db_source, "Preprint", is_guest=is_guest, include_abstracts=with_abstracts, is_other=is_other)
                    pdf_files.append(pdf_p)
                except Exception as e:
                    log.warning(f"chunk preprint {idx} failed: {e}")
            try:
                all_pre_pdf = os.path.join(user_space, f"INDEX_Preprints_{safe_query}_{ts}.pdf")
                generate_all_papers_index(query, preprints, all_pre_pdf, title_prefix="(Preprints)")
                pdf_files.append(all_pre_pdf)
            except Exception as e:
                log.warning(f"ALL preprint failed: {e}")

        if os.path.exists(txt_path):
            pdf_files.append(txt_path)

        # Generate Academic Citations Export: BibTeX (.bib) & RIS (.ris)
        try:
            bib_path = os.path.join(user_space, f"REFERENCES_{safe_query}_{ts}.bib")
            generate_bibtex_file(final_papers, bib_path)
            pdf_files.append(bib_path)
        except Exception as e:
            log.warning(f"BibTeX generation failed: {e}")

        try:
            ris_path = os.path.join(user_space, f"REFERENCES_{safe_query}_{ts}.ris")
            generate_ris_file(final_papers, ris_path)
            pdf_files.append(ris_path)
        except Exception as e:
            log.warning(f"RIS generation failed: {e}")

        _set_task(task_id, progress=95, message=f"{status_prefix}ضغط {len(pdf_files)} ملف في حزمة ZIP...")

        # Build PDF ZIP only
        pdf_zip = os.path.join(user_space, f"{safe_query}_{ts}_PDF.zip")
        built = build_zip(pdf_zip, pdf_files)

        if not built or not os.path.exists(pdf_zip):
            raise ValueError("تعذّر إنشاء حزمة ZIP.")

        # Immediate cleanup: delete individual PDF files and text log immediately upon zip completion
        for temp_f in pdf_files:
            try:
                actual_p = temp_f[0] if isinstance(temp_f, tuple) else temp_f
                if actual_p != pdf_zip and os.path.isfile(actual_p):
                    os.remove(actual_p)
            except Exception as e:
                log.warning(f"Could not remove temp file {temp_f}: {e}")

        # Remove temporary FullText_PDFs directory if present
        fulltext_dir = os.path.join(user_space, "FullText_PDFs")
        if os.path.isdir(fulltext_dir):
            try:
                shutil.rmtree(fulltext_dir, ignore_errors=True)
            except Exception:
                pass

        abs_zip_path = os.path.abspath(pdf_zip)
        pdf_url = f"/download/{uh}/{os.path.basename(pdf_zip)}" if os.path.exists(pdf_zip) else ""

        # Save companion .json metadata file for history and preview
        json_filename = f"{safe_query}_{ts}_PDF.json"
        json_p = os.path.join(user_space, json_filename)
        try:
            with open(json_p, "w", encoding="utf-8") as jf:
                json.dump({
                    "query": query,
                    "timestamp": ts,
                    "count": len(final_papers),
                    "papers": final_papers,
                    "filename": os.path.basename(pdf_zip),
                    "pdf_url": pdf_url,
                    "download_url": pdf_url,
                    "save_path": abs_zip_path,
                    "with_abstracts": with_abstracts,
                    "user_hash": uh,
                    "guest_ip": guest_ip,
                    "guest_fp": guest_fp,
                    "guest_token": guest_token,
                    "is_guest": is_guest,
                    "stopped": is_stopped
                }, jf, ensure_ascii=False)
        except Exception as je:
            log.warning(f"Failed to save companion JSON for VIP: {je}")

        comp_msg = f"تم إيقاف البحث بنجاح! تم إعداد ملف الأبحاث بما تم جمعه ({len(peer)} بحث محكّم، {len(preprints)} مسودة)" if is_stopped else f"اكتمل الاستخراج بنجاح! تم العثور على ({len(peer)} بحث محكّم، {len(preprints)} مسودة)"

        _set_task(task_id, status="completed", progress=100,
                  message=comp_msg,
                  papers=final_papers,
                  include_abstracts=with_abstracts,
                  with_abstracts=with_abstracts,
                  has_abstracts=with_abstracts,
                  pdf_url=pdf_url, md_url="",
                  pdf_zip=pdf_url, md_zip="",
                  file_type="zip",
                  is_zip=True,
                  filename=os.path.basename(pdf_zip),
                  save_path=abs_zip_path,
                  local_path=abs_zip_path,
                  file_path=abs_zip_path,
                  user_hash=uh,
                  guest_ip=guest_ip,
                  guest_fp=guest_fp,
                  guest_token=guest_token,
                  is_guest=is_guest,
                  counts={"peer": len(peer), "preprints": len(preprints), "batches": len(pdf_files), "unlimited": unlimited, "stopped": is_stopped})
    except Exception as e:
        log.error(f"Task {task_id} failed: {e}")
        is_cancelled = (task_id in CANCELLED_TASKS) or ("إلغاء" in str(e))
        clean_user_space = user_space if 'user_space' in locals() else None
        clean_safe_query = safe_query if 'safe_query' in locals() else ""
        clean_ts = ts if 'ts' in locals() else ""
        clean_pdf_files = pdf_files if 'pdf_files' in locals() else None
        clean_pdf_zip = pdf_zip if 'pdf_zip' in locals() else None
        _cleanup_task_files(clean_user_space, clean_safe_query, clean_ts, clean_pdf_files, clean_pdf_zip)

        if is_guest and guest_ip and guest_fp and 'final_papers' not in locals():
            try:
                target_limit_val = target_limit if 'target_limit' in locals() else limit
                with_abs_val = with_abstracts if 'with_abstracts' in locals() else False
                refund_guest_search_quota(guest_ip, guest_fp, target_limit_val * (2 if with_abs_val else 1), is_other=is_other if 'is_other' in locals() else False, guest_token=guest_token if 'guest_token' in locals() else "")
            except Exception:
                pass

        if is_cancelled:
            _set_task(task_id, status="error", progress=100,
                      message="تم إلغاء البحث بناءً على طلبك.",
                      error="تم إلغاء البحث بناءً على طلبك.",
                      pdf_url="", pdf_zip="", md_url="", md_zip="",
                      save_path="", local_path="", file_path="", papers=[])
        else:
            _set_task(task_id, status="error", progress=100, error=str(e),
                      pdf_url="", pdf_zip="", md_url="", md_zip="",
                      save_path="", local_path="", file_path="")
    finally:
        if task_id in CANCELLED_TASKS:
            CANCELLED_TASKS.discard(task_id)

# ─────────────────────────────────────────────────────────────────────────
# نقاط الـ API
# ─────────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    index_file = "templates/index.html" if os.path.exists("templates/index.html") else "index.html"
    is_hf = bool(os.environ.get("SPACE_ID") or os.environ.get("HF_SPACE"))
    is_local = not is_hf and is_local_instance(request)
    is_local_flag = "true" if is_local else "false"
    is_hf_flag = "true" if is_hf else "false"
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            injected = f"<script>window.__IS_LOCAL_INSTANCE__ = {is_local_flag}; window.__IS_HF_SPACE__ = {is_hf_flag}; window.__GUEST_QUOTA_LIMIT__ = {GUEST_SEARCH_QUOTA}; window.__SECONDARY_QUOTA_LIMIT__ = {SECONDARY_SEARCH_QUOTA};</script>"
            if "</head>" in html_content:
                html_content = html_content.replace("</head>", f"{injected}</head>")
            return HTMLResponse(content=html_content)
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/active-task")
async def api_active_task(request: Request, password: str = "", guest_token: str = ""):
    """Returns any currently running task for the given access key, guest token, or client IP."""
    clean_gt = (guest_token or "").strip() or request.headers.get("X-Guest-Token", "").strip()
    ip, browser_fp = get_fingerprint(request)
    uh = hashlib.sha256(f"guest_{clean_gt}_{browser_fp}".encode()).hexdigest()[:16] if clean_gt else hashlib.sha256(f"{ip}_{browser_fp}".encode()).hexdigest()[:16]
    owner = session_owner(request)
    if not owner and not is_local_instance(request):
        return {"has_active_task": False}
    return find_active_task_for_key("", owner or "local_user", "")

@app.get("/api/guest-quota")
async def api_guest_quota(request: Request, response: Response, password: str = "", guest_token: str = ""):
    """
    Returns live remaining search quota:
    - VIP: Unlimited
    - Secondary password (other_password): 250 standard searches / 125 with summaries daily
    - Guest without code: 50 standard searches / 25 with summaries daily
    """
    clean_gt = (guest_token or "").strip() or request.headers.get("X-Guest-Token", "").strip()
    ip, browser_fp = get_fingerprint(request)
    is_banned, ban_remaining = db_check_ip_ban(ip)
    if is_banned:
        hours = int(ban_remaining // 3600)
        mins = int((ban_remaining % 3600) // 60)
        time_str = f"{hours} ساعة و {mins} دقيقة" if hours > 0 else f"{mins} دقيقة"
        return {
            "ok": False,
            "banned": True,
            "remaining_seconds": int(ban_remaining),
            "error": f"تم حظر عنوان IP الخاص بك مؤقتاً لمدة 24 ساعة لتجاوز 5 محاولات خاطئة متتالية. الوقت المتبقي لفك الحظر: {time_str}."
        }

    uh = hashlib.sha256(f"guest_{clean_gt}_{browser_fp}".encode()).hexdigest()[:16] if clean_gt else hashlib.sha256(f"{ip}_{browser_fp}".encode()).hexdigest()[:16]
    owner = session_owner(request)
    active_task = find_active_task_for_key("", owner or "local_user", "") if (owner or is_local_instance(request)) else {"has_active_task": False}
    if not owner and clean_gt and not is_local_instance(request):
        issue_session(response, uh, secure=request.url.scheme == "https")

    session_uh = session_owner(request)
    is_vip = verify_password(password) or bool(session_uh and any(hmac.compare_digest(session_uh, user_hash_for(p)) for p in APP_PASSWORDS))
    if is_vip or is_local_instance(request):
        return {
            "ok": True,
            "is_vip": True,
            "is_other": False,
            "quota_limit": 999999,
            "remaining": 999999,
            "remaining_summary": 999999,
            "unlimited": True,
            "auto_renew": False,
            "active_task": active_task
        }
    is_other = verify_other_password(password) or bool(session_uh and any(hmac.compare_digest(session_uh, user_hash_for(p)) for p in OTHER_PASSWORDS))
    quota_limit = SECONDARY_SEARCH_QUOTA if is_other else GUEST_SEARCH_QUOTA
    rem = get_guest_remaining_quota(ip, browser_fp, is_other=is_other, guest_token=clean_gt)
    return {
        "ok": True,
        "is_vip": False,
        "is_other": is_other,
        "quota_limit": quota_limit,
        "remaining": rem,
        "remaining_summary": rem // 2,
        "unlimited": False,
        "auto_renew": is_other,
        "active_task": active_task,
        "renew_time": "12:00 AM (توقيت بغداد UTC+3)",
        "baghdad_time": get_baghdad_now().strftime("%Y-%m-%d %H:%M:%S")
    }


@app.post("/api/login")
async def api_login(request: Request):
    """
    تسجيل الدخول بالرمز الثانوي أو رمز VIP مع حظر IP لمدة 24 ساعة بعد 5 محاولات خاطئة متتالية.
    """
    ip, _ = get_fingerprint(request)
    is_banned, remaining = db_check_ip_ban(ip)
    if is_banned:
        hours = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        time_str = f"{hours} ساعة و {mins} دقيقة" if hours > 0 else f"{mins} دقيقة"
        return JSONResponse(
            status_code=403,
            content={
                "status": "banned",
                "banned": True,
                "error": f"تم حظر عنوان IP الخاص بك ({ip}) لمدة 24 ساعة بسبب تجاوز 5 محاولات خاطئة متتالية. الوقت المتبقي لفك الحظر: {time_str}.",
                "remaining_seconds": int(remaining)
            }
        )

    password = ""
    try:
        data = await request.json()
        password = str(data.get("password") or "").strip()
    except Exception:
        try:
            form = await request.form()
            password = str(form.get("password") or "").strip()
        except Exception:
            pass

    if not password:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "يرجى إدخال رمز الوصول / Please enter access code."}
        )

    is_vip = verify_password(password)
    is_other = verify_other_password(password)

    if is_vip:
        db_record_auth_attempt(ip, success=True)
        response = JSONResponse({
            "status": "success",
            "tier": "vip",
            "is_vip": True,
            "is_other": False,
            "quota": "unlimited",
            "message": "تم تسجيل الدخول بنجاح! حساب VIP نشط (استخراج شامل وبلا حدود)."
        })
        issue_session(response, user_hash_for(password), secure=request.url.scheme == "https")
        return response
    elif is_other:
        db_record_auth_attempt(ip, success=True)
        response = JSONResponse({
            "status": "success",
            "tier": "secondary",
            "is_vip": False,
            "is_other": True,
            "quota": SECONDARY_SEARCH_QUOTA,
            "message": f"تم تفعيل الرمز الثانوي بنجاح! حصة يومية متجددة سعتها {SECONDARY_SEARCH_QUOTA} بحثاً (تتجدد 12:00 ص بتوقيت بغداد)."
        })
        issue_session(response, user_hash_for(password), secure=request.url.scheme == "https")
        return response
    else:
        # Invalid attempt
        banned, attempts_left, rem = db_record_auth_attempt(ip, success=False)
        if banned:
            return JSONResponse(
                status_code=403,
                content={
                    "status": "banned",
                    "banned": True,
                    "error": "تم إدخال الرمز بشكل خاطئ 5 مرات متتالية! تم حظر عنوان IP الخاص بك لمدة 24 ساعة لحماية المنصة من محاولات التخمين الآلية.",
                    "remaining_seconds": int(rem)
                }
            )
        else:
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "error": f"الرمز المدخل غير صحيح! تبقى لديك {attempts_left} من أصل 5 محاولات قبل حظر عنوانك لـ 24 ساعة.",
                    "attempts_left": attempts_left
                }
            )



@app.post("/api/logout")
async def api_logout(request: Request):
    require_same_origin(request)
    response = JSONResponse({"ok": True})
    revoke_session(response)
    return response

@app.get("/hero.jpg")
@app.get("/hero.webp")
async def get_hero_image():
    for name in ["templates/hero.webp", "templates/hero.jpg", "hero.webp", "hero.jpg", "static/hero.jpg"]:
        if os.path.exists(name):
            media = "image/webp" if name.endswith(".webp") else "image/jpeg"
            return FileResponse(
                name,
                media_type=media,
                headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=3600"}
            )
    raise HTTPException(404, "الصورة غير موجودة على الخادم.")

@app.api_route("/health", methods=["GET", "HEAD"], response_class=PlainTextResponse)
async def health_check():
    return PlainTextResponse("OK", status_code=200)

@app.get("/api/heartbeat")
async def api_heartbeat(tab_id: str = ""):
    return {"status": "ok", "tab_id": tab_id}

@app.get("/api/settings")
async def get_settings(request: Request):
    is_local = is_local_instance(request)
    email_to_show = os.environ.get("UNPAYWALL_EMAIL", "academic@knowledgeocean.org") if is_local else "academic@knowledgeocean.org"
    return {
        "unpaywall_email": email_to_show,
        "elsevier_api_key": "***" if os.environ.get("ELSEVIER_API_KEY") else "",
        "providers": {
            "pubmed": True, "crossref": True, "openalex": True, "europepmc": True,
            "semanticscholar": True, "elsevier": bool(os.environ.get("ELSEVIER_API_KEY")),
            "doaj": True, "arxiv": True, "core": True, "zenodo": True,
            "googlebooks": True, "openlibrary": True
        }
    }

@app.post("/api/settings")
async def save_settings(request: Request):
    raise HTTPException(status_code=403, detail="Runtime settings are read-only. Configure secrets in the deployment environment.")

@app.head("/", include_in_schema=False)
async def head_root():
    return PlainTextResponse("", status_code=200)

@app.post("/api/search")
async def start_search(
    request: Request, password: str = Form(""), query: str = Form(...), mode: str = Form("keyword"), db_source: str = Form("all"),
    limit: int = Form(10), affiliation: str = Form(""), require_title: bool = Form(False), year_from: str = Form(None), year_to: str = Form(None), include_preprint: bool = Form(False),
    include_abstracts: bool = Form(False), download_fulltext: bool = Form(False), guest_token: str = Form(""),
    search_scope: str = Form("all"), doc_type_filter: str = Form("all")
):
    require_same_origin(request)
    with_abstracts = bool(include_abstracts or download_fulltext)
    ip, browser_fp = get_fingerprint(request)
    is_banned, ban_remaining = db_check_ip_ban(ip)
    if is_banned:
        hours = int(ban_remaining // 3600)
        mins = int((ban_remaining % 3600) // 60)
        time_str = f"{hours} ساعة و {mins} دقيقة" if hours > 0 else f"{mins} دقيقة"
        return JSONResponse(
            status_code=403,
            content={
                "status": "banned",
                "banned": True,
                "error": f"تم حظر عنوان IP الخاص بك ({ip}) مؤقتاً لمدة 24 ساعة لتجاوز 5 محاولات خاطئة متتالية. الوقت المتبقي لفك الحظر: {time_str}."
            }
        )

    clean_pwd = (password or "").strip()
    if clean_pwd:
        if not (verify_password(clean_pwd) or verify_other_password(clean_pwd)):
            banned, attempts_left, rem = db_record_auth_attempt(ip, success=False)
            if banned:
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "banned",
                        "banned": True,
                        "error": "تم إدخال الرمز بشكل خاطئ 5 مرات متتالية! تم حظر عنوان IP الخاص بك لمدة 24 ساعة لحماية المنصة من محاولات التخمين الآلية.",
                        "remaining_seconds": int(rem)
                    }
                )
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "status": "error",
                        "error": f"رمز الوصول المدخل غير صحيح! تبقى لديك {attempts_left} من أصل 5 محاولات قبل حظر عنوانك لـ 24 ساعة.",
                        "attempts_left": attempts_left
                    }
                )
        else:
            db_record_auth_attempt(ip, success=True)

    clean_guest_token = (guest_token or "").strip() or request.headers.get("X-Guest-Token", "").strip()
    owner_session = session_owner(request)
    is_vip = verify_password(password) or bool(owner_session and any(hmac.compare_digest(owner_session, user_hash_for(p)) for p in APP_PASSWORDS))
    is_other = (not is_vip) and (verify_other_password(password) or bool(owner_session and any(hmac.compare_digest(owner_session, user_hash_for(p)) for p in OTHER_PASSWORDS)))
    is_guest = not is_vip

    # On local instances, grant full open access with zero restrictions and without requiring any passcode!
    if is_local_instance(request):
        uh = (user_hash_for(password) if password and verify_password(password) else owner_session) if is_vip else "local_user"
    else:
        # Users with other_password are in normal queue, but have 250 daily searches renewing every day
        if is_guest:
            rate_multiplier = 2 if with_abstracts else 1
            quota_limit = SECONDARY_SEARCH_QUOTA if is_other else GUEST_SEARCH_QUOTA
            rem = get_guest_remaining_quota(ip, browser_fp, is_other=is_other, guest_token=clean_guest_token)

            if rem < rate_multiplier:
                max_summary = quota_limit // 2
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": f"نفد رصيد البحث اليومي ({quota_limit} بحث عادي أو {max_summary} بحث مع ملخصات). يتجدد الرصيد يومياً، أو أدخل مفتاح الوصول (VIP) للمتابعة بلا حدود. / Daily search quota reached ({quota_limit} standard or {max_summary} with summaries). Quota renews daily, or enter VIP key.",
                        "remaining": rem,
                        "remaining_summary": rem // 2,
                        "quota_limit": quota_limit
                    }
                )

            # Calculate units needed based on number of papers requested:
            # Each standard paper costs 1 credit; each paper with abstract costs 2 credits
            req_papers = max(1, int(limit))
            max_allowed_papers = rem // rate_multiplier
            if req_papers > max_allowed_papers:
                req_papers = max_allowed_papers
                limit = req_papers

            units_needed = req_papers * rate_multiplier
            limited, remaining = check_guest_search_quota(ip, browser_fp, units_needed, is_other=is_other, guest_token=clean_guest_token)
            if limited:
                max_summary = quota_limit // 2
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": f"نفد رصيد البحث اليومي ({quota_limit} بحث عادي أو {max_summary} بحث مع ملخصات). يتجدد الرصيد يومياً، أو أدخل مفتاح الوصول (VIP) للمتابعة بلا حدود. / Daily search quota reached.",
                        "remaining": remaining,
                        "remaining_summary": remaining // 2,
                        "quota_limit": quota_limit
                    }
                )
            if is_other:
                uh = user_hash_for(password) if password and verify_other_password(password) else owner_session
            elif clean_guest_token:
                uh = hashlib.sha256(f"guest_{clean_guest_token}_{browser_fp}".encode()).hexdigest()[:16]
            else:
                uh = hashlib.sha256(f"{ip}_{browser_fp}".encode()).hexdigest()[:16]
            if is_other:
                if limit > 250:
                    limit = 250
            else:
                if limit > 50:
                    limit = 50
        else:
            uh = user_hash_for(password) if password and verify_password(password) else owner_session

    if not query.strip():
        return JSONResponse(status_code=400, content={"error": "مصطلح البحث فارغ."})
    if len(query.strip()) < 3:
        return JSONResponse(status_code=400, content={"error": "مصطلح البحث قصير جداً (3 أحرف على الأقل)."})
    if db_source == "elsevier" and not is_vip:
        return JSONResponse(status_code=403, content={"error": "قاعدة بيانات Scopus (Elsevier) غير متاحة للضيوف وتتطلب إدخال مفتاح الوصول (VIP) أو استخدام النسخة المحلية."})
    if mode == "author" and any(ord(c) > 127 for c in query):
        return JSONResponse(status_code=400, content={"error": "في وضع الباحث، اكتب الاسم بالأحرف الإنجليزية فقط."})

    task_id = str(uuid.uuid4())
    code_hash = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()[:24] if password.strip() else ""
    _set_task(task_id, status="queued", progress=0, message="في الطابور…",
              query=query.strip(), mode=mode, code_hash=code_hash, user_hash=uh,
              is_guest=is_guest, is_vip=not is_guest,
              guest_ip=ip if is_guest else "", guest_fp=browser_fp if is_guest else "",
              guest_token=clean_guest_token if is_guest else "",
              started_at=time.time())
    response = JSONResponse({"task_id": task_id, "user_hash": uh})
    issue_session(response, uh, secure=request.url.scheme == "https")
    threading.Thread(target=managed_pipeline_wrapper, kwargs={
        "query": query.strip(),
        "mode": mode,
        "db_source": db_source,
        "limit": limit,
        "affiliation": affiliation.strip(),
        "uh": uh,
        "task_id": task_id,
        "require_title": require_title,
        "year_from": year_from,
        "year_to": year_to,
        "include_preprint": include_preprint,
        "is_guest": is_guest,
        "include_abstracts": with_abstracts,
        "download_fulltext": download_fulltext,
        "guest_ip": ip if is_guest else "",
        "guest_fp": browser_fp if is_guest else "",
        "is_other": is_other if is_guest else False,
        "guest_token": clean_guest_token if is_guest else "",
        "search_scope": search_scope,
        "doc_type_filter": doc_type_filter
    }, daemon=True).start()
    return response

@app.post("/api/cancel/{task_id}")
async def cancel_task(task_id: str, request: Request):
    require_same_origin(request)
    task_info = TASKS.get(task_id) or db_get_task(task_id)
    if not task_info:
        raise HTTPException(404, "Task not found")
    require_owner(request, task_info.get("user_hash", ""), local=is_local_instance(request))
    CANCELLED_TASKS.add(task_id)
    in_q = False
    with QUEUE_LOCK:
        if task_id in GUEST_QUEUE:
            GUEST_QUEUE.remove(task_id)
            in_q = True
        if task_id in ACTIVE_GUESTS:
            ACTIVE_GUESTS.remove(task_id)

    with TASKS_LOCK:
        task = TASKS.get(task_id, {})

    curr_status = task.get("status", "")
    if curr_status == "completed":
        return {"status": "completed", "task_id": task_id, "preserved": True}

    if curr_status == "error":
        return {"status": "error", "task_id": task_id, "preserved": False}

    has_papers = bool(task.get("papers"))
    if curr_status == "queued" or in_q or not has_papers:
        _set_task(task_id, status="error", progress=100,
                  message="تم إلغاء البحث بناءً على طلبك.",
                  error="تم إلغاء البحث بناءً على طلبك.",
                  pdf_url="", pdf_zip="", md_url="", md_zip="",
                  save_path="", local_path="", file_path="", papers=[])
        return {"status": "cancelled", "task_id": task_id, "preserved": False}

    # If running with collected papers: let process_pipeline gracefully wrap up collected papers and generate PDF
    _set_task(task_id, progress=min(90, max(task.get("progress", 0), 80)),
              message="تم إيقاف البحث — جاري الآن توليد وتجهيز ملف الأبحاث بما تم جمعه...")
    return {
        "status": "stopping",
        "task_id": task_id,
        "preserved": True,
        "message": "تم إيقاف البحث — جاري الآن توليد وتجهيز ملف الأبحاث بما تم جمعه حتى الآن..."
    }

@app.get("/api/status/{task_id}")
async def get_status(task_id: str, request: Request):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if task is None:
        task = db_get_task(task_id)
    if task is None:
        raise HTTPException(404, "المهمة غير موجودة.")
    require_owner(request, task.get("user_hash", ""), local=is_local_instance(request))
    return task

@app.api_route("/api/doi-lookup", methods=["GET", "POST"])
async def api_doi_lookup(request: Request, doi: str = Form(None), password: str = Form(None)):
    """استعلام تفصيلي فوري عن أي بحث عبر معرّف DOI."""
    req_doi = doi
    pwd = password
    if request.method == "POST":
        try:
            form = await request.form()
            req_doi = req_doi or form.get("doi")
            pwd = pwd or form.get("password")
        except Exception:
            pass
        if not req_doi or not pwd:
            try:
                body = await request.json()
                req_doi = req_doi or body.get("doi")
                pwd = pwd or body.get("password")
            except Exception:
                pass
    if not req_doi:
        req_doi = request.query_params.get("doi")
    if not pwd:
        pwd = request.query_params.get("password")

    ip, browser_fp = get_fingerprint(request)
    is_banned, ban_remaining = db_check_ip_ban(ip)
    if is_banned:
        return JSONResponse({"ok": False, "status": "banned", "error": f"تم حظر عنوان IP الخاص بك لـ 24 ساعة لتجاوز 5 محاولات خاطئة متتالية. المتبقي: {int(ban_remaining // 60)} دقيقة.", "remaining_seconds": int(ban_remaining)}, status_code=403)

    if pwd and pwd.strip():
        if not (verify_password(pwd.strip()) or verify_other_password(pwd.strip())):
            banned, attempts_left, rem = db_record_auth_attempt(ip, success=False)
            if banned:
                return JSONResponse({"ok": False, "status": "banned", "error": "تم إدخال الرمز بشكل خاطئ 5 مرات متتالية! تم حظر عنوانك لـ 24 ساعة.", "remaining_seconds": int(rem)}, status_code=403)
            return JSONResponse({"ok": False, "status": "error", "error": f"رمز الوصول المدخل غير صحيح! تبقى لديك {attempts_left} من أصل 5 محاولات قبل حظر عنوانك لـ 24 ساعة.", "attempts_left": attempts_left}, status_code=401)
        else:
            db_record_auth_attempt(ip, success=True)

    if not req_doi or not req_doi.strip():
        return JSONResponse({"ok": False, "error": "يرجى إدخال معرّف DOI للبحث."}, status_code=400)

    clean_doi = normalize_doi(req_doi)
    if not clean_doi:
        return JSONResponse({"ok": False, "error": "صيغة معرّف DOI غير صالحة. مثال: 10.1007/s40278-024-60584-4"}, status_code=400)

    # DOI Lookup access check: Free & unlimited for VIP, secondary key, or local; generous daily rate limit for guests
    is_vip = verify_password(pwd or "")
    is_other = verify_other_password(pwd or "")
    if not (is_vip or is_other or is_local_instance(request)):
        ip, browser_fp = get_fingerprint(request)
        today = get_baghdad_today()
        lim_ip, _ = db_check_rate_limit(f"doi_ip_{ip}", today, 1, 100)
        if lim_ip:
            return JSONResponse({
                "ok": False,
                "error": "تم الوصول إلى الحد اليومي لفحص المعرّفات (100 استعلام). يتجدد الرصيد يومياً، أو أدخل مفتاح الوصول (VIP). / Daily DOI lookup limit reached (100 queries)."
            }, status_code=429)

    headers = {"User-Agent": "KnowledgeOcean/1.0 (mailto:contact@knowledgeocean.org)"}
    paper_data = {
        "doi": clean_doi,
        "doi_url": f"https://doi.org/{clean_doi}",
        "title": "",
        "authors": [],
        "journal": "",
        "publisher": "",
        "year": "0000",
        "volume": "",
        "issue": "",
        "pages": "",
        "abstract": "",
        "is_oa": False,
        "oa_url": None,
        "pdf_url": None,
        "citation_count": 0,
        "is_preprint": False,
        "sources": []
    }

    def needs_data():
        return not paper_data["title"] or not paper_data["authors"] or not paper_data["journal"] or paper_data["year"] == "0000" or not paper_data["abstract"] or not paper_data["volume"] or not paper_data["pages"]

    # 1. استعلام Crossref
    try:
        cr_url = f"https://api.crossref.org/works/{urllib.parse.quote(clean_doi)}"
        cr_res = requests.get(cr_url, headers=headers, timeout=8)
        if cr_res.status_code == 200:
            msg = cr_res.json().get("message", {})
            titles = msg.get("title", [])
            paper_data["title"] = titles[0] if titles else ""
            paper_data["year"] = extract_crossref_year(msg)
            paper_data["volume"] = str(msg.get("volume") or "")
            paper_data["issue"] = str(msg.get("issue") or "")
            paper_data["pages"] = str(msg.get("page") or msg.get("article-number") or "")
            containers = msg.get("container-title") or []
            paper_data["journal"] = clean_journal_name(containers[0] if containers else "")
            paper_data["publisher"] = msg.get("publisher", "")
            paper_data["authors"] = extract_crossref_authors(msg)
            paper_data["citation_count"] = msg.get("is-referenced-by-count", 0)
            paper_data["is_preprint"] = (msg.get("type") == "posted-content")
            raw_abstract = msg.get("abstract", "")
            if raw_abstract:
                clean_abs = re.sub(r"<[^>]+>", " ", raw_abstract).strip()
                clean_abs = re.sub(r"\s+", " ", clean_abs)
                paper_data["abstract"] = clean_abs
            paper_data["sources"].append("crossref")
    except Exception as e:
        log.warning(f"Error in Crossref DOI lookup: {e}")

    # 2. استعلام Unpaywall للتحقق من الوصول المفتوح ورابط PDF المباشر
    try:
        upw_url = f"https://api.unpaywall.org/v2/{clean_doi}?email={UNPAYWALL_EMAIL}"
        upw_res = requests.get(upw_url, headers=headers, timeout=6)
        if upw_res.status_code == 200:
            upw_data = upw_res.json()
            paper_data["is_oa"] = upw_data.get("is_oa", False)
            best_oa = upw_data.get("best_oa_location") or {}
            paper_data["oa_url"] = best_oa.get("url") or best_oa.get("url_for_pdf")
            paper_data["pdf_url"] = best_oa.get("url_for_pdf")
            if not paper_data["title"] and upw_data.get("title"):
                paper_data["title"] = upw_data.get("title")
            if not paper_data["journal"] and upw_data.get("journal_name"):
                paper_data["journal"] = clean_journal_name(upw_data.get("journal_name"))
            if paper_data["year"] == "0000" and upw_data.get("year"):
                paper_data["year"] = str(upw_data.get("year"))
            paper_data["sources"].append("unpaywall")
    except Exception as e:
        log.warning(f"Error in Unpaywall lookup: {e}")

    # 3. استعلام OpenAlex لجلب المؤلفين والملخص وبيانات المجلد والصفحات المكتملة
    if needs_data():
        try:
            oa_url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
            oa_res = requests.get(oa_url, headers=headers, timeout=6)
            if oa_res.status_code == 200:
                oa_data = oa_res.json()
                if not paper_data["title"] and oa_data.get("title"):
                    paper_data["title"] = oa_data.get("title")
                oa_auths = [a.get("author", {}).get("display_name", "").strip() for a in oa_data.get("authorships", []) if a.get("author", {}).get("display_name", "").strip()]
                if not paper_data["authors"] and oa_auths:
                    paper_data["authors"] = oa_auths
                if paper_data["year"] == "0000":
                    if oa_data.get("publication_year"):
                        paper_data["year"] = str(oa_data.get("publication_year"))
                    elif oa_data.get("publication_date"):
                        paper_data["year"] = str(oa_data.get("publication_date"))[:4]
                if not paper_data["journal"]:
                    loc = oa_data.get("primary_location") or {}
                    src = (loc.get("source") or {}) if isinstance(loc, dict) else {}
                    paper_data["journal"] = clean_journal_name(src.get("display_name", "") or "")
                if not paper_data["publisher"]:
                    loc = oa_data.get("primary_location") or {}
                    src = (loc.get("source") or {}) if isinstance(loc, dict) else {}
                    if src.get("host_organization_name"):
                        paper_data["publisher"] = src.get("host_organization_name")
                biblio = oa_data.get("biblio") or {}
                if not paper_data["volume"] and biblio.get("volume"):
                    paper_data["volume"] = str(biblio.get("volume") or "")
                if not paper_data["issue"] and biblio.get("issue"):
                    paper_data["issue"] = str(biblio.get("issue") or "")
                if not paper_data["pages"]:
                    fp_ = str(biblio.get("first_page") or "")
                    lp_ = str(biblio.get("last_page") or "")
                    paper_data["pages"] = f"{fp_}–{lp_}" if fp_ and lp_ and fp_ != lp_ else fp_
                inv = oa_data.get("abstract_inverted_index")
                if inv and not paper_data["abstract"]:
                    word_pos = []
                    for word, positions in inv.items():
                        for pos in positions:
                            word_pos.append((pos, word))
                    word_pos.sort()
                    paper_data["abstract"] = " ".join(w for _, w in word_pos)
                if not paper_data["citation_count"] and oa_data.get("cited_by_count"):
                    paper_data["citation_count"] = oa_data.get("cited_by_count", 0)
                if not paper_data["oa_url"] and oa_data.get("open_access", {}).get("oa_url"):
                    paper_data["oa_url"] = oa_data.get("open_access", {}).get("oa_url")
                    paper_data["is_oa"] = True
                if oa_data.get("type") == "preprint":
                    paper_data["is_preprint"] = True
                paper_data["sources"].append("openalex")
        except Exception as e:
            log.warning(f"Error in OpenAlex lookup: {e}")

    # 4. استعلام Semantic Scholar لاستيراد المؤلفين والعنوان والمجلد والصفحات
    if needs_data():
        try:
            s2_headers = dict(headers)
            if SEMANTIC_SCHOLAR_API_KEY:
                s2_headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            s2_url = f"https://api.semanticscholar.org/graph/v1/paper/{clean_doi}?fields=title,abstract,year,authors,venue,publicationVenue,openAccessPdf,citationCount,publicationTypes,journal"
            s2_res = requests.get(s2_url, headers=s2_headers, timeout=6)
            if s2_res.status_code == 200:
                s2_data = s2_res.json()
                if not paper_data["title"] and s2_data.get("title"):
                    paper_data["title"] = s2_data.get("title")
                s2_auths = [a["name"].strip() for a in s2_data.get("authors", []) if a.get("name") and a["name"].strip()]
                if not paper_data["authors"] and s2_auths:
                    paper_data["authors"] = s2_auths
                if paper_data["year"] == "0000" and s2_data.get("year"):
                    paper_data["year"] = str(s2_data.get("year"))
                if not paper_data["publisher"] and (s2_data.get("publicationVenue") or {}).get("name"):
                    paper_data["publisher"] = s2_data["publicationVenue"]["name"]
                if not paper_data["abstract"] and s2_data.get("abstract"):
                    paper_data["abstract"] = s2_data.get("abstract")
                if not paper_data["journal"] and s2_data.get("venue"):
                    paper_data["journal"] = clean_journal_name(s2_data.get("venue"))
                if not paper_data["citation_count"] and s2_data.get("citationCount"):
                    paper_data["citation_count"] = s2_data.get("citationCount", 0)
                if not paper_data["oa_url"] and (s2_data.get("openAccessPdf") or {}).get("url"):
                    paper_data["oa_url"] = s2_data["openAccessPdf"]["url"]
                    paper_data["is_oa"] = True
                s2_j = s2_data.get("journal") or {}
                if not paper_data["volume"] and s2_j.get("volume"):
                    paper_data["volume"] = str(s2_j.get("volume") or "")
                if not paper_data["pages"] and s2_j.get("pages"):
                    paper_data["pages"] = str(s2_j.get("pages") or "")
                paper_data["sources"].append("semanticscholar")
        except Exception as e:
            log.warning(f"Error in Semantic Scholar lookup: {e}")

    # 5. استعلام Europe PMC
    if needs_data():
        try:
            epmc_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"{urllib.parse.quote(clean_doi)}"&format=json&resultType=core'
            epmc_res = requests.get(epmc_url, headers=headers, timeout=6)
            if epmc_res.status_code == 200:
                epmc_data = epmc_res.json()
                results = epmc_data.get("resultList", {}).get("result", [])
                if results:
                    res0 = results[0]
                    if not paper_data["title"] and res0.get("title"):
                        paper_data["title"] = res0.get("title")
                    epmc_auths = [a.get("fullName") or f"{a.get('firstName', '')} {a.get('lastName', '')}".strip() for a in res0.get("authorList", {}).get("author", [])]
                    epmc_auths = [a.strip() for a in epmc_auths if a and a.strip()]
                    if not epmc_auths and res0.get("authorString"):
                        epmc_auths = [a.strip() for a in res0["authorString"].split(",") if a.strip()]
                    if not paper_data["authors"] and epmc_auths:
                        paper_data["authors"] = epmc_auths
                    if paper_data["year"] == "0000" and res0.get("pubYear"):
                        paper_data["year"] = str(res0.get("pubYear"))
                    if not paper_data["journal"]:
                        paper_data["journal"] = clean_journal_name(res0.get("journalTitle") or res0.get("journalInfo", {}).get("journal", {}).get("title", ""))
                    if not paper_data["volume"] and res0.get("journalVolume"):
                        paper_data["volume"] = str(res0.get("journalVolume") or "")
                    if not paper_data["issue"] and res0.get("issue"):
                        paper_data["issue"] = str(res0.get("issue") or "")
                    if not paper_data["pages"] and res0.get("pageInfo"):
                        paper_data["pages"] = str(res0.get("pageInfo") or "")
                    if not paper_data["abstract"] and res0.get("abstractText"):
                        paper_data["abstract"] = res0.get("abstractText")
                    paper_data["sources"].append("europepmc")
        except Exception as e:
            log.warning(f"Error in Europe PMC lookup: {e}")

    # 6. استعلام DataCite (لمعرفات المستودعات والبيانات Zenodo / Figshare / IEEE)
    if needs_data():
        try:
            dc_url = f"https://api.datacite.org/dois/{urllib.parse.quote(clean_doi)}"
            dc_res = requests.get(dc_url, headers=headers, timeout=6)
            if dc_res.status_code == 200:
                attrs = dc_res.json().get("data", {}).get("attributes", {})
                if not paper_data["title"]:
                    titles = attrs.get("titles") or []
                    if titles and titles[0].get("title"):
                        paper_data["title"] = titles[0]["title"]
                dc_creators = attrs.get("creators") or []
                dc_auths = []
                for c in dc_creators:
                    cname = c.get("name") or f"{c.get('givenName', '')} {c.get('familyName', '')}".strip()
                    if cname and cname.strip():
                        dc_auths.append(cname.strip())
                if not paper_data["authors"] and dc_auths:
                    paper_data["authors"] = dc_auths
                if paper_data["year"] == "0000" and attrs.get("publicationYear"):
                    paper_data["year"] = str(attrs.get("publicationYear"))
                if not paper_data["publisher"] and attrs.get("publisher"):
                    paper_data["publisher"] = attrs.get("publisher")
                cont = attrs.get("container") or {}
                if not paper_data["journal"] and cont.get("title"):
                    paper_data["journal"] = clean_journal_name(cont.get("title"))
                if not paper_data["volume"] and cont.get("volume"):
                    paper_data["volume"] = str(cont.get("volume") or "")
                if not paper_data["issue"] and cont.get("issue"):
                    paper_data["issue"] = str(cont.get("issue") or "")
                if not paper_data["pages"] and (cont.get("firstPage") or cont.get("lastPage")):
                    fp = str(cont.get("firstPage") or "")
                    lp = str(cont.get("lastPage") or "")
                    paper_data["pages"] = f"{fp}–{lp}" if fp and lp and fp != lp else fp
                if not paper_data["abstract"]:
                    descriptions = attrs.get("descriptions") or []
                    if descriptions and descriptions[0].get("description"):
                        paper_data["abstract"] = re.sub(r"<[^>]+>", " ", descriptions[0]["description"]).strip()
                paper_data["sources"].append("datacite")
        except Exception as e:
            log.warning(f"Error in DataCite lookup: {e}")

    # 7. استعلام PubMed الحيوي كخيار بديل مباشر
    if needs_data():
        try:
            pm_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(clean_doi)}[DOI]&retmode=json"
            pm_res = requests.get(pm_url, headers=headers, timeout=5)
            if pm_res.status_code == 200:
                idlist = pm_res.json().get("esearchresult", {}).get("idlist", [])
                if idlist:
                    sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={idlist[0]}&retmode=json"
                    sum_res = requests.get(sum_url, headers=headers, timeout=5)
                    if sum_res.status_code == 200:
                        doc = sum_res.json().get("result", {}).get(idlist[0], {})
                        if not paper_data["title"] and doc.get("title"):
                            paper_data["title"] = doc.get("title", "")
                        if not paper_data["authors"]:
                            pm_auths = [a.get("name", "").strip() for a in doc.get("authors", []) if a.get("name")]
                            if pm_auths:
                                paper_data["authors"] = pm_auths
                        if not paper_data["journal"]:
                            paper_data["journal"] = clean_journal_name(doc.get("fulljournalname") or doc.get("source", ""))
                        if not paper_data["volume"] and doc.get("volume"):
                            paper_data["volume"] = str(doc.get("volume") or "")
                        if not paper_data["issue"] and doc.get("issue"):
                            paper_data["issue"] = str(doc.get("issue") or "")
                        if not paper_data["pages"] and doc.get("pages"):
                            paper_data["pages"] = str(doc.get("pages") or "")
                        if paper_data["year"] == "0000" and doc.get("pubdate"):
                            m_y = re.search(r'(\d{4})', str(doc["pubdate"]))
                            if m_y:
                                paper_data["year"] = m_y.group(1)
                        paper_data["sources"].append("pubmed")
        except Exception as e:
            log.warning(f"Error in PubMed DOI lookup: {e}")

    # 🚀 المُنقِذ: استخراج البيانات من الترويسات المركبة في الملخص إن دعت الحاجة
    if (not paper_data["journal"] or not paper_data["volume"] or not paper_data["pages"]) and paper_data["abstract"]:
        m = re.match(r'^([^¦\n\r]+)\s*¦\s*Volume\s*(\d+)\s*¦\s*Issue\s*(\d+)\s*¦[^¦\n\r]+?\s*(\d+[\-–]\d+|\d+)', paper_data["abstract"], re.IGNORECASE)
        if m:
            if not paper_data["journal"]:
                paper_data["journal"] = clean_journal_name(m.group(1).strip())
            if not paper_data["volume"]:
                paper_data["volume"] = m.group(2).strip()
            if not paper_data["issue"]:
                paper_data["issue"] = m.group(3).strip()
            if not paper_data["pages"]:
                paper_data["pages"] = m.group(4).strip()
            paper_data["abstract"] = re.sub(r'^[^¦\n\r]+¦[^¦\n\r]+¦[^¦\n\r]+¦[^¦\n\r]+(?:Sir,|)\s*', '', paper_data["abstract"]).strip()

    # 🚀 إذا كانت تفاصيل المجلد أو الصفحات ملتصقة باسم المجلة
    if paper_data["journal"] and (not paper_data["volume"] or not paper_data["pages"]):
        m_j = re.search(r'^(.*?)[,\s]+(?:Vol(?:ume|\.)?\s*)?(\d+)(?:\s*\(([^\)]+)\))?[,\s]+(?:pp?\.?\s*)?([eE]?\d+[\-–\.\w]*|Article\s+\w+.*)$', paper_data["journal"])
        if m_j:
            clean_j_title = m_j.group(1).strip()
            if clean_j_title and len(clean_j_title) > 3:
                paper_data["journal"] = clean_journal_name(clean_j_title)
                if not paper_data["volume"]:
                    paper_data["volume"] = m_j.group(2).strip()
                if not paper_data["issue"] and m_j.group(3):
                    paper_data["issue"] = m_j.group(3).strip()
                if not paper_data["pages"] and m_j.group(4):
                    paper_data["pages"] = m_j.group(4).strip()

    # Format APA and BibTeX using the strict citation engine
    paper_data["title"] = clean_title_for_citation(paper_data["title"])
    paper_data["journal"] = clean_journal_name(paper_data["journal"])
    paper_data["authors"] = [a.strip() for a in paper_data["authors"] if a and a.strip() and a.strip().lower() not in ("unknown", "unknown authors", "et al", "et al.")]

    paper_data["apa"] = format_apa_7th(paper_data, bold_volume=True)
    paper_data["apa_html"] = format_apa_7th_html(paper_data, bold_volume=True)
    paper_data["apa_plain"] = format_apa_7th_plain(paper_data)
    paper_data["bibtex"] = generate_bibtex_entry(paper_data, index=1)
    paper_data["bibtex_download_url"] = f"/api/download-bibtex?doi={urllib.parse.quote(clean_doi)}"

    paper_data["is_preprint"] = is_preprint_record(
        doi=clean_doi, journal=paper_data["journal"], title=paper_data["title"],
        raw_type=paper_data.get("raw_type"), publisher=paper_data["publisher"],
        is_preprint=paper_data["is_preprint"]
    )
    paper_data["is_peer_reviewed"] = not paper_data["is_preprint"]
    paper_data["peer_review_status"] = "محكم (Peer-Reviewed)" if not paper_data["is_preprint"] else "غير محكم / مسودة (Preprint / Unreviewed)"
    paper_data["peer_review_status_en"] = "Peer-Reviewed" if not paper_data["is_preprint"] else "Preprint / Unreviewed"

    return JSONResponse({"ok": True, "paper": paper_data})


@app.api_route("/api/download-bibtex", methods=["GET", "POST"])
async def api_download_bibtex(request: Request):
    """Secure, rate-limited endpoint for downloading .bib files. Uses the full engine fallback."""
    ip, _browser_fp = get_fingerprint(request)
    is_banned, ban_remaining = db_check_ip_ban(ip)
    if is_banned:
        return JSONResponse({"ok": False, "status": "banned", "error": f"تم حظر IP الخاص بك. المتبقي: {int(ban_remaining // 60)} دقيقة."}, status_code=403)
    
    pwd = request.query_params.get("password") or ""
    if not is_local_instance(request) and not (verify_password(pwd) or verify_other_password(pwd)):
        lim_ip, _ = db_check_rate_limit(f"bib_ip_{ip}", get_baghdad_today(), 1, 200)
        if lim_ip:
            return JSONResponse({"ok": False, "error": "تم الوصول إلى الحد اليومي لتنزيل المراجع."}, status_code=429)

    doi, bib_text, filename = "", "", ""
    
    if request.method == "POST":
        try:
            body = await request.json()
            doi, bib_text, filename, pwd = body.get("doi", ""), body.get("bibtex", ""), body.get("filename", ""), body.get("password", pwd)
        except Exception:
            try:
                form = await request.form()
                doi, bib_text, filename, pwd = form.get("doi", ""), form.get("bibtex", ""), form.get("filename", ""), form.get("password", pwd)
            except Exception: pass
    else:
        doi, bib_text, filename = request.query_params.get("doi", ""), request.query_params.get("bibtex", ""), request.query_params.get("filename", "")

    clean_doi = normalize_doi(doi) if doi else ""
    
    if clean_doi and not bib_text:
        try:
            paper_res = await api_doi_lookup(request, doi=clean_doi, password=pwd)
            data = json.loads(paper_res.body.decode())
            bib_text = data.get("paper", {}).get("bibtex", "")
        except Exception as e:
            log.warning(f"Failed full DOI lookup for bibtex download: {e}")
            
        if not bib_text:
            bib_text = f"@misc{{reference,\n  doi = {{{clean_doi}}},\n  url = {{https://doi.org/{clean_doi}}}\n}}"

    if not bib_text:
        raise HTTPException(400, "لم يتم تقديم معرّف DOI أو نص BibTeX صالح للتنزيل.")

    if filename:
        base_name = os.path.splitext(filename)[0]
    else:
        base_name = f"citation_{clean_doi.replace('/', '_').replace(':', '_')}"
    safe_name = sanitize_filename(base_name) + ".bib"
    return Response(
        content=str(bib_text)[:50000].encode("utf-8"),
        media_type="application/x-bibtex; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff"
        }
    )


@app.api_route("/api/find-doi", methods=["GET", "POST"])
async def api_find_doi(request: Request, title: str = Form(None), limit: int = Form(10), password: str = Form(None)):
    """
    البحث الشامل باسم البحث (Title) لاستخراج معرّف الـ DOI والبيانات الأكاديمية:
    يستعلم بالتوازي من 7 من أكبر قواعد البيانات الأكاديمية الشاملة عالمياً:
    1. Crossref
    2. OpenAlex
    3. Semantic Scholar
    4. PubMed (NCBI)
    5. Europe PMC
    6. arXiv
    7. DOAJ
    مع حساب نسبة التطابق الدقيقة وترتيب النتائج بحسب أعلى نسبة تطابق.
    """
    req_title = title
    pwd = password
    if request.method == "POST":
        try:
            form = await request.form()
            req_title = req_title or form.get("title")
            pwd = pwd or form.get("password")
        except Exception:
            pass
        if not req_title or not pwd:
            try:
                body = await request.json()
                req_title = req_title or body.get("title")
                pwd = pwd or body.get("password")
            except Exception:
                pass
    if not req_title:
        req_title = request.query_params.get("title")
    if not pwd:
        pwd = request.query_params.get("password")

    ip, browser_fp = get_fingerprint(request)
    is_banned, ban_remaining = db_check_ip_ban(ip)
    if is_banned:
        return JSONResponse({"ok": False, "status": "banned", "error": f"تم حظر عنوان IP الخاص بك لـ 24 ساعة لتجاوز 5 محاولات خاطئة متتالية. المتبقي: {int(ban_remaining // 60)} دقيقة.", "remaining_seconds": int(ban_remaining)}, status_code=403)

    if pwd and pwd.strip():
        if not (verify_password(pwd.strip()) or verify_other_password(pwd.strip())):
            banned, attempts_left, rem = db_record_auth_attempt(ip, success=False)
            if banned:
                return JSONResponse({"ok": False, "status": "banned", "error": "تم إدخال الرمز بشكل خاطئ 5 مرات متتالية! تم حظر عنوانك لـ 24 ساعة.", "remaining_seconds": int(rem)}, status_code=403)
            return JSONResponse({"ok": False, "status": "error", "error": f"رمز الوصول المدخل غير صحيح! تبقى لديك {attempts_left} من أصل 5 محاولات قبل حظر عنوانك لـ 24 ساعة.", "attempts_left": attempts_left}, status_code=401)
        else:
            db_record_auth_attempt(ip, success=True)

    if not req_title or not req_title.strip():
        return JSONResponse({"ok": False, "error": "يرجى إدخال عنوان البحث للبحث عن معرّف DOI."}, status_code=400)

    # Rate limiting / VIP access check
    is_vip = verify_password(pwd or "")
    is_other = verify_other_password(pwd or "")
    if not (is_vip or is_other or is_local_instance(request)):
        ip, browser_fp = get_fingerprint(request)
        today = get_baghdad_today()
        lim_ip, _ = db_check_rate_limit(f"find_doi_ip_{ip}", today, 1, 100)
        if lim_ip:
            return JSONResponse({
                "ok": False,
                "error": "تم الوصول إلى الحد اليومي لمطابقة العناوين واستخراج المعرّفات (100 استعلام). يتجدد الرصيد يومياً، أو أدخل مفتاح الوصول (VIP)."
            }, status_code=429)

    def clean_input_title(raw_title: str) -> str:
        if not raw_title:
            return ""
        t = html.unescape(str(raw_title))
        t = re.sub(r"<[^>]+>", " ", t)
        t = re.sub(r"^\s*\[?(?:pdf|html|doc)\]?[:\s\-]+", "", t, flags=re.I)
        t = re.sub(r"[:\s\-]+\[?(?:pdf|html|doc)\]?\s*$", "", t, flags=re.I)
        t = t.strip("'\"`“”‘’«»[](){}")
        t = re.sub(r"[\r\n\t\xa0\u2000-\u200b]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"[\s.,:;–—\-]+$", "", t).strip()
        return t

    clean_t = clean_input_title(req_title)
    if not clean_t:
        return JSONResponse({"ok": False, "error": "يرجى إدخال عنوان بحث صالح للبحث عن معرّف DOI."}, status_code=400)

    headers = {"User-Agent": "KnowledgeOcean/2.0 (mailto:contact@knowledgeocean.org)"}

    # Worker functions for concurrent multi-database query
    def _search_crossref(t: str):
        items = []
        try:
            url = f"https://api.crossref.org/works?query.title={urllib.parse.quote(t)}&rows=25"
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                for it in r.json().get("message", {}).get("items", []):
                    t_list = it.get("title") or []
                    title_str = t_list[0] if t_list else ""
                    doi = normalize_doi(it.get("DOI"))
                    if title_str:
                        containers = it.get("container-title") or []
                        journal_str = containers[0] if containers else ""
                        pub_str = it.get("publisher", "")
                        raw_t = it.get("type")
                        is_ppr = (raw_t == "posted-content" or is_preprint_record(doi=doi, journal=journal_str, title=title_str, raw_type=raw_t, publisher=pub_str))
                        
                        authors = []
                        for a in it.get("author", []):
                            fam = a.get("family", "").strip()
                            giv = a.get("given", "").strip()
                            name = a.get("name", "").strip() or a.get("literal", "").strip()
                            if fam and giv:
                                authors.append(f"{giv} {fam}".strip())
                            elif fam:
                                authors.append(fam)
                            elif name:
                                authors.append(name)

                        year_str = "0000"
                        for date_field in ["issued", "published-print", "published-online", "created"]:
                            dp = it.get(date_field, {}).get("date-parts", [[None]])[0][0]
                            if dp and str(dp).isdigit() and len(str(dp)) == 4:
                                year_str = str(dp)
                                break

                        volume_str = str(it.get("volume") or "")
                        issue_str = str(it.get("issue") or "")
                        page_str = str(it.get("page") or "")

                        items.append({
                            "doi": doi,
                            "doi_url": f"https://doi.org/{doi}" if doi else "",
                            "title": title_str,
                            "authors": authors,
                            "journal": journal_str,
                            "year": year_str,
                            "volume": volume_str,
                            "issue": issue_str,
                            "pages": page_str,
                            "publisher": pub_str,
                            "is_preprint": is_ppr,
                            "source": "crossref"
                        })
        except Exception:
            pass
        return items

    def _search_openalex(t: str):
        items = []
        try:
            # 1. Primary search: filter by title.search
            url = f"https://api.openalex.org/works?filter=title.search:{urllib.parse.quote(t)}&per_page=25"
            r = requests.get(url, headers=headers, timeout=6)
            results = r.json().get("results", []) if r.status_code == 200 else []
            # 2. Fallback: if fewer than 5 results, search general query
            if len(results) < 5:
                url_fb = f"https://api.openalex.org/works?search={urllib.parse.quote(t)}&per_page=25"
                r_fb = requests.get(url_fb, headers=headers, timeout=6)
                if r_fb.status_code == 200:
                    fb_results = r_fb.json().get("results", [])
                    seen_ids = {x.get("id") for x in results}
                    for item_fb in fb_results:
                        if item_fb.get("id") not in seen_ids:
                            results.append(item_fb)

            for it in results:
                title_str = it.get("title") or ""
                raw_doi = it.get("doi") or ""
                doi = normalize_doi(raw_doi)
                if title_str:
                    primary_loc = it.get("primary_location") or {}
                    source_obj = primary_loc.get("source") or {}
                    authorships = it.get("authorships") or []
                    journal_str = source_obj.get("display_name") or ""
                    pub_str = source_obj.get("host_organization_name", "")
                    raw_t = it.get("type")
                    is_ppr = (raw_t in ("preprint", "posted-content") or is_preprint_record(doi=doi, journal=journal_str, title=title_str, raw_type=raw_t, publisher=pub_str))
                    biblio = it.get("biblio") or {}
                    volume_str = str(biblio.get("volume") or "")
                    issue_str = str(biblio.get("issue") or "")
                    first_p = str(biblio.get("first_page") or "")
                    last_p = str(biblio.get("last_page") or "")
                    page_str = f"{first_p}–{last_p}" if (first_p and last_p and first_p != last_p) else first_p

                    items.append({
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else (primary_loc.get("landing_page_url") or ""),
                        "title": title_str,
                        "authors": [a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")],
                        "journal": journal_str,
                        "year": str(it.get("publication_year") or "0000"),
                        "volume": volume_str,
                        "issue": issue_str,
                        "pages": page_str,
                        "publisher": pub_str,
                        "is_preprint": is_ppr,
                        "oa_url": (it.get("open_access") or {}).get("oa_url") or primary_loc.get("pdf_url"),
                        "source": "openalex"
                    })
        except Exception:
            pass
        return items

    def _search_semanticscholar(t: str):
        items = []
        try:
            s2_headers = dict(headers)
            if SEMANTIC_SCHOLAR_API_KEY:
                s2_headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(t)}&limit=15&fields=title,authors,year,externalIds,venue,publicationVenue,openAccessPdf"
            r = requests.get(url, headers=s2_headers, timeout=6)
            if r.status_code == 200:
                for it in r.json().get("data", []):
                    title_str = it.get("title") or ""
                    ext = it.get("externalIds") or {}
                    doi = normalize_doi(ext.get("DOI") or "")
                    arxiv_id = ext.get("ArXiv") or ""
                    if not doi and arxiv_id:
                        doi = f"10.48550/arXiv.{arxiv_id}"
                    if title_str:
                        oa_obj = it.get("openAccessPdf") or {}
                        pub_venue = it.get("publicationVenue") or {}
                        journal_str = it.get("venue") or pub_venue.get("name", "")
                        items.append({
                            "doi": doi,
                            "doi_url": f"https://doi.org/{doi}" if doi else (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""),
                            "title": title_str,
                            "authors": [a.get("name", "") for a in it.get("authors", []) if a.get("name")],
                            "journal": journal_str,
                            "year": str(it.get("year") or "0000"),
                            "publisher": "",
                            "is_preprint": bool(arxiv_id and not ext.get("DOI")),
                            "oa_url": oa_obj.get("url"),
                            "source": "semanticscholar"
                        })
        except Exception:
            pass
        return items

    def _search_pubmed(t: str):
        items = []
        try:
            clean_pubmed_q = " ".join(w for w in re.sub(r"[^\w\s]", " ", t).split() if len(w) > 1)
            if not clean_pubmed_q:
                clean_pubmed_q = t
            esearch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(clean_pubmed_q)}[Title]&retmode=json&retmax=12"
            r = requests.get(esearch_url, headers=headers, timeout=6)
            if r.status_code == 200:
                id_list = r.json().get("esearchresult", {}).get("idlist", [])
                if id_list:
                    esum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(id_list)}&retmode=json"
                    r2 = requests.get(esum_url, headers=headers, timeout=6)
                    if r2.status_code == 200:
                        res_dict = r2.json().get("result", {})
                        for pmid in id_list:
                            it = res_dict.get(pmid, {})
                            title_str = it.get("title") or ""
                            doi = ""
                            for aid in it.get("articleids", []):
                                if aid.get("idtype") == "doi":
                                    doi = normalize_doi(aid.get("value"))
                                    break
                            if title_str:
                                items.append({
                                    "doi": doi,
                                    "doi_url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                    "title": title_str.rstrip("."),
                                    "authors": [a.get("name", "") for a in it.get("authors", []) if a.get("name")],
                                    "journal": it.get("source", ""),
                                    "year": str(it.get("pubdate", "")[:4] or "0000"),
                                    "volume": str(it.get("volume") or ""),
                                    "issue": str(it.get("issue") or ""),
                                    "pages": str(it.get("pages") or ""),
                                    "publisher": "",
                                    "is_preprint": False,
                                    "source": "pubmed"
                                })
        except Exception:
            pass
        return items

    def _search_europepmc(t: str):
        items = []
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22{urllib.parse.quote(t)}%22&format=json&pageSize=12"
            r = requests.get(url, headers=headers, timeout=6)
            raw_items = []
            if r.status_code == 200:
                raw_items = r.json().get("resultList", {}).get("result", [])

            # Fallback if quoted returned 0
            if not raw_items:
                t_words = " ".join(re.sub(r"[^\w\s]", " ", t).split())
                if t_words:
                    url_fb = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:({urllib.parse.quote(t_words)})&format=json&pageSize=12"
                    r_fb = requests.get(url_fb, headers=headers, timeout=6)
                    if r_fb.status_code == 200:
                        raw_items = r_fb.json().get("resultList", {}).get("result", [])

            for it in raw_items:
                title_str = it.get("title") or ""
                doi = normalize_doi(it.get("doi"))
                if title_str:
                    items.append({
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else "",
                        "title": title_str.rstrip("."),
                        "authors": [a.strip() for a in (it.get("authorString") or "").split(",") if a.strip()],
                        "journal": it.get("journalTitle", ""),
                        "year": str(it.get("pubYear") or "0000"),
                        "volume": str(it.get("journalVolume") or ""),
                        "issue": str(it.get("issue") or ""),
                        "pages": str(it.get("pageInfo") or ""),
                        "publisher": "",
                        "is_preprint": (it.get("pubType") == "preprint"),
                        "source": "europepmc"
                    })
        except Exception:
            pass
        return items

    def _search_arxiv(t: str):
        items = []
        try:
            url = f"https://export.arxiv.org/api/query?search_query=ti:%22{urllib.parse.quote(t)}%22&max_results=12"
            r = requests.get(url, headers=headers, timeout=6)
            raw_entries = []
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                raw_entries = root.findall('atom:entry', ns)

            # Fallback if quoted returned 0
            if not raw_entries:
                t_clean_words = " ".join(re.sub(r"[^\w\s]", " ", t).split()[:8])
                if t_clean_words:
                    url_fb = f"https://export.arxiv.org/api/query?search_query=ti:{urllib.parse.quote(t_clean_words)}&max_results=12"
                    r_fb = requests.get(url_fb, headers=headers, timeout=6)
                    if r_fb.status_code == 200:
                        root_fb = ET.fromstring(r_fb.text)
                        raw_entries = root_fb.findall('atom:entry', ns)

            for entry in raw_entries:
                title_elem = entry.find('atom:title', ns)
                title_str = title_elem.text if title_elem is not None else ""
                id_elem = entry.find('atom:id', ns)
                raw_id = id_elem.text.split('/abs/')[-1] if id_elem is not None else ""
                doi_elem = entry.find('arxiv:doi', ns)
                doi = normalize_doi(doi_elem.text if doi_elem is not None else (f"10.48550/arXiv.{raw_id}" if raw_id else ""))
                published = entry.find('atom:published', ns)
                year = published.text[:4] if published is not None else "0000"
                authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns) if a.find('atom:name', ns) is not None]
                if title_str:
                    items.append({
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else f"https://arxiv.org/abs/{raw_id}",
                        "title": re.sub(r"\s+", " ", title_str).strip(),
                        "authors": authors,
                        "journal": "arXiv",
                        "year": year,
                        "publisher": "arXiv",
                        "is_preprint": True,
                        "source": "arxiv"
                    })
        except Exception:
            pass
        return items

    def _search_doaj(t: str):
        items = []
        try:
            url = f"https://doaj.org/api/search/articles/bibjson.title:%22{urllib.parse.quote(t)}%22?pageSize=12"
            r = requests.get(url, headers=headers, timeout=6)
            raw_results = []
            if r.status_code == 200:
                raw_results = r.json().get("results", [])

            # Fallback if quoted returned 0
            if not raw_results:
                t_words = " ".join(re.sub(r"[^\w\s]", " ", t).split())
                if t_words:
                    url_fb = f"https://doaj.org/api/search/articles/bibjson.title:({urllib.parse.quote(t_words)})?pageSize=12"
                    r_fb = requests.get(url_fb, headers=headers, timeout=6)
                    if r_fb.status_code == 200:
                        raw_results = r_fb.json().get("results", [])

            for it in raw_results:
                bib = it.get("bibjson", {})
                title_str = bib.get("title") or ""
                doi = ""
                for identifier in bib.get("identifier", []):
                    if identifier.get("type") == "doi":
                        doi = normalize_doi(identifier.get("id"))
                        break
                if title_str:
                    j_obj = bib.get("journal") or {}
                    j_vol = str(j_obj.get("volume") or "")
                    j_num = str(j_obj.get("number") or "")
                    start_p = str(bib.get("start_page") or "")
                    end_p = str(bib.get("end_page") or "")
                    p_str = f"{start_p}–{end_p}" if (start_p and end_p and start_p != end_p) else start_p
                    items.append({
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else "",
                        "title": title_str,
                        "authors": [a.get("name", "") for a in bib.get("author", []) if a.get("name")],
                        "journal": j_obj.get("title", ""),
                        "year": str(bib.get("year") or "0000"),
                        "volume": j_vol,
                        "issue": j_num,
                        "pages": p_str,
                        "publisher": "",
                        "is_preprint": False,
                        "source": "doaj"
                    })
        except Exception:
            pass
        return items

    def _search_scholarly_registry(t: str):
        items = []
        try:
            records = search_verified_registry(t, min_similarity=65.0)
            for rec in records:
                doi = normalize_doi(rec.get("doi"))
                pub_url = rec.get("doi_url") or rec.get("url") or (f"https://doi.org/{doi}" if doi else "")
                items.append({
                    "doi": doi,
                    "doi_url": pub_url,
                    "title": rec.get("title", ""),
                    "authors": rec.get("authors", []),
                    "journal": rec.get("journal", ""),
                    "year": str(rec.get("year") or "0000"),
                    "volume": str(rec.get("volume") or ""),
                    "issue": str(rec.get("issue") or ""),
                    "pages": str(rec.get("pages") or ""),
                    "publisher": rec.get("publisher", ""),
                    "is_preprint": bool(rec.get("is_preprint", False)),
                    "oa_url": rec.get("oa_url") or rec.get("url") or "",
                    "source": rec.get("source", "ResearchGate / Verified Record")
                })
        except Exception:
            pass
        return items

    search_tasks = [
        _search_scholarly_registry,
        _search_crossref,
        _search_openalex,
        _search_semanticscholar,
        _search_pubmed,
        _search_europepmc,
        _search_arxiv,
        _search_doaj
    ]

    candidates_by_key = {}
    title_to_doi_key = {}

    with ThreadPoolExecutor(max_workers=len(search_tasks)) as pool:
        futures = {pool.submit(fn, clean_t): fn for fn in search_tasks}
        try:
            for fut in as_completed(futures, timeout=12):
                try:
                    batch = fut.result()
                    if not isinstance(batch, list):
                        continue
                    for item in batch:
                        c_title = item.get("title", "")
                        if not c_title:
                            continue
                        sim = calculate_accurate_title_similarity(clean_t, c_title)
                        item["similarity"] = sim

                        doi = item.get("doi")
                        norm_t = normalize_title_for_matching(c_title)

                        if doi:
                            key = f"doi:{doi.lower()}"
                            if norm_t in title_to_doi_key and title_to_doi_key[norm_t] != key:
                                old_k = title_to_doi_key[norm_t]
                                if old_k in candidates_by_key and not candidates_by_key[old_k].get("doi"):
                                    del candidates_by_key[old_k]
                            title_to_doi_key[norm_t] = key
                        else:
                            if norm_t in title_to_doi_key:
                                key = title_to_doi_key[norm_t]
                            else:
                                key = f"title:{norm_t}"
                                title_to_doi_key[norm_t] = key

                        if key not in candidates_by_key:
                            candidates_by_key[key] = item
                        else:
                            existing = candidates_by_key[key]
                            if sim > existing.get("similarity", 0):
                                existing["similarity"] = sim
                                existing["title"] = c_title
                            if not existing.get("doi") and item.get("doi"):
                                existing["doi"] = item["doi"]
                                existing["doi_url"] = item["doi_url"]
                            if not existing.get("doi_url") and item.get("doi_url"):
                                existing["doi_url"] = item["doi_url"]
                            if not existing.get("authors") and item.get("authors"):
                                existing["authors"] = item["authors"]
                            if not existing.get("journal") and item.get("journal"):
                                existing["journal"] = item["journal"]
                            if (not existing.get("year") or existing.get("year") == "0000") and item.get("year") and item.get("year") != "0000":
                                existing["year"] = item["year"]
                            if not existing.get("oa_url") and item.get("oa_url"):
                                existing["oa_url"] = item["oa_url"]
                            if not existing.get("volume") and item.get("volume"):
                                existing["volume"] = item["volume"]
                            if not existing.get("issue") and item.get("issue"):
                                existing["issue"] = item["issue"]
                            if not existing.get("pages") and item.get("pages"):
                                existing["pages"] = item["pages"]
                except Exception:
                    pass
        except TimeoutError:
            pass

    candidates = list(candidates_by_key.values())
    for item in candidates:
        if not item.get("doi_url"):
            item["doi_url"] = item.get("oa_url") or item.get("url") or ""
        item["apa"] = format_strict_apa_7th(item)
        if item["apa"]:
            item["apa_html"] = apa_to_html(item["apa"])
            item["apa_plain"] = apa_to_plain(item["apa"])

    norm_target = normalize_title_for_matching(clean_t)
    def _rank_key(x):
        sim = x.get("similarity", 0)
        c_norm = normalize_title_for_matching(x.get("title", ""))
        is_exact = 1 if (c_norm == norm_target) else 0
        has_link = 1 if (x.get("doi") or x.get("doi_url") or x.get("oa_url")) else 0
        has_doi = 1 if x.get("doi") else 0
        has_authors = 1 if x.get("authors") else 0
        has_journal = 1 if x.get("journal") else 0
        not_preprint = 0 if x.get("is_preprint") else 1
        return (is_exact, sim, has_link, has_doi, not_preprint, has_authors, has_journal)

    candidates.sort(key=_rank_key, reverse=True)

    target_limit = int(limit) if str(limit).isdigit() else 10
    return JSONResponse({"ok": True, "count": len(candidates), "results": candidates[:target_limit]})

@app.api_route("/api/history", methods=["GET", "POST"])
async def fetch_history_data(request: Request, password: str = None):
    pwd = password
    clean_guest_token = ""
    client_hashes = []
    if request.method == "POST":
        try:
            form = await request.form()
            pwd = pwd or form.get("password")
            clean_guest_token = form.get("guest_token") or ""
            cached_raw = form.get("cached_uhs")
            if cached_raw:
                try:
                    c_list = json.loads(cached_raw) if isinstance(cached_raw, str) else cached_raw
                    if isinstance(c_list, list):
                        client_hashes.extend([str(h) for h in c_list if h and isinstance(h, str)])
                except Exception:
                    pass
        except Exception:
            pass
        if not pwd or not clean_guest_token:
            try:
                body = await request.json()
                pwd = pwd or body.get("password")
                clean_guest_token = clean_guest_token or body.get("guest_token") or ""
                if "cached_uhs" in body and isinstance(body["cached_uhs"], list):
                    client_hashes.extend([str(h) for h in body["cached_uhs"] if h and isinstance(h, str)])
            except Exception:
                pass
    if not pwd:
        pwd = request.query_params.get("password")
    if not pwd:
        pwd = request.headers.get("X-Password")
    if not clean_guest_token:
        clean_guest_token = request.query_params.get("guest_token") or request.headers.get("X-Guest-Token") or ""
    clean_guest_token = clean_guest_token.strip()

    ip, browser_fp = get_fingerprint(request)

    candidate_uhs = set()
    if clean_guest_token:
        token_uh = hashlib.sha256(f"guest_{clean_guest_token}_{browser_fp}".encode()).hexdigest()[:16]
        candidate_uhs.add(token_uh)
    for ch in client_hashes:
        if ch and not ("/" in ch or "\\" in ch or ".." in ch):
            candidate_uhs.add(ch)

    # Strict isolation: retrieve tasks strictly belonging to this guest_token or client candidate hashes
    matched_tasks = db_get_tasks_for_guest(clean_guest_token, list(candidate_uhs))
    for t in matched_tasks:
        t_uh = t.get("user_hash")
        if t_uh and not ("/" in t_uh or "\\" in t_uh or ".." in t_uh):
            candidate_uhs.add(t_uh)

    authorized_hash = session_owner(request)
    if not authorized_hash and not is_local_instance(request):
        raise HTTPException(403, "Owner session required")
    candidate_uhs = {authorized_hash} if authorized_hash else {"local_user"}
    spaces = []
    # Only the authenticated owner workspace may be scanned.
    if pwd and (verify_password(pwd) or verify_other_password(pwd)) and authorized_hash == user_hash_for(pwd):
        pwd_space = os.path.join(DOWNLOAD_DIR, user_hash_for(pwd))
        if pwd_space not in spaces:
            spaces.append(pwd_space)

    if is_local_instance(request):
        local_space = os.path.join(DOWNLOAD_DIR, "local_user")
        if local_space not in spaces:
            spaces.append(local_space)
        if os.path.isdir(DOWNLOAD_DIR):
            for d in os.listdir(DOWNLOAD_DIR):
                full_d = os.path.join(DOWNLOAD_DIR, d)
                if os.path.isdir(full_d) and full_d not in spaces:
                    spaces.append(full_d)
    else:
        # In cloud / Hugging Face Spaces:
        # STRICT ISOLATION: Include ONLY candidate user hash directories belonging to this specific user/token!
        # DO NOT scan other directories or match by IP, guaranteeing zero data leakage across users!
        for cuh in candidate_uhs:
            full_d = os.path.join(DOWNLOAD_DIR, cuh)
            if os.path.isdir(full_d) and full_d not in spaces:
                spaces.append(full_d)

    files = []
    seen_files = set()
    now = time.time()
    for user_space in spaces:
        if not os.path.exists(user_space):
            continue
        rel_uh = os.path.basename(user_space)
        try:
            entries = os.listdir(user_space)
        except Exception:
            continue
        for entry in entries:
            fp = os.path.join(user_space, entry)
            is_valid = os.path.isfile(fp) and (entry.lower().endswith(".pdf") or entry.lower().endswith(".zip")) and not entry.lower().endswith(".json")
            if is_valid and entry not in seen_files:
                seen_files.add(entry)
                try:
                    st = os.stat(fp)
                except Exception:
                    continue

                # Check companion JSON for metadata
                base_name = os.path.splitext(entry)[0]
                companion_json = os.path.join(user_space, f"{base_name}.json")
                query_title = ""
                paper_count = 0
                if os.path.isfile(companion_json):
                    try:
                        with open(companion_json, "r", encoding="utf-8") as jf:
                            mdata = json.load(jf)
                            query_title = mdata.get("query") or ""
                            paper_count = mdata.get("count") or len(mdata.get("papers") or [])
                    except Exception:
                        pass
                if not query_title:
                    clean_name = entry.replace("Academic_Report_", "").replace("INDEX_", "")
                    query_title = clean_name.split('_')[0] if '_' in clean_name else clean_name

                files.append({
                    "filename": entry,
                    "name": entry,
                    "type": "PDF" if entry.lower().endswith(".pdf") else "ZIP",
                    "file_type": "pdf" if entry.lower().endswith(".pdf") else "zip",
                    "size": f"{st.st_size / (1024 * 1024):.2f} MB" if st.st_size >= 1024*1024 else f"{st.st_size / 1024:.1f} KB",
                    "timestamp": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "at": int(st.st_mtime * 1000),
                    "hours_left": round(max(0, FILE_TTL_SECONDS - (now - st.st_mtime)) / 3600, 1),
                    "download_url": f"/download/{rel_uh}/{entry}",
                    "pdf_url": f"/download/{rel_uh}/{entry}",
                    "save_path": os.path.abspath(fp),
                    "local_path": os.path.abspath(fp),
                    "user_hash": rel_uh,
                    "query": query_title,
                    "paper_count": paper_count
                })
    sorted_files = sorted(files, key=lambda x: x["at"], reverse=True)
    return {"files": sorted_files, "items": sorted_files, "ok": True, "count": len(sorted_files)}

@app.get("/api/history/load")
async def load_history_entry(request: Request, filename: str, user_hash: str = "", guest_token: str = ""):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")

    clean_gt = (guest_token or "").strip() or request.headers.get("X-Guest-Token", "").strip()
    candidate_hashes = []
    if user_hash and not ("/" in user_hash or "\\" in user_hash or ".." in user_hash):
        candidate_hashes.append(user_hash)
    ip, browser_fp = get_fingerprint(request)
    if clean_gt:
        token_uh = hashlib.sha256(f"guest_{clean_gt}_{browser_fp}".encode()).hexdigest()[:16]
        if token_uh not in candidate_hashes:
            candidate_hashes.append(token_uh)
    guest_uh = hashlib.sha256(f"{ip}_{browser_fp}".encode()).hexdigest()[:16]
    if guest_uh not in candidate_hashes:
        candidate_hashes.append(guest_uh)

    matched_tasks = db_get_tasks_for_guest(clean_gt, candidate_hashes)
    for t in matched_tasks:
        t_uh = t.get("user_hash")
        if t_uh and t_uh not in candidate_hashes and not ("/" in t_uh or "\\" in t_uh or ".." in t_uh):
            candidate_hashes.append(t_uh)
    if is_local_instance(request):
        candidate_hashes.append("local_user")
        if os.path.isdir(DOWNLOAD_DIR):
            for d in os.listdir(DOWNLOAD_DIR):
                if d not in candidate_hashes and os.path.isdir(os.path.join(DOWNLOAD_DIR, d)):
                    candidate_hashes.append(d)

    authorized_hash = session_owner(request)
    if not authorized_hash and not is_local_instance(request):
        raise HTTPException(403, "Owner session required")
    candidate_hashes = [authorized_hash] if authorized_hash else ["local_user"]
    target_fp = None
    target_json_fp = None
    found_uh = ""
    for uh in candidate_hashes:
        folder = os.path.join(DOWNLOAD_DIR, uh)
        check_fp = os.path.join(folder, filename)
        if os.path.isfile(check_fp):
            target_fp = check_fp
            found_uh = uh
            base_name = os.path.splitext(filename)[0]
            c_json = os.path.join(folder, f"{base_name}.json")
            if os.path.isfile(c_json):
                target_json_fp = c_json
            break

    if not target_fp:
        raise HTTPException(404, "File not found in history")

    data = {
        "filename": filename,
        "download_url": f"/download/{found_uh}/{filename}",
        "save_path": os.path.abspath(target_fp),
        "file_type": "pdf" if filename.lower().endswith(".pdf") else "zip",
        "papers": [],
        "query": filename.replace("Academic_Report_", "").split('_')[0]
    }

    if target_json_fp and os.path.isfile(target_json_fp):
        try:
            with open(target_json_fp, "r", encoding="utf-8") as jf:
                jdata = json.load(jf)
                data.update(jdata)
                data["download_url"] = f"/download/{found_uh}/{filename}"
                data["save_path"] = os.path.abspath(target_fp)
        except Exception as e:
            log.warning(f"Failed to read json companion: {e}")

    return {"ok": True, "data": data}

@app.api_route("/api/delete", methods=["POST", "DELETE"])
async def delete_file(request: Request):
    require_same_origin(request)
    filename = ""
    password = ""
    user_hash = ""
    guest_token = ""

    # Check for JSON payload
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                filename = body.get("filename") or ""
                password = body.get("password") or ""
                user_hash = body.get("user_hash") or ""
                guest_token = body.get("guest_token") or ""
        except Exception:
            pass

    # Check for Form payload fallback
    if not filename:
        try:
            form = await request.form()
            filename = form.get("filename") or ""
            password = form.get("password") or ""
            user_hash = form.get("user_hash") or ""
            guest_token = form.get("guest_token") or ""
        except Exception:
            pass

    # Query params fallback
    if not filename:
        filename = request.query_params.get("filename") or ""
        password = password or request.query_params.get("password") or ""
        user_hash = user_hash or request.query_params.get("user_hash") or ""
        guest_token = guest_token or request.query_params.get("guest_token") or ""

    if not guest_token:
        guest_token = request.headers.get("X-Guest-Token", "").strip()
    clean_gt = (guest_token or "").strip()

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "اسم ملف غير صالح."})

    candidate_hashes = []
    if user_hash and not ("/" in user_hash or "\\" in user_hash or ".." in user_hash):
        candidate_hashes.append(user_hash)

    ip, browser_fp = get_fingerprint(request)
    if clean_gt:
        token_uh = hashlib.sha256(f"guest_{clean_gt}_{browser_fp}".encode()).hexdigest()[:16]
        if token_uh not in candidate_hashes:
            candidate_hashes.append(token_uh)
    guest_uh = hashlib.sha256(f"{ip}_{browser_fp}".encode()).hexdigest()[:16]
    if guest_uh not in candidate_hashes:
        candidate_hashes.append(guest_uh)

    matched_tasks = db_get_tasks_for_guest(clean_gt, candidate_hashes)
    for t in matched_tasks:
        t_uh = t.get("user_hash")
        if t_uh and t_uh not in candidate_hashes and not ("/" in t_uh or "\\" in t_uh or ".." in t_uh):
            candidate_hashes.append(t_uh)

    if password:
        pwd_uh = user_hash_for(password)
        if pwd_uh not in candidate_hashes:
            candidate_hashes.append(pwd_uh)

    if is_local_instance(request):
        if "local_user" not in candidate_hashes:
            candidate_hashes.append("local_user")
        if os.path.isdir(DOWNLOAD_DIR):
            for d in os.listdir(DOWNLOAD_DIR):
                if d not in candidate_hashes and os.path.isdir(os.path.join(DOWNLOAD_DIR, d)):
                    candidate_hashes.append(d)

    authorized_hash = session_owner(request)
    if not authorized_hash and not is_local_instance(request):
        raise HTTPException(403, "Owner session required")
    candidate_hashes = [authorized_hash] if authorized_hash else ["local_user"]
    deleted = False
    base_dir = os.path.abspath(DOWNLOAD_DIR)
    for uh in candidate_hashes:
        target_space = os.path.abspath(os.path.join(base_dir, uh))
        fp = os.path.abspath(os.path.join(target_space, filename))
        if os.path.isfile(fp):
            try:
                os.remove(fp)
                deleted = True
                base_name = os.path.splitext(filename)[0]
                c_json = os.path.join(target_space, f"{base_name}.json")
                if os.path.isfile(c_json):
                    try:
                        os.remove(c_json)
                    except Exception:
                        pass
            except Exception as e:
                log.warning(f"Error deleting {fp}: {e}")

    if deleted:
        return {"status": "deleted", "ok": True, "filename": filename}
    return JSONResponse(status_code=404, content={"error": "الملف غير موجود أو ليس لديك صلاحية لحذفه."})


@app.get("/download/{user_hash}/{filename}")
async def download_file(user_hash: str, filename: str, request: Request, password: Optional[str] = None):
    require_owner(request, user_hash, local=is_local_instance(request))
    if "/" in filename or "\\" in filename or ".." in filename or ".." in user_hash or "/" in user_hash or "\\" in user_hash:
        raise HTTPException(400, "اسم ملف غير صالح.")

    base_dir = os.path.abspath(DOWNLOAD_DIR)
    target_space = os.path.abspath(os.path.join(base_dir, user_hash))
    fp = os.path.abspath(os.path.join(target_space, filename))

    # Strict path traversal validation
    if os.path.commonpath([base_dir, fp]) != base_dir or not fp.startswith(target_space):
        raise HTTPException(403, "محاولة وصول غير مصرح بها للمسار.")

    if not os.path.isfile(fp):
        raise HTTPException(404, "انتهت صلاحية الملف أو لم يتم العثور عليه على الخادم.")

    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/zip"
    is_preview = request.query_params.get("preview") in ("1", "true", "yes")
    disposition = "inline" if (is_preview and media_type == "application/pdf") else "attachment"
    return FileResponse(
        fp,
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-cache"
        }
    )

def disk_purge_loop():
    while True:
        try:
            now = time.time()
            if os.path.isdir(DOWNLOAD_DIR):
                for uh in os.listdir(DOWNLOAD_DIR):
                    space = os.path.join(DOWNLOAD_DIR, uh)
                    if not os.path.isdir(space):
                        continue
                    for fn in os.listdir(space):
                        fp = os.path.join(space, fn)
                        try:
                            if os.path.isfile(fp) and os.stat(fp).st_mtime < now - FILE_TTL_SECONDS:
                                os.remove(fp)
                        except OSError:
                            pass
                    try:
                        if not os.listdir(space):
                            os.rmdir(space)
                    except OSError:
                        pass
            with TASKS_LOCK:
                stale = [tid for tid, t in TASKS.items() if t.get("status") in ("completed", "error") and t.get("_done_at", now) < now - 6 * 3600]
                for tid in stale:
                    TASKS.pop(tid, None)
        except Exception:
            pass
        time.sleep(1800)

# ==========================================
# CLIENT HEARTBEAT & LOGGING FILTERS
# ==========================================
_last_client_heartbeat = 0.0
_client_lock = threading.Lock()

class _HeartbeatAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "heartbeat" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(_HeartbeatAccessFilter())

@app.api_route("/api/heartbeat", methods=["GET", "POST", "HEAD"])
async def api_heartbeat(request: Request):
    global _last_client_heartbeat
    with _client_lock:
        _last_client_heartbeat = time.time()
    return JSONResponse({
        "status": "active",
        "app": "Knowledge Ocean",
        "server_time": _last_client_heartbeat,
        "version": "9.5"
    })

_browser_opened = False
_browser_lock = threading.Lock()

def _open_browser_once():
    global _browser_opened
    with _browser_lock:
        if _browser_opened:
            return
        _browser_opened = True

    time.sleep(1.2)
    try:
        import webbrowser
        log.info("🌐 [BrowserManager] Opening browser: http://localhost:7860/")
        webbrowser.open("http://localhost:7860/", new=0)
    except Exception as e:
        log.warning(f"Failed to auto-open browser: {e}")

from contextlib import asynccontextmanager
@asynccontextmanager
async def _lifespan(_app):
    init_db()
    init_fonts()
    threading.Thread(target=disk_purge_loop, daemon=True).start()
    log.info("🚀 Knowledge Ocean v1.0 Engine Ready (Canonical Multi-Source Edition)")
    if os.environ.get("LOCAL_INSTANCE") == "1" and not os.environ.get("NO_BROWSER"):
        threading.Thread(target=_open_browser_once, daemon=True).start()
    yield

app.router.lifespan_context = _lifespan

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, access_log=False)