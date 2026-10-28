# -*- coding: utf-8 -*-
"""
Thread-safe, rate-limited HTTP network client and circuit breaker.
Provides safe_get() with per-provider locks, delay management, and 429 cooldowns.
"""

import os
import time
import logging
import threading
from email.utils import parsedate_to_datetime
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("AcademicAPI")

from config_loader import load_local_config

# Load local config.txt if present (supports local user settings)
load_local_config()

UNPAYWALL_EMAIL = os.environ.get("UNPAYWALL_EMAIL", "contact@example.com").strip()
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
ELSEVIER_API_KEY = os.environ.get("ELSEVIER_API_KEY", "").strip()
CORE_API_KEY = os.environ.get("CORE_API_KEY", "").strip()

# Global session with connection pooling
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": f"KnowledgeOcean/9.5 (mailto:{UNPAYWALL_EMAIL})"})

try:
    # Notice: 429 is NOT in status_forcelist to prevent 12-second lock freezes on rate limits.
    # 429 is handled gracefully by our circuit breaker.
    retry_strategy = Retry(
        total=2,
        status_forcelist=[500, 502, 503, 504],
        backoff_factor=1.0,
        # A provider may send Retry-After measured in hours. Circuit breakers
        # handle cooldowns; urllib3 must never sleep for that unbounded value.
        respect_retry_after_header=False
    )
    _adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=retry_strategy)
    HTTP.mount("https://", _adapter)
    HTTP.mount("http://", _adapter)
    # Personal/free Scopus keys must not incur hidden transport-level retries.
    HTTP.mount("https://api.elsevier.com/", HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=0))
except Exception:
    pass

# Independent per-provider concurrency locks
ENGINE_LOCKS: Dict[str, threading.Lock] = {
    'crossref': threading.Lock(),
    'pubmed': threading.Lock(),
    'elsevier': threading.Lock(),
    'europepmc': threading.Lock(),
    'openalex': threading.Lock(),
    'semanticscholar': threading.Lock(),
    'arxiv': threading.Lock(),
    'doaj': threading.Lock(),
    'googlebooks': threading.Lock(),
    'openlibrary': threading.Lock(),
    'zenodo': threading.Lock(),
    'core': threading.Lock()
}

ENGINE_DELAYS: Dict[str, float] = {
    'crossref': 0.2,
    'pubmed': 0.3,
    'elsevier': 2.0,
    'europepmc': 0.3,
    'openalex': 0.2,
    'semanticscholar': 0.8,
    'arxiv': 1.5,
    'doaj': 0.2,
    'googlebooks': 0.3,
    'openlibrary': 0.3,
    'zenodo': 0.3,
    'core': 0.3
}

# Independent circuit breaker state: engine_name -> {cooldown_until, reason, tripped_at}
CIRCUIT_STATES: Dict[str, dict] = {}
CIRCUIT_LOCK = threading.Lock()

def is_engine_in_cooldown(engine_name: str) -> bool:
    now = time.time()
    with CIRCUIT_LOCK:
        st = CIRCUIT_STATES.get(engine_name)
        if not st:
            return False
        return now < st.get("cooldown_until", 0)

def trip_engine_circuit(engine_name: str, cooldown_seconds: float = 60.0, reason: str = "Rate-limited / 429"):
    with CIRCUIT_LOCK:
        now = time.time()
        CIRCUIT_STATES[engine_name] = {
            "cooldown_until": now + cooldown_seconds,
            "reason": reason,
            "tripped_at": now
        }
        log.warning(f"Circuit breaker tripped for '{engine_name}' for {cooldown_seconds}s (Reason: {reason}).")

def get_engine_circuit_status(engine_name: str) -> Optional[dict]:
    with CIRCUIT_LOCK:
        st = CIRCUIT_STATES.get(engine_name)
        if st and time.time() < st.get("cooldown_until", 0):
            return dict(st)
        return None

# Global event controlling guest execution vs VIP
GUESTS_CAN_RUN = threading.Event()
GUESTS_CAN_RUN.set()
CANCELLED_TASKS = set()
TASKS = {}
TASKS_LOCK = threading.RLock()


def _task_stopped(task_id: Optional[str]) -> bool:
    if not task_id:
        return False
    if task_id in CANCELLED_TASKS:
        return True
    with TASKS_LOCK:
        task = TASKS.get(task_id, {})
        deadline = task.get("_search_deadline")
        return task.get("status") in ("completed", "error") or bool(deadline and time.monotonic() >= deadline)


def _header_wait(value: str) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError, AttributeError):
            return 0.0
    return max(0.0, min(7 * 86400.0, seconds))


def _scopus_quota_cooldown(response, circuit_key: str) -> bool:
    """Honor the actual key's allowance; no assumed universal free quota."""
    headers = response.headers
    exhausted = str(headers.get("X-RateLimit-Remaining", "")).strip() == "0" or "QUOTA_EXCEEDED" in str(headers.get("X-ELS-Status", "")).upper()
    if not exhausted and response.status_code != 429:
        return False
    cooldown = max(60.0, _header_wait(headers.get("Retry-After", "")))
    if exhausted:
        try:
            cooldown = max(cooldown, min(7 * 86400.0, float(headers.get("X-RateLimit-Reset", "")) - time.time()))
        except (TypeError, ValueError, OverflowError):
            pass
    trip_engine_circuit(circuit_key, cooldown_seconds=cooldown, reason="Scopus quota exhausted" if exhausted else "HTTP 429 Too Many Requests")
    return True

def safe_get(engine_name: str, url: str, task_id: Optional[str] = None, is_guest: bool = False, **kwargs) -> Optional[requests.Response]:
    """
    Executes a safe GET request respecting per-provider locks, delays,
    granular circuit breaker cooldowns (429, 401/403, 5xx, timeout), and instant task cancellations.
    """
    circuit_key = kwargs.pop("circuit_key", engine_name)
    quota_aware = kwargs.pop("quota_aware", False)
    if _task_stopped(task_id):
        return None

    # Check circuit breaker
    if is_engine_in_cooldown(circuit_key):
        return None

    while is_guest and not GUESTS_CAN_RUN.is_set():
        if _task_stopped(task_id):
            return None
        if task_id:
            with TASKS_LOCK:
                if task_id in TASKS:
                    TASKS[task_id].update({"status": "queued", "message": "تم إيقاف البحث مؤقتاً لإعطاء الأولوية لمستخدم يمتلك رمز وصول..."})
        GUESTS_CAN_RUN.wait(timeout=0.4)
        if task_id:
            with TASKS_LOCK:
                if task_id in TASKS:
                    TASKS[task_id].update({"status": "processing", "message": "جاري استئناف البحث بعد انتهاء مستخدم الـ VIP..."})

    if _task_stopped(task_id):
        return None

    lock = ENGINE_LOCKS.get(engine_name)
    delay = ENGINE_DELAYS.get(engine_name, 0.3)

    if lock:
        while not lock.acquire(timeout=0.2):
            if _task_stopped(task_id):
                return None
    try:
        if _task_stopped(task_id) or is_engine_in_cooldown(circuit_key):
            return None
        res = HTTP.get(url, **kwargs)
        if task_id and task_id in CANCELLED_TASKS:
            return None
        if quota_aware and _scopus_quota_cooldown(res, circuit_key):
            pass
        elif res.status_code == 429:
            retry_after = res.headers.get("Retry-After")
            cooldown = 60.0
            if retry_after and retry_after.isdigit():
                cooldown = min(180.0, float(retry_after))
            trip_engine_circuit(circuit_key, cooldown_seconds=cooldown, reason="HTTP 429 Too Many Requests")
        elif res.status_code in (401, 403):
            trip_engine_circuit(circuit_key, cooldown_seconds=300.0, reason=f"HTTP {res.status_code} Auth/Forbidden")
        elif res.status_code >= 500:
            trip_engine_circuit(circuit_key, cooldown_seconds=30.0, reason=f"HTTP {res.status_code} Server Error")

        if lock and not (task_id and task_id in CANCELLED_TASKS):
            time.sleep(delay)
        return res
    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
        trip_engine_circuit(circuit_key, cooldown_seconds=20.0, reason="Request Timeout")
        return None
    except requests.exceptions.RequestException as e:
        log.warning(f"Engine '{engine_name}' request failed: {e}")
        return None
    finally:
        if lock:
            lock.release()
